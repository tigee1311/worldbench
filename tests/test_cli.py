from pathlib import Path

from click.testing import CliRunner

from worldbench.backends.demo import DemoBackend
from worldbench.cli import app
from worldbench.dataset import validate_dataset
from worldbench.utils import read_json


def test_compare_models_command_saves_latest_artifacts(tmp_path: Path, monkeypatch) -> None:
    dataset_path = DemoBackend().create(tmp_path / "demo")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["compare", str(dataset_path), "--models", "good_model", "bad_model"])

    assert result.exit_code == 0, result.output
    assert "good_model" in result.output
    assert "bad_model" in result.output
    assert "Largest gaps" in result.output

    comparison_path = tmp_path / ".worldbench" / "comparisons" / "latest" / "comparison.json"
    report_path = tmp_path / ".worldbench" / "comparisons" / "latest" / "comparison.md"
    assert comparison_path.exists()
    assert report_path.exists()

    comparison = read_json(comparison_path)
    assert comparison["overall"]["score_a"] > comparison["overall"]["score_b"]
    assert comparison["overall"]["winner"] == "good_model"
    assert "action/contact dynamics" in comparison["conclusion"]


def test_import_lerobot_demo_command_creates_valid_dataset(tmp_path: Path) -> None:
    output_path = tmp_path / "lerobot_push_cube"

    result = CliRunner().invoke(app, ["import-lerobot", "--demo", "--out", str(output_path)])

    assert result.exit_code == 0, result.output
    assert "Experimental LeRobot-style import" in result.output
    assert (output_path / "episode_001" / "frames" / "000.png").exists()
    assert (output_path / "episode_001" / "actions.json").exists()
    assert validate_dataset(output_path).is_valid


def test_benchmark_demo_command_saves_latest_artifacts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["benchmark", "--demo"])

    assert result.exit_code == 0, result.output
    assert "WorldBench Demo Benchmark" in result.output
    assert "good_model average" in result.output
    assert (tmp_path / "benchmarks" / "push_cube" / "episode_001" / "frames" / "000.png").exists()

    benchmark_path = tmp_path / ".worldbench" / "benchmarks" / "latest" / "benchmark.json"
    report_path = tmp_path / ".worldbench" / "benchmarks" / "latest" / "benchmark.md"
    assert benchmark_path.exists()
    assert report_path.exists()

    benchmark = read_json(benchmark_path)
    assert benchmark["scenario_count"] == 5
    assert benchmark["good_model_average"] > benchmark["bad_model_average"]
    assert benchmark["largest_failure_modes"]
