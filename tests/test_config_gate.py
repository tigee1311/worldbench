from __future__ import annotations

import copy
from pathlib import Path

from click.testing import CliRunner
import pytest

from worldbench.cli import app
from worldbench.config import coverage_for, load_config
from worldbench.runners.regression import build_gate_comparison
from worldbench.schemas import EvaluationResult


def test_project_config_parses_metrics_gate_and_stable_hash(tmp_path: Path) -> None:
    path = tmp_path / "worldbench.yml"
    path.write_text(
        """metrics:
  visual_similarity: {enabled: true, required: true, weight: 0.6}
  temporal_stability: {enabled: true, required: true, weight: 0.4}
  action_consistency: {enabled: false, required: false, weight: 0}
  object_permanence: {enabled: false, required: false, weight: 0}
  contact_realism: {enabled: false, required: false, weight: 0}
gate:
  min_metric_coverage: 1.0
""",
        encoding="utf-8",
    )

    config, loaded_path = load_config(path)

    assert loaded_path == path
    assert config.enabled_metrics == ["visual_similarity", "temporal_stability"]
    assert config.required_metrics == ["visual_similarity", "temporal_stability"]
    assert config.configured_weights == {
        "visual_similarity": 0.6,
        "temporal_stability": 0.4,
    }
    assert len(config.configuration_hash) == 64


