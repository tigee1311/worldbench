from pathlib import Path

from worldbench import WorldBench, evaluate, load_dataset
from worldbench.backends.demo import DemoBackend


def test_good_model_scores_higher_than_bad_model(tmp_path: Path) -> None:
    dataset_path = DemoBackend().create(tmp_path / "demo")

    good = WorldBench(dataset_path).evaluate(predictions=dataset_path / "good_model")
    bad = WorldBench(dataset_path).evaluate(predictions=dataset_path / "bad_model")

    assert good.score > bad.score
    assert good.metrics["action_consistency"].score > bad.metrics["action_consistency"].score


def test_convenience_api_and_report(tmp_path: Path) -> None:
    dataset_path = DemoBackend().create(tmp_path / "demo")
    dataset = load_dataset(dataset_path)

    result = evaluate(dataset)
    report_path = result.save_report(tmp_path / "report.md")

    assert result.score > 80
    assert report_path.exists()
    assert "WorldBench Evaluation Report" in report_path.read_text(encoding="utf-8")

