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


def compare_results(run_a: str | Path | EvaluationResult, run_b: str | Path | EvaluationResult) -> dict[str, object]:
    a = load_result(run_a) if not isinstance(run_a, EvaluationResult) else run_a
    b = load_result(run_b) if not isinstance(run_b, EvaluationResult) else run_b
    metrics: dict[str, dict[str, float]] = {}
    for name in sorted(set(a.metrics) | set(b.metrics)):
        score_a = a.metrics[name].score if name in a.metrics else 0.0
        score_b = b.metrics[name].score if name in b.metrics else 0.0
        metrics[name] = {"run_a": score_a, "run_b": score_b, "delta": score_b - score_a}
    return {
        "run_a_score": a.score,
        "run_b_score": b.score,
        "delta": b.score - a.score,
        "metrics": metrics,
        "winner": "run_b" if b.score > a.score else "run_a" if a.score > b.score else "tie",
    }


def compare_model_folders(dataset_path: str | Path, model_a: str, model_b: str) -> dict[str, object]:
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
        score_a = result_a.metrics[name].score if name in result_a.metrics else 0.0
        score_b = result_b.metrics[name].score if name in result_b.metrics else 0.0
        metrics.append(
            {
                "name": name,
                "label": _display_name(name),
                "score_a": score_a,
                "score_b": score_b,
                "delta": _signed_delta(score_a, score_b, delta_direction),
                "winner_delta": abs(score_a - score_b),
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

    weakest_loser_metrics = _weakest_metrics(result_a if loser == label_a else result_b if loser == label_b else result_b)
    comparison = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "dataset_path": str(dataset_path) if dataset_path is not None else None,
        "label_a": label_a,
        "label_b": label_b,
        "delta_direction": delta_direction,
        "overall": {
            "score_a": result_a.score,
            "score_b": result_b.score,
            "delta": _signed_delta(result_a.score, result_b.score, delta_direction),
            "winner": winner,
            "loser": loser,
            "winner_margin": winner_margin,
        },
        "metrics": metrics,
        "largest_gaps": sorted(metrics, key=lambda item: item["winner_delta"], reverse=True)[:3],
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
        (directory / "comparison.md").write_text(generate_comparison_markdown(comparison), encoding="utf-8")
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

    rows = [
        [
            str(metric["label"]),
            f"{float(metric['score_a']):.1f}/100",
            f"{float(metric['score_b']):.1f}/100",
            f"{float(metric['delta']):+.1f}",
        ]
        for metric in metrics
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
        summary = f"`{winner}` beats `{loser}` by +{float(overall['winner_margin']):.1f} overall points."

    return "\n".join(
        [
            "# WorldBench Model Comparison",
            "",
            summary,
            "",
            "## Overall",
            "",
            markdown_table(
                ["Run", "Overall"],
                [
                    [label_a, f"{float(overall['score_a']):.1f}/100"],
                    [label_b, f"{float(overall['score_b']):.1f}/100"],
                ],
            ),
            "",
            "## Metric Deltas",
            "",
            markdown_table(["Metric", label_a, label_b, "Delta"], rows),
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


def _signed_delta(score_a: float, score_b: float, direction: Literal["a_minus_b", "b_minus_a"]) -> float:
    return score_a - score_b if direction == "a_minus_b" else score_b - score_a


def _display_name(metric_name: str) -> str:
    return metric_name.replace("_", " ").title()


def _weakest_metrics(result: EvaluationResult) -> set[str]:
    return {name for name, metric in result.metrics.items() if metric.score < 60.0}


def _comparison_conclusion(loser: str, weak_metrics: set[str]) -> str:
    if loser == "tie":
        return "Both runs are close; inspect per-episode evidence before choosing a model."
    if {"action_consistency", "contact_realism"} & weak_metrics:
        return f"{loser} produces plausible frames but violates robot action/contact dynamics."
    if "object_permanence" in weak_metrics:
        return f"{loser} loses task-relevant objects during prediction."
    if "temporal_stability" in weak_metrics:
        return f"{loser} has unstable future frames with flicker or sudden jumps."
    if "visual_similarity" in weak_metrics:
        return f"{loser} does not visually match the held-out future frames closely enough."
    return f"{loser} trails on aggregate score; inspect the metric deltas for the dominant gap."