def test_configuration_hash_is_order_independent_and_materially_sensitive(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.yml"
    second = tmp_path / "second.yml"
    changed = tmp_path / "changed.yml"
    first.write_text(
        """metrics:
  visual_similarity: {enabled: true, required: true, weight: 0.6}
  temporal_stability: {enabled: true, required: false, weight: 0.4}
""",
        encoding="utf-8",
    )
    second.write_text(
        """metrics:
  temporal_stability: {weight: 0.4, required: false, enabled: true}
  visual_similarity: {weight: 0.6, required: true, enabled: true}
""",
        encoding="utf-8",
    )
    changed.write_text(
        """metrics:
  visual_similarity: {enabled: true, required: true, weight: 0.7}
  temporal_stability: {enabled: true, required: false, weight: 0.3}
""",
        encoding="utf-8",
    )

    config_a, _ = load_config(first)
    config_b, _ = load_config(second)
    config_c, _ = load_config(changed)

    assert config_a.configuration_hash == config_b.configuration_hash
    assert config_a.configuration_hash != config_c.configuration_hash


@pytest.mark.parametrize(
    "body, message",
    [
        (
            """metrics:
  visual_similarity: {enabled: false, weight: 0}
  temporal_stability: {enabled: false, weight: 0}
  action_consistency: {enabled: false, weight: 0}
  object_permanence: {enabled: false, weight: 0}
  contact_realism: {enabled: false, weight: 0}
""",
            "At least one metric",
        ),
        (
            "metrics:\n  visual_similarity: {enabled: false, required: true, weight: 1}",
            "Required metrics",
        ),
        ("metrics:\n  made_up: {enabled: true, weight: 1}", "Unknown metrics"),
        (
            "metrics:\n  visual_similarity: {enabled: true, weight: -1}",
            "greater than or equal",
        ),
        (
            "metrics:\n  visual_similarity: {enabled: true, weight: .inf}",
            "finite number",
        ),
        (
            "metrics:\n  visual_similarity: {enabled: true, weight: 1}\ngate:\n  min_metric_coverage: .inf",
            "finite number",
        ),
    ],
)
def test_invalid_config_is_rejected(tmp_path: Path, body: str, message: str) -> None:
    path = tmp_path / "worldbench.yml"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_config(path)


def test_coverage_reports_configured_weight_and_effective_weights() -> None:
    coverage = coverage_for(
        [
            "visual_similarity",
            "action_consistency",
            "temporal_stability",
            "object_permanence",
            "contact_realism",
        ],
        {
            "visual_similarity": 0.25,
            "action_consistency": 0.30,
            "temporal_stability": 0.20,
            "object_permanence": 0.15,
            "contact_realism": 0.10,
        },
        ["visual_similarity", "temporal_stability"],
    )

    assert coverage["metric_coverage"] == pytest.approx(0.4)
    assert coverage["configured_weight_coverage"] == pytest.approx(0.45)
    assert coverage["effective_normalized_weights"] == pytest.approx(
        {"visual_similarity": 5 / 9, "temporal_stability": 4 / 9}
    )
    assert coverage["unsupported_metrics"] == [
        "action_consistency",
        "object_permanence",
        "contact_realism",
    ]


def test_result_schema_v2_serializes_composite_and_loads_legacy() -> None:
    legacy = EvaluationResult.model_validate(
        {
            "schema_version": "1",
            "dataset_path": "suite",
            "created_at": "2026-01-01T00:00:00Z",
            "score": 87.28,
            "weights": {"visual_similarity": 0.25},
            "metrics": {
                "visual_similarity": {"name": "visual_similarity", "score": 87.28}
            },
        }
    )

    assert legacy.composite_score == 87.28
    assert legacy.overall_score == 87.28
    assert legacy.to_dict()["composite_score"] == 87.28
    assert legacy.effective_normalized_weights == {"visual_similarity": 1.0}


def test_gate_fails_when_required_metric_disappears() -> None:
    baseline = _batch()
    candidate = _batch(available=("visual_similarity",))

    result = build_gate_comparison(
        baseline,
        candidate,
        required_metrics=["temporal_stability"],
        strict_config_match=False,
    )

    assert result["status"] == "FAIL"
    assert {item["kind"] for item in result["failure_reasons"]} >= {
        "metric_disappeared",
        "required_metric",
    }


def test_gate_fails_mismatched_weights_and_hash_in_strict_mode() -> None:
    baseline = _batch()
    candidate = _batch()
    candidate["configured_weights"] = {
        "visual_similarity": 0.7,
        "temporal_stability": 0.3,
    }
    candidate["configuration_hash"] = "candidate"

    result = build_gate_comparison(baseline, candidate)

    assert result["status"] == "FAIL"
    mismatch = next(
        item
        for item in result["failure_reasons"]
        if item["kind"] == "configuration_mismatch"
    )
    assert "configured metric weights differ" in mismatch["details"]
    assert "configuration hashes differ" in mismatch["details"]


def test_gate_warns_for_intentional_non_strict_config_comparison() -> None:
    baseline = _batch()
    candidate = _batch()
    candidate["configuration_hash"] = "candidate"

    result = build_gate_comparison(baseline, candidate, strict_config_match=False)

    assert result["status"] == "PASS"
    assert any(
        "configuration hashes differ" in warning for warning in result["warnings"]
    )


def test_gate_fails_schema_mismatch_in_strict_mode() -> None:
    baseline = _batch()
    candidate = _batch()
    candidate["schema_version"] = "1"

    result = build_gate_comparison(baseline, candidate)

    mismatch = next(
        item
        for item in result["failure_reasons"]
        if item["kind"] == "configuration_mismatch"
    )
    assert "result schema versions differ" in mismatch["details"]


def test_gate_warns_for_legacy_schema_v1_artifacts() -> None:
    baseline = _batch()
    candidate = _batch()
    baseline["schema_version"] = "1"
    candidate["schema_version"] = "1"
    baseline.pop("configuration_hash")
    candidate.pop("configuration_hash")

    result = build_gate_comparison(baseline, candidate)

    assert result["status"] == "PASS"
    assert (
        "This result predates schema v2, so full configuration compatibility could not be verified."
        in result["warnings"]
    )


def test_gate_fails_when_available_episode_counts_differ() -> None:
    baseline = _batch()
    candidate = _batch()
    candidate["aggregate"]["metrics"]["visual_similarity"]["available_count"] = 2

    result = build_gate_comparison(baseline, candidate)

    mismatch = next(
        item
        for item in result["failure_reasons"]
        if item["kind"] == "configuration_mismatch"
    )
    assert (
        "available episode counts differ for visual_similarity" in mismatch["details"]
    )


def test_gate_rejects_different_dataset_content() -> None:
    baseline = _batch()
    candidate = _batch()
    candidate["dataset_identifier"] = "sha256:different"

    with pytest.raises(ValueError, match="different ground-truth dataset content"):
        build_gate_comparison(baseline, candidate)


def test_gate_enforces_episode_regressions_and_minimum_improvement() -> None:
    baseline = _batch()
    candidate = _batch()
    candidate["episodes"][0]["score"] = 79.5
    candidate["aggregate"]["overall"]["mean"] = 79.5

    result = build_gate_comparison(
        baseline,
        candidate,
        max_overall_drop=100,
        max_episode_regressions=0,
        min_composite_improvement=0,
    )

    kinds = {item["kind"] for item in result["failure_reasons"]}
    assert {"episode_regressions", "composite_improvement"} <= kinds


def test_gate_enforces_minimum_count_metric_and_weight_coverage() -> None:
    candidate = _batch(available=("visual_similarity",))
    result = build_gate_comparison(
        copy.deepcopy(candidate),
        candidate,
        min_metric_count=2,
        min_metric_coverage=0.75,
        min_configured_weight_coverage=0.7,
    )
    kinds = {item["kind"] for item in result["failure_reasons"]}
    assert {"metric_count", "metric_coverage", "configured_weight_coverage"} <= kinds


def test_development_commands_are_hidden_and_deprecated(tmp_path: Path) -> None:
    help_result = CliRunner().invoke(app, ["--help"])
    assert "demo" not in help_result.output
    assert "benchmark" not in help_result.output
    result = CliRunner().invoke(app, ["demo", str(tmp_path / "fixture")])
    assert result.exit_code == 0
    assert "Deprecated" in result.output


def _batch(
    *, available: tuple[str, ...] = ("visual_similarity", "temporal_stability")
) -> dict:
    configured = ["visual_similarity", "temporal_stability"]
    weights = {"visual_similarity": 0.6, "temporal_stability": 0.4}
    metrics = {}
    for name in configured:
        if name in available:
            metrics[name] = {
                "status": "available",
                "mean": 80.0,
                "available_count": 1,
                "total_count": 1,
            }
        else:
            metrics[name] = {
                "status": "unsupported",
                "available_count": 0,
                "total_count": 1,
            }
    return {
        "schema_version": "2",
        "result_type": "batch_evaluation",
        "checkpoint_name": "checkpoint",
        "skip_context": 4,
        "episode_count": 1,
        "episode_ids": ["episode.mp4"],
        "dataset_identifier": "sha256:dataset",
        "episodes": [{"episode_id": "episode.mp4", "score": 80.0}],
        "aggregate": {
            "overall": {"mean": 80.0},
            "composite_score": {"mean": 80.0},
            "metrics": metrics,
        },
        "horizon": {
            "t+1": {"metrics": {name: {"mean": 80.0, "count": 1} for name in available}}
        },
        "enabled_metrics": configured,
        "required_metrics": [],
        "configured_weights": weights,
        "configuration_hash": "baseline",
        "coverage": coverage_for(configured, weights, list(available)),
    }
