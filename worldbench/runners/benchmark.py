"""Synthetic benchmark suite runner."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from worldbench.runners.evaluator import EvaluationRunner
from worldbench.utils import markdown_table, write_json


FAILURE_MODE_LABELS = {
    "action_consistency": "action mismatch",
    "contact_realism": "pre-contact object motion",
    "object_permanence": "object disappearance",
    "temporal_stability": "temporal flicker",
    "visual_similarity": "visual prediction drift",
}
SCENARIO_FAILURE_METRICS = {
    "action_mismatch": "action_consistency",
    "pre_contact_motion": "contact_realism",
    "object_disappears": "object_permanence",
    "temporal_flicker": "temporal_stability",
}


def run_benchmark_suite(benchmark_root: str | Path) -> dict[str, object]:
    """Evaluate good_model and bad_model across benchmark scenario folders."""

    root = Path(benchmark_root)
    scenario_dirs = [
        path
        for path in sorted(root.iterdir())
        if path.is_dir() and (path / "episode_001").is_dir()
    ]
    if not scenario_dirs:
        raise ValueError(f"No benchmark scenarios found under {root}")

    scenarios = []
    good_scores: list[float] = []
    bad_scores: list[float] = []
    failure_scores: dict[str, list[float]] = {}

    for scenario_dir in scenario_dirs:
        good = EvaluationRunner(scenario_dir, predictions=scenario_dir / "good_model").run()
        bad = EvaluationRunner(scenario_dir, predictions=scenario_dir / "bad_model").run()
        good_scores.append(good.score)
        bad_scores.append(bad.score)
        for name, metric in bad.metrics.items():
            if metric.is_available and metric.score is not None:
                failure_scores.setdefault(name, []).append(metric.score)
        scenarios.append(
            {
                "name": scenario_dir.name,
                "good_model": good.to_dict(),
                "bad_model": bad.to_dict(),
                "delta": good.score - bad.score,
            }
        )

    largest_failure_modes = _largest_failure_modes(scenarios, failure_scores)
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_root": str(root),
        "scenario_count": len(scenarios),
        "good_model_average": sum(good_scores) / len(good_scores),
        "bad_model_average": sum(bad_scores) / len(bad_scores),
        "overall_delta": (sum(good_scores) / len(good_scores)) - (sum(bad_scores) / len(bad_scores)),
        "largest_failure_modes": largest_failure_modes,
        "scenarios": scenarios,
    }


def save_benchmark_artifacts(payload: dict[str, object], output_root: str | Path = ".worldbench/benchmarks") -> dict[str, Path]:
    """Save benchmark JSON/Markdown to timestamped and latest folders."""

    root = Path(output_root)
    run_dir = root / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    latest_dir = root / "latest"
    markdown = generate_benchmark_markdown(payload)
    for directory in (run_dir, latest_dir):
        write_json(directory / "benchmark.json", payload)
        (directory / "benchmark.md").write_text(markdown, encoding="utf-8")
    return {
        "json": latest_dir / "benchmark.json",
        "markdown": latest_dir / "benchmark.md",
        "timestamped_json": run_dir / "benchmark.json",
        "timestamped_markdown": run_dir / "benchmark.md",
    }


def generate_benchmark_markdown(payload: dict[str, object]) -> str:
    scenarios = payload["scenarios"]
    assert isinstance(scenarios, list)
    rows = []
    for scenario in scenarios:
        assert isinstance(scenario, dict)
        good = scenario["good_model"]
        bad = scenario["bad_model"]
        assert isinstance(good, dict)
        assert isinstance(bad, dict)
        rows.append(
            [
                str(scenario["name"]),
                f"{float(good['score']):.1f}/100",
                f"{float(bad['score']):.1f}/100",
                f"{float(scenario['delta']):+.1f}",
            ]
        )

    failure_modes = payload["largest_failure_modes"]
    assert isinstance(failure_modes, list)
    return "\n".join(
        [
            "# WorldBench Demo Benchmark",
            "",
            f"**good_model average:** {float(payload['good_model_average']):.1f}/100",
            f"**bad_model average:** {float(payload['bad_model_average']):.1f}/100",
            f"**overall delta:** +{float(payload['overall_delta']):.1f}",
            "",
            "## Scenario Scores",
            "",
            markdown_table(["Scenario", "good_model", "bad_model", "Delta"], rows),
            "",
            "## Largest Failure Modes",
            "",
            "\n".join(f"- {item}" for item in failure_modes),
            "",
        ]
    )


def _largest_failure_modes(scenarios: list[dict[str, object]], failure_scores: dict[str, list[float]]) -> list[str]:
    scenario_rankings = []
    for scenario in scenarios:
        metric_name = SCENARIO_FAILURE_METRICS.get(str(scenario["name"]))
        if metric_name is None:
            continue
        bad_model = scenario["bad_model"]
        assert isinstance(bad_model, dict)
        metrics = bad_model["metrics"]
        assert isinstance(metrics, dict)
        metric = metrics.get(metric_name)
        if isinstance(metric, dict) and metric.get("score") is not None:
            scenario_rankings.append((FAILURE_MODE_LABELS[metric_name], float(metric["score"])))

    if scenario_rankings:
        ranked = sorted(scenario_rankings, key=lambda item: item[1])
        return [label for label, _ in ranked[:3]]

    ranked = sorted(
        (
            (metric_name, sum(scores) / len(scores))
            for metric_name, scores in failure_scores.items()
            if scores
        ),
        key=lambda item: item[1],
    )
    return [FAILURE_MODE_LABELS.get(name, name.replace("_", " ")) for name, _ in ranked[:3]]
