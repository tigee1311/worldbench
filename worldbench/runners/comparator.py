"""Compare WorldBench result JSON files."""

from __future__ import annotations

from pathlib import Path

from worldbench.schemas import EvaluationResult
from worldbench.utils import read_json


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

