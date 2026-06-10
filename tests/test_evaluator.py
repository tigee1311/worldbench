from pathlib import Path

from worldbench import WorldBench, evaluate, load_dataset
from worldbench.backends.demo import DemoBackend
from worldbench.runners.evaluator import EvaluationRunner


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


def test_run_and_save_updates_latest_alias(tmp_path: Path) -> None:
    dataset_path = DemoBackend().create(tmp_path / "demo")
    output_root = tmp_path / "runs"

    result_path = EvaluationRunner(dataset_path, predictions=dataset_path / "bad_model").run_and_save(output_root)

    assert result_path.exists()
    assert (output_root / "latest" / "result.json").exists()
