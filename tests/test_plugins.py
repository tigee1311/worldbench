from __future__ import annotations

from pathlib import Path

import pytest

from worldbench import paired_bootstrap_interval, verify_result_file
from worldbench.dataset import Episode, RolloutDataset
from worldbench.plugins import (
    MetricRequirements,
    PluginRegistry,
    UnsupportedPluginResult,
)
from worldbench.runners.evaluator import EvaluationRunner
from worldbench.schemas import EpisodeMetadata, MetricResult


class ConstantMetric:
    name = "custom_constant"
    version = "0.1.0"
    requirements = MetricRequirements(input_modalities=("rgb_frames",))

    def evaluate(self, episode: Episode, prediction_frames: list[Path]) -> MetricResult:
        del episode, prediction_frames
        return MetricResult(name=self.name, score=77.0)


class LaterMetric:
    name = "z_later"
    version = "2.0.0"
    requirements = MetricRequirements(input_modalities=("rgb_frames",))

    def evaluate(self, episode: Episode, prediction_frames: list[Path]) -> MetricResult:
        del episode, prediction_frames
        return MetricResult(name=self.name, score=88.0)


class UnsupportedMetric:
    name = "custom_unsupported"
    version = "0.1.0"
    requirements = MetricRequirements(requires_actions=True)

    def evaluate(self, episode: Episode, prediction_frames: list[Path]) -> MetricResult:
        del episode, prediction_frames
        raise UnsupportedPluginResult("custom action schema is unsupported")


class FailingMetric:
    name = "custom_failing"
    version = "0.1.0"
    requirements = MetricRequirements(input_modalities=("rgb_frames",))

    def evaluate(self, episode: Episode, prediction_frames: list[Path]) -> MetricResult:
        del episode, prediction_frames
        raise RuntimeError("boom")


def test_metric_registry_orders_plugins_deterministically() -> None:
    registry = PluginRegistry()
    registry.register_metric(LaterMetric())
    registry.register_metric(ConstantMetric())

    assert [plugin.name for plugin in registry.metrics.items()] == [
        "custom_constant",
        "z_later",
    ]
    assert registry.provenance()["metric_plugins"] == {
        "custom_constant": "0.1.0",
        "z_later": "2.0.0",
    }


def test_duplicate_metric_names_fail_clearly() -> None:
    registry = PluginRegistry()
    registry.register_metric(ConstantMetric())

    with pytest.raises(ValueError, match="Duplicate metric plugin name"):
        registry.register_metric(ConstantMetric())


def test_metric_plugin_version_appears_in_result_provenance(tmp_path: Path) -> None:
    result = EvaluationRunner(_dataset(tmp_path)).run(
        metrics=[ConstantMetric()],
        weights={"custom_constant": 1.0},
    )

    assert result.score == pytest.approx(77.0)
    assert result.provenance["metric_plugins"] == {"custom_constant": "0.1.0"}


def test_unsupported_metric_plugin_returns_na(tmp_path: Path) -> None:
    result = EvaluationRunner(_dataset(tmp_path)).run(
        metrics=[UnsupportedMetric()],
        weights={"custom_unsupported": 1.0},
    )

    metric = result.metrics["custom_unsupported"]
    assert metric.status == "unsupported"
    assert metric.score is None
    assert metric.reason == "custom action schema is unsupported"


def test_metric_plugin_exceptions_are_isolated(tmp_path: Path) -> None:
    result = EvaluationRunner(_dataset(tmp_path)).run(
        metrics=[FailingMetric()],
        weights={"custom_failing": 1.0},
    )

    metric = result.metrics["custom_failing"]
    assert metric.status == "unsupported"
    assert metric.score is None
    assert "Metric plugin 'custom_failing' failed" in str(metric.reason)


def test_duplicate_explicit_metric_names_fail_before_evaluation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Duplicate metric plugin name"):
        EvaluationRunner(_dataset(tmp_path)).run(
            metrics=[ConstantMetric(), ConstantMetric()],
            weights={"custom_constant": 1.0},
        )


def test_public_api_exports_hardening_helpers() -> None:
    assert paired_bootstrap_interval
    assert verify_result_file


def _dataset(tmp_path: Path) -> RolloutDataset:
    episode = Episode(
        name="episode_001",
        path=tmp_path / "episode_001",
        frames=[],
        predictions=[],
        actions=[],
        states=[],
        metadata=EpisodeMetadata(name="episode_001"),
    )
    return RolloutDataset(path=tmp_path, episodes=[episode])
