from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw
import pytest

from worldbench.backends.demo import DemoBackend
from worldbench.dataset import Episode
from worldbench.metrics.contact import ContactRealismMetric
from worldbench.metrics.object_permanence import ObjectPermanenceMetric
from worldbench.runners.evaluator import weighted_score
from worldbench.runners.reporter import generate_markdown_report
from worldbench.schemas import EpisodeMetadata, EpisodeResult, EvaluationResult, MetricResult


def _make_real_style_episode(tmp_path: Path) -> Episode:
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frames: list[Path] = []
    for idx, offset in enumerate([0, 3, 6]):
        image = Image.new("RGB", (96, 72), (20, 24, 28))
        draw = ImageDraw.Draw(image)
        draw.rectangle((8 + offset, 18, 24 + offset, 34), fill=(228, 40, 34))
        draw.rectangle((50 + offset, 30, 68 + offset, 48), fill=(42, 206, 98))
        path = frames_dir / f"{idx:06d}.png"
        image.save(path)
        frames.append(path)

    return Episode(
        name="episode_000001",
        path=tmp_path,
        frames=frames,
        predictions=frames,
        actions=[],
        states=[],
        metadata=EpisodeMetadata(
            name="episode_000001",
            robot="real_yaskawa_arm",
            task="real rollout",
            fps=30,
            description="Real robot footage with colors that could trigger the demo heuristics.",
        ),
    )


def test_synthetic_demo_object_and_contact_remain_available(tmp_path: Path) -> None:
    dataset_path = DemoBackend().create(tmp_path / "demo")
    from worldbench.dataset import load_dataset

    demo_episode = load_dataset(dataset_path).episodes[0]

    object_result = ObjectPermanenceMetric().evaluate(demo_episode, demo_episode.predictions)
    contact_result = ContactRealismMetric().evaluate(demo_episode, demo_episode.predictions)

    assert object_result.is_available
    assert object_result.score is not None
    assert contact_result.is_available
    assert contact_result.score is not None


def test_real_style_rollout_marks_object_and_contact_unsupported(tmp_path: Path) -> None:
    episode = _make_real_style_episode(tmp_path)

    object_result = ObjectPermanenceMetric().evaluate(episode, episode.predictions)
    contact_result = ContactRealismMetric().evaluate(episode, episode.predictions)

    assert not object_result.is_available
    assert object_result.score is None
    assert object_result.reason == "Reliable object tracking is unavailable for this rollout."
    assert not contact_result.is_available
    assert contact_result.score is None
    assert contact_result.reason == "Reliable robot and object tracking are unavailable for this rollout."


def test_unavailable_object_and_contact_metrics_are_excluded_from_overall_score() -> None:
    metrics = {
        "visual_similarity": MetricResult(name="visual_similarity", score=80.0),
        "temporal_stability": MetricResult(name="temporal_stability", score=60.0),
        "object_permanence": MetricResult(
            name="object_permanence",
            score=None,
            status="unsupported",
            reason="Reliable object tracking is unavailable for this rollout.",
        ),
        "contact_realism": MetricResult(
            name="contact_realism",
            score=None,
            status="unsupported",
            reason="Reliable robot and object tracking are unavailable for this rollout.",
        ),
    }
    weights = {
        "visual_similarity": 0.25,
        "temporal_stability": 0.20,
        "object_permanence": 0.15,
        "contact_realism": 0.10,
    }

    assert weighted_score(metrics, weights) == pytest.approx(71.11111111111111)


def test_reports_show_na_and_reason_for_object_and_contact(capsys) -> None:
    episode = EpisodeResult(
        episode="episode_000001",
        score=99.7,
        metrics={
            "visual_similarity": MetricResult(name="visual_similarity", score=100.0),
            "temporal_stability": MetricResult(name="temporal_stability", score=99.3),
            "object_permanence": MetricResult(
                name="object_permanence",
                score=None,
                status="unsupported",
                reason="Reliable object tracking is unavailable for this rollout.",
            ),
            "contact_realism": MetricResult(
                name="contact_realism",
                score=None,
                status="unsupported",
                reason="Reliable robot and object tracking are unavailable for this rollout.",
            ),
        },
    )

    payload = EvaluationResult(
        dataset_path="dataset",
        predictions_path="predictions",
        created_at="2026-01-01T00:00:00Z",
        score=99.7,
        metrics=episode.metrics,
        episodes=[episode],
        weights={"visual_similarity": 0.25, "temporal_stability": 0.20, "object_permanence": 0.15, "contact_realism": 0.10},
    )

    payload.print_summary()
    markdown = generate_markdown_report(payload)
    output = capsys.readouterr().out

    assert "Object Permanence" in output
    assert "Contact Realism" in output
    assert "N/A" in output
    assert "Reliable object tracking is unavailable for this rollout." in markdown
    assert "Reliable robot and object tracking are unavailable for this rollout." in markdown
