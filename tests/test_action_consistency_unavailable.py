from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw
import pytest

from worldbench.dataset import Episode
from worldbench.metrics.action_consistency import ActionConsistencyMetric
from worldbench.runners.evaluator import weighted_score
from worldbench.runners.reporter import generate_markdown_report
from worldbench.schemas import (
    ActionRecord,
    EpisodeMetadata,
    EpisodeResult,
    EvaluationResult,
    MetricResult,
)


def _make_motion_frames(tmp_path: Path) -> list[Path]:
    frames: list[Path] = []
    for idx, x in enumerate([16, 20, 24]):
        image = Image.new("RGB", (64, 48), (10, 10, 10))
        draw = ImageDraw.Draw(image)
        draw.rectangle((x, 18, x + 6, 24), fill=(220, 40, 40))
        path = tmp_path / f"{idx:03d}.png"
        image.save(path)
        frames.append(path)
    return frames


def _make_episode(tmp_path: Path, actions: list[ActionRecord]) -> Episode:
    frames = _make_motion_frames(tmp_path)
    return Episode(
        name="episode_001",
        path=tmp_path,
        frames=frames,
        predictions=frames,
        actions=actions,
        states=[],
        metadata=EpisodeMetadata(),
    )


def test_directional_string_actions_still_score_normally(tmp_path: Path) -> None:
    episode = _make_episode(
        tmp_path,
        [
            ActionRecord(t=0, action="move_right", dx=1.0, dy=0.0),
            ActionRecord(t=1, action="move_right", dx=1.0, dy=0.0),
            ActionRecord(t=2, action="move_right", dx=1.0, dy=0.0),
        ],
    )

    result = ActionConsistencyMetric().evaluate(episode, episode.predictions)

    assert result.is_available
    assert result.score is not None and result.score > 80


def test_explicit_dx_dy_actions_still_score_normally(tmp_path: Path) -> None:
    episode = _make_episode(
        tmp_path,
        [
            ActionRecord(t=0, action="noop", dx=1.0, dy=0.0),
            ActionRecord(t=1, action="noop", dx=1.0, dy=0.0),
            ActionRecord(t=2, action="noop", dx=1.0, dy=0.0),
        ],
    )

    result = ActionConsistencyMetric().evaluate(episode, episode.predictions)

    assert result.is_available
    assert result.score is not None and result.score > 80


def test_arbitrary_numeric_action_vector_is_unsupported(tmp_path: Path) -> None:
    episode = _make_episode(
        tmp_path,
        [
            ActionRecord(t=0, action=[1.2, 3.4, 5.6, 7.8, 9.1, 2.3, 4.5]),
            ActionRecord(t=1, action=[1.2, 3.4, 5.6, 7.8, 9.1, 2.3, 4.5]),
            ActionRecord(t=2, action=[1.2, 3.4, 5.6, 7.8, 9.1, 2.3, 4.5]),
        ],
    )

    result = ActionConsistencyMetric().evaluate(episode, episode.predictions)

    assert not result.is_available
    assert result.score is None
    assert (
        result.reason
        == "unsupported raw numeric action vectors require an action adapter."
    )


def test_unavailable_metric_excluded_from_overall_score() -> None:
    metrics = {
        "visual_similarity": MetricResult(name="visual_similarity", score=80.0),
        "action_consistency": MetricResult(
            name="action_consistency",
            score=None,
            status="unsupported",
            reason="Raw numeric action vectors require an action adapter.",
        ),
        "temporal_stability": MetricResult(name="temporal_stability", score=60.0),
    }
    weights = {
        "visual_similarity": 0.25,
        "action_consistency": 0.30,
        "temporal_stability": 0.20,
    }

    assert weighted_score(metrics, weights) == pytest.approx(71.11111111111111)


def test_all_available_metrics_preserve_weighted_score() -> None:
    metrics = {
        "visual_similarity": MetricResult(name="visual_similarity", score=80.0),
        "action_consistency": MetricResult(name="action_consistency", score=50.0),
        "temporal_stability": MetricResult(name="temporal_stability", score=60.0),
    }
    weights = {
        "visual_similarity": 0.25,
        "action_consistency": 0.30,
        "temporal_stability": 0.20,
    }

    assert weighted_score(metrics, weights) == pytest.approx(62.666666666666664)


def test_report_shows_na_for_unsupported_metrics(capsys) -> None:
    result = EvaluationResult(
        dataset_path="dataset",
        predictions_path="predictions",
        created_at="2026-01-01T00:00:00Z",
        score=71.1,
        metrics={
            "visual_similarity": MetricResult(name="visual_similarity", score=80.0),
            "action_consistency": MetricResult(
                name="action_consistency",
                score=None,
                status="unsupported",
                reason="unsupported raw numeric action vectors require an action adapter.",
            ),
        },
        episodes=[
            EpisodeResult(
                episode="episode_001",
                score=71.1,
                metrics={
                    "visual_similarity": MetricResult(
                        name="visual_similarity", score=80.0
                    ),
                    "action_consistency": MetricResult(
                        name="action_consistency",
                        score=None,
                        status="unsupported",
                        reason="unsupported raw numeric action vectors require an action adapter.",
                    ),
                },
            )
        ],
        weights={"visual_similarity": 0.25, "action_consistency": 0.30},
    )

    result.print_summary()
    markdown = generate_markdown_report(result)
    output = capsys.readouterr().out

    assert "N/A" in output
    assert "N/A" in markdown
    assert (
        "unsupported raw numeric action vectors require an action adapter." in markdown
    )
