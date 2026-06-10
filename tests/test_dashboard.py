from pathlib import Path

from worldbench.backends.demo import DemoBackend
from worldbench.dashboard import build_dashboard_html, build_frame_index
from worldbench.runners.evaluator import EvaluationRunner


def test_dashboard_html_builds_without_streamlit(tmp_path: Path) -> None:
    dataset_path = DemoBackend().create(tmp_path / "demo")
    result = EvaluationRunner(dataset_path, predictions=dataset_path / "good_model").run()

    html = build_dashboard_html(result, build_frame_index(result))

    assert "WorldBench Dashboard" in html
    assert "streamlit" not in html.lower()
    assert "/frame?episode=" in html

