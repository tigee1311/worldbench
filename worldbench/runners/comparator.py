"""Compare WorldBench result JSON files and model folders."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from worldbench.runners.evaluator import EvaluationRunner
from worldbench.schemas import EvaluationResult
from worldbench.utils import markdown_table, read_json, write_json


def load_result(path: str | Path) -> EvaluationResult:
    candidate = Path(path)
    if candidate.is_dir():
        candidate = candidate / "result.json"
    return EvaluationResult.model_validate(read_json(candidate))


def compare_results(
    run_a: str | Path | EvaluationResult, run_b: str | Path | EvaluationResult
) -> dict[str, object]:
    a = load_result(run_a) if not isinstance(run_a, EvaluationResult) else run_a
    b = load_result(run_b) if not isinstance(run_b, EvaluationResult) else run_b
    metrics: dict[str, dict[str, float]] = {}
    for name in sorted(set(a.metrics) | set(b.metrics)):
        metric_a = a.metrics.get(name)
        metric_b = b.metrics.get(name)
        score_a = (
            metric_a.score if metric_a is not None and metric_a.is_available else None
        )
        score_b = (
            metric_b.score if metric_b is not None and metric_b.is_available else None
        )
        delta = None if score_a is None or score_b is None else score_b - score_a
        metrics[name] = {"run_a": score_a, "run_b": score_b, "delta": delta}
    return {
        "run_a_composite_score": a.score,
        "run_b_composite_score": b.score,
        "run_a_score": a.score,
        "run_b_score": b.score,
        "delta": b.score - a.score,
        "metrics": metrics,
        "coverage": {
            "a": a.coverage,
            "b": b.coverage,
        },
        "winner": "run_b"
        if b.score > a.score
        else "run_a"
        if a.score > b.score
        else "tie",
    }


def compare_model_folders(
    dataset_path: str | Path, model_a: str, model_b: str
) -> dict[str, object]:
    """Evaluate and compare two model prediction folders inside a dataset root."""

    dataset = Path(dataset_path)
    result_a = EvaluationRunner(dataset, predictions=dataset / model_a).run()
    result_b = EvaluationRunner(dataset, predictions=dataset / model_b).run()
    return build_comparison(
        result_a=result_a,
        result_b=result_b,
        label_a=model_a,
        label_b=model_b,
        source="model_folders",
        dataset_path=dataset,
        delta_direction="a_minus_b",
    )


def compare_result_files(run_a: str | Path, run_b: str | Path) -> dict[str, object]:
    """Load and compare two saved WorldBench result files or run directories."""

    result_a = load_result(run_a)
    result_b = load_result(run_b)
    return build_comparison(
        result_a=result_a,
        result_b=result_b,
        label_a="run_a",
        label_b="run_b",
        source="result_files",
        dataset_path=None,
        delta_direction="b_minus_a",
    )


def build_comparison(
    result_a: EvaluationResult,
    result_b: EvaluationResult,
    label_a: str,
    label_b: str,
    source: str,
    dataset_path: str | Path | None,
    delta_direction: Literal["a_minus_b", "b_minus_a"],
) -> dict[str, object]:
    """Build a serializable comparison payload."""

    metrics = []
    for name in sorted(set(result_a.metrics) | set(result_b.metrics)):
        metric_a = result_a.metrics.get(name)
        metric_b = result_b.metrics.get(name)
        score_a = (
            metric_a.score if metric_a is not None and metric_a.is_available else None
        )
        score_b = (
            metric_b.score if metric_b is not None and metric_b.is_available else None
        )
        metrics.append(
            {
                "name": name,
                "label": _display_name(name),
                "score_a": score_a,
                "score_b": score_b,
                "delta": None
                if score_a is None or score_b is None
                else _signed_delta(score_a, score_b, delta_direction),
                "winner_delta": None
                if score_a is None or score_b is None
                else abs(score_a - score_b),
            }
        )

    if result_a.score > result_b.score:
        winner = label_a
        loser = label_b
        winner_margin = result_a.score - result_b.score
    elif result_b.score > result_a.score:
        winner = label_b
        loser = label_a
        winner_margin = result_b.score - result_a.score
    else:
        winner = "tie"
        loser = "tie"
        winner_margin = 0.0

    weakest_loser_metrics = _weakest_metrics(
        result_a if loser == label_a else result_b if loser == label_b else result_b
    )
    comparable_metrics = [
        metric for metric in metrics if metric["winner_delta"] is not None
    ]
    comparison = {
        "schema_version": "2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "dataset_path": str(dataset_path) if dataset_path is not None else None,
        "label_a": label_a,
        "label_b": label_b,
        "delta_direction": delta_direction,
        "overall": {
            "label": "Composite Score",
            "score_a": result_a.score,
            "score_b": result_b.score,
            "delta": _signed_delta(result_a.score, result_b.score, delta_direction),
            "winner": winner,
            "loser": loser,
            "winner_margin": winner_margin,
        },
        "metrics": metrics,
        "coverage": {
            "a": result_a.coverage,
            "b": result_b.coverage,
        },
        "largest_gaps": sorted(
            comparable_metrics,
            key=lambda item: float(item["winner_delta"]),
            reverse=True,
        )[:3],
        "conclusion": _comparison_conclusion(loser, weakest_loser_metrics),
        "results": {
            "a": result_a.to_dict(),
            "b": result_b.to_dict(),
        },
    }
    return comparison


def save_comparison_artifacts(
    comparison: dict[str, object],
    output_root: str | Path = ".worldbench/comparisons",
) -> dict[str, Path]:
    """Save comparison JSON/Markdown to a timestamped folder and latest alias."""

    root = Path(output_root)
    run_dir = root / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    latest_dir = root / "latest"
    for directory in (run_dir, latest_dir):
        write_json(directory / "comparison.json", comparison)
        (directory / "comparison.md").write_text(
            generate_comparison_markdown(comparison), encoding="utf-8"
        )
    return {
        "json": latest_dir / "comparison.json",
        "markdown": latest_dir / "comparison.md",
        "timestamped_json": run_dir / "comparison.json",
        "timestamped_markdown": run_dir / "comparison.md",
    }


def generate_comparison_markdown(comparison: dict[str, object]) -> str:
    """Render a saved comparison payload as Markdown."""

    label_a = str(comparison["label_a"])
    label_b = str(comparison["label_b"])
    overall = comparison["overall"]
    assert isinstance(overall, dict)
    metrics = comparison["metrics"]
    assert isinstance(metrics, list)
    largest_gaps = comparison["largest_gaps"]
    assert isinstance(largest_gaps, list)
    coverage = comparison.get("coverage", {})

    rows = [
        [
            str(metric["label"]),
            "N/A"
            if metric["score_a"] is None
            else f"{float(metric['score_a']):.1f}/100",
            "N/A"
            if metric["score_b"] is None
            else f"{float(metric['score_b']):.1f}/100",
            "N/A" if metric["delta"] is None else f"{float(metric['delta']):+.1f}",
        ]
        for metric in metrics
        if metric["delta"] is not None
        or metric["score_a"] is not None
        or metric["score_b"] is not None
    ]
    gap_rows = [
        [str(metric["label"]), f"{float(metric['winner_delta']):.1f}"]
        for metric in largest_gaps
    ]
    winner = str(overall["winner"])
    loser = str(overall["loser"])
    if winner == "tie":
        summary = f"`{label_a}` and `{label_b}` are tied."
    else:
        summary = f"`{winner}` beats `{loser}` by +{float(overall['winner_margin']):.1f} Composite Score points."

    return "\n".join(
        [
            "# WorldBench Checkpoint Comparison",
            "",
            summary,
            "",
            "## Composite Scores",
            "",
            markdown_table(
                ["Run", "Composite Score"],
                [
                    [label_a, _format_optional_score(overall["score_a"])],
                    [label_b, _format_optional_score(overall["score_b"])],
                ],
            ),
            "",
            "## Metric Deltas",
            "",
            markdown_table(["Metric", label_a, label_b, "Delta"], rows),
            "",
            "## Metric Coverage",
            "",
            markdown_table(
                ["Run", "Metrics", "Configured Weight"],
                [
                    [label_a, *_format_coverage(coverage.get("a", {}))],
                    [label_b, *_format_coverage(coverage.get("b", {}))],
                ],
            ),
            "",
            "## Largest Gaps",
            "",
            markdown_table(["Metric", "Gap"], gap_rows),
            "",
            "## Conclusion",
            "",
            str(comparison["conclusion"]),
            "",
        ]
    )


def _signed_delta(
    score_a: float, score_b: float, direction: Literal["a_minus_b", "b_minus_a"]
) -> float:
    return score_a - score_b if direction == "a_minus_b" else score_b - score_a


def _display_name(metric_name: str) -> str:
    return metric_name.replace("_", " ").title()


def _weakest_metrics(result: EvaluationResult) -> set[str]:
    return {
        name
        for name, metric in result.metrics.items()
        if metric.is_available and metric.score is not None and metric.score < 60.0
    }


def _comparison_conclusion(loser: str, weak_metrics: set[str]) -> str:
    if loser == "tie":
        return (
            "Both runs are close; inspect per-episode evidence before choosing a model."
        )
    if {"action_consistency", "contact_realism"} & weak_metrics:
        return f"{loser} produces plausible frames but violates robot action/contact dynamics."
    if "object_permanence" in weak_metrics:
        return f"{loser} loses task-relevant objects during prediction."
    if "temporal_stability" in weak_metrics:
        return f"{loser} has unstable future frames with flicker or sudden jumps."
    if "visual_similarity" in weak_metrics:
        return f"{loser} does not visually match the held-out future frames closely enough."
    return f"{loser} trails on aggregate score; inspect the metric deltas for the dominant gap."


def _format_optional_score(score: float | None) -> str:
    return "N/A" if score is None else f"{float(score):.1f}/100"


def _format_coverage(coverage: object) -> tuple[str, str]:
    if not isinstance(coverage, dict):
        return "legacy artifact", "N/A"
    count = f"{coverage.get('available_metric_count', 0)}/{coverage.get('configured_metric_count', 0)}"
    weight = f"{float(coverage.get('configured_weight_coverage', 0.0)):.0%}"
    return count, weight
