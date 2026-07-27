from __future__ import annotations

from pathlib import Path

from benchmarks.performance import run_benchmarks, write_report
from research_metrics.corruption_harness import (
    run_harness,
)
from research_metrics.corruption_harness import (
    write_report as write_research_report,
)
from worldbench.utils import read_json


def test_metric_research_harness_runs_and_writes_small_artifacts(
    tmp_path: Path,
) -> None:
    payload = run_harness(
        severities=(0.0, 0.5), repeats=1, frame_count=6, size=(24, 24)
    )

    assert payload["status"] == "research_only"
    assert payload["production_metrics_changed"] is False
    assert "frame_freeze" in payload["corruptions"]
    assert "current_visual_similarity" in payload["metrics"]

    json_path, markdown_path = write_research_report(payload, tmp_path)
    assert read_json(json_path)["status"] == "research_only"
    assert "Production metrics were not changed" in markdown_path.read_text(
        encoding="utf-8"
    )


def test_performance_harness_runs_without_strict_timing_gate(tmp_path: Path) -> None:
    payload = run_benchmarks(quick=True)

    assert payload["status"] == "informational"
    assert payload["strict_timing_gate"] is False
    assert "short_64" in payload["cases"]
    assert "batch_episode_evaluation" in payload["cases"]

    output = write_report(payload, tmp_path / "perf.json")
    assert read_json(output)["strict_timing_gate"] is False
