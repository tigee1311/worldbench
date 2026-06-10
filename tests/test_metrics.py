from pathlib import Path

from worldbench.backends.demo import DemoBackend
from worldbench.dataset import load_dataset
from worldbench.metrics import ActionConsistencyMetric, ObjectPermanenceMetric, VisualSimilarityMetric
from worldbench.runners.evaluator import resolve_prediction_frames


def test_good_predictions_have_high_visual_similarity(tmp_path: Path) -> None:
    dataset_path = DemoBackend().create(tmp_path / "demo")
    dataset = load_dataset(dataset_path)
    episode = dataset.episodes[0]
    predictions = resolve_prediction_frames(episode, dataset_path / "good_model")

    result = VisualSimilarityMetric().evaluate(episode, predictions)

    assert result.score > 90


def test_bad_predictions_fail_action_consistency(tmp_path: Path) -> None:
    dataset_path = DemoBackend().create(tmp_path / "demo")
    dataset = load_dataset(dataset_path)
    episode = dataset.episodes[0]
    predictions = resolve_prediction_frames(episode, dataset_path / "bad_model")

    result = ActionConsistencyMetric().evaluate(episode, predictions)

    assert result.score < 60
    assert result.details["failed_steps"] > 0
    assert result.details["mismatch_percentage"] > 0
    assert result.details["commanded_vs_predicted"]


def test_bad_predictions_penalize_object_permanence(tmp_path: Path) -> None:
    dataset_path = DemoBackend().create(tmp_path / "demo")
    dataset = load_dataset(dataset_path)
    episode = dataset.episodes[0]
    bad_predictions = resolve_prediction_frames(episode, dataset_path / "bad_model")
    good_predictions = resolve_prediction_frames(episode, dataset_path / "good_model")

    bad = ObjectPermanenceMetric().evaluate(episode, bad_predictions)
    good = ObjectPermanenceMetric().evaluate(episode, good_predictions)

    assert good.score > bad.score
    assert "disappearance_percentage" in bad.details
