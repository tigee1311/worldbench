"""Checkpoint regression evaluation and gating."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from worldbench.runners.evaluator import aggregate_horizon_results, numeric_summary
from worldbench.runners.video import collect_video_files, evaluate_video_pair
from worldbench.utils import read_json, write_json


UNCHANGED_TOLERANCE = 0.01


def evaluate_video_batch(
    ground_truth_root: str | Path,
    predictions_root: str | Path,
    *,
    name: str | None = None,
    skip_context: int = 0,
    output_root: str | Path = ".worldbench/batches",
    output: str | Path | None = None,
) -> tuple[dict[str, Any], dict[str, Path]]:
    """Evaluate one checkpoint prediction folder across many video episodes."""

    gt_root = Path(ground_truth_root)
    pred_root = Path(predictions_root)
    _validate_batch_roots(gt_root, pred_root)

    ground_truth = collect_video_files(gt_root)
    predictions = collect_video_files(pred_root)
    matched, missing, extra = _paired_video_ids(ground_truth, predictions)
    if missing or extra:
        raise ValueError(_format_pairing_error(matched, missing, extra))
    if not matched:
        raise ValueError(f"No supported video files found under {gt_root}.")

    checkpoint_name = name or pred_root.name
    run_dir = Path(output_root) / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    episode_dir = run_dir / "episodes"
    episode_dir.mkdir(parents=True, exist_ok=True)

    episode_payloads: list[dict[str, Any]] = []
    episode_results = []
    for episode_id in matched:
        result = evaluate_video_pair(
            ground_truth[episode_id],
            predictions[episode_id],
            skip_context=skip_context,
            name=episode_id,
        )
        episode_result_path = episode_dir / f"{_safe_artifact_name(episode_id)}.json"
        write_json(episode_result_path, result.to_dict())
        episode_results.extend(result.episodes)
        episode_payloads.append(
            {
                "episode_id": episode_id,
                "ground_truth_path": str(ground_truth[episode_id]),
                "prediction_path": str(predictions[episode_id]),
                "result_path": str(episode_result_path),
                "score": result.score,
                "metrics": {
                    metric_name: metric.model_dump(mode="json")
                    for metric_name, metric in result.metrics.items()
                },
                "horizon": result.horizon,
                "issues": result.issues,
                "main_failure": result.main_failure,
                "result": result.to_dict(),
            }
        )

    payload = {
        "schema_version": "1",
        "result_type": "batch_evaluation",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": checkpoint_name,
        "ground_truth_root": str(gt_root),
        "predictions_root": str(pred_root),
        "skip_context": skip_context,
        "pairing_rule": "Videos are paired by relative POSIX path under each root.",
        "episode_count": len(episode_payloads),
        "episode_ids": matched,
        "episodes": episode_payloads,
        "aggregate": {
            "overall": numeric_summary([float(item["score"]) for item in episode_payloads]),
            "metrics": _aggregate_batch_metrics(episode_payloads),
        },
        "horizon": aggregate_horizon_results(episode_results),
        "worst_episodes": sorted(
            (
                {"episode_id": item["episode_id"], "score": item["score"]}
                for item in episode_payloads
            ),
            key=lambda item: float(item["score"]),
        )[:5],
        "configuration": {
            "skip_context": skip_context,
            "metric_source": "worldbench.runners.evaluator.default_metrics",
            "unchanged_tolerance": UNCHANGED_TOLERANCE,
        },
    }

    paths = save_batch_artifacts(
        payload,
        output_root=output_root,
        output=output,
        run_dir=run_dir,
    )
    return payload, paths


def save_batch_artifacts(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
    output: str | Path | None = None,
    run_dir: str | Path | None = None,
) -> dict[str, Path]:
    """Save batch artifacts to timestamped/latest paths plus optional copy."""

    root = Path(output_root)
    latest = root / "latest"
    timestamped = Path(run_dir) if run_dir is not None else root / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    paths = {
        "json": timestamped / "batch.json",
        "latest_json": latest / "batch.json",
    }
    write_json(paths["json"], payload)
    write_json(paths["latest_json"], payload)
    if output is not None:
        output_path = Path(output)
    else:
        checkpoint_name = payload.get("checkpoint_name")
        output_path = Path(f"{checkpoint_name}.json") if checkpoint_name else None
    if output_path is not None:
        write_json(output_path, payload)
        paths["output_json"] = output_path
    return paths


def load_batch_result(path: str | Path) -> dict[str, Any]:
    candidate = Path(path)
    if candidate.is_dir():
        candidate = candidate / "batch.json"
    payload = read_json(candidate)
    if payload.get("result_type") != "batch_evaluation":
        raise ValueError(f"Expected a batch evaluation result: {candidate}")
    return payload


def build_gate_comparison(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    max_overall_drop: float = 0.0,
    max_metric_drop: float = 0.0,
    max_horizon_drop: float = 0.0,
) -> dict[str, Any]:
    """Compare two batch results and return a PASS/FAIL gate payload."""

    _validate_gate_compatibility(baseline, candidate)

    baseline_overall = _stat_mean(baseline["aggregate"]["overall"])
    candidate_overall = _stat_mean(candidate["aggregate"]["overall"])
    overall_delta = candidate_overall - baseline_overall

    failures: list[dict[str, Any]] = []
    if baseline_overall - candidate_overall > max_overall_drop + UNCHANGED_TOLERANCE:
        failures.append(
            {
                "kind": "overall",
                "baseline": baseline_overall,
                "candidate": candidate_overall,
                "change": overall_delta,
                "allowed_drop": max_overall_drop,
            }
        )

    metric_deltas = _metric_deltas(
        baseline,
        candidate,
        max_metric_drop=max_metric_drop,
        failures=failures,
    )
    horizon_deltas = _horizon_deltas(
        baseline,
        candidate,
        max_horizon_drop=max_horizon_drop,
        failures=failures,
    )
    episode_deltas = _episode_deltas(baseline, candidate)
    status = "FAIL" if failures else "PASS"
    return {
        "schema_version": "1",
        "result_type": "gate_comparison",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "passed": status == "PASS",
        "baseline": {
            "checkpoint_name": baseline.get("checkpoint_name"),
            "score": baseline_overall,
            "episode_count": baseline.get("episode_count"),
        },
        "candidate": {
            "checkpoint_name": candidate.get("checkpoint_name"),
            "score": candidate_overall,
            "episode_count": candidate.get("episode_count"),
        },
        "thresholds": {
            "max_overall_drop": max_overall_drop,
            "max_metric_drop": max_metric_drop,
            "max_horizon_drop": max_horizon_drop,
            "unchanged_tolerance": UNCHANGED_TOLERANCE,
        },
        "overall": {
            "baseline": baseline_overall,
            "candidate": candidate_overall,
            "change": overall_delta,
        },
        "metrics": metric_deltas,
        "horizon": horizon_deltas,
        "episodes": episode_deltas,
        "failure_reasons": failures,
    }


def save_gate_artifacts(
    payload: dict[str, Any],
    output_root: str | Path = ".worldbench/gates",
) -> dict[str, Path]:
    root = Path(output_root)
    run_dir = root / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    latest = root / "latest"
    paths = {
        "json": run_dir / "gate.json",
        "latest_json": latest / "gate.json",
    }
    write_json(paths["json"], payload)
    write_json(paths["latest_json"], payload)
    return paths


def _validate_batch_roots(gt_root: Path, pred_root: Path) -> None:
    if not gt_root.exists():
        raise ValueError(f"Ground-truth root does not exist: {gt_root}")
    if not gt_root.is_dir():
        raise ValueError(f"Ground-truth root is not a directory: {gt_root}")
    if not pred_root.exists():
        raise ValueError(f"Prediction root does not exist: {pred_root}")
    if not pred_root.is_dir():
        raise ValueError(f"Prediction root is not a directory: {pred_root}")


def _paired_video_ids(
    ground_truth: dict[str, Path],
    predictions: dict[str, Path],
) -> tuple[list[str], list[str], list[str]]:
    gt_ids = set(ground_truth)
    pred_ids = set(predictions)
    return (
        sorted(gt_ids & pred_ids),
        sorted(gt_ids - pred_ids),
        sorted(pred_ids - gt_ids),
    )


def _format_pairing_error(matched: list[str], missing: list[str], extra: list[str]) -> str:
    lines = [
        "Cannot evaluate checkpoint.",
        "",
        f"Matched episodes: {len(matched)}",
        f"Missing predictions: {len(missing)}",
        f"Prediction-only episodes: {len(extra)}",
    ]
    if missing:
        lines.extend(["", "Missing:", *missing[:20]])
    if extra:
        lines.extend(["", "Prediction-only:", *extra[:20]])
    return "\n".join(lines)


def _aggregate_batch_metrics(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    metric_names = sorted(
        {
            metric_name
            for episode in episodes
            for metric_name in episode.get("metrics", {})
        }
    )
    aggregate: dict[str, Any] = {}
    for name in metric_names:
        values = []
        unavailable = []
        for episode in episodes:
            metric = episode.get("metrics", {}).get(name)
            if not isinstance(metric, dict):
                continue
            if metric.get("status") == "available" and isinstance(metric.get("score"), (int, float)):
                values.append(float(metric["score"]))
            else:
                unavailable.append(
                    {
                        "episode_id": episode["episode_id"],
                        "reason": metric.get("reason"),
                    }
                )
        if values:
            stats = numeric_summary(values)
            stats.update(
                {
                    "status": "available",
                    "available_count": len(values),
                    "total_count": len(episodes),
                    "unavailable_count": len(unavailable),
                }
            )
            aggregate[name] = stats
        else:
            aggregate[name] = {
                "status": "unsupported",
                "available_count": 0,
                "total_count": len(episodes),
                "reason": "Metric was unavailable for every episode.",
                "unavailable_episodes": unavailable[:20],
            }
    return aggregate


def _validate_gate_compatibility(baseline: dict[str, Any], candidate: dict[str, Any]) -> None:
    baseline_ids = set(_episode_ids(baseline))
    candidate_ids = set(_episode_ids(candidate))
    if baseline_ids != candidate_ids:
        missing = sorted(baseline_ids - candidate_ids)
        extra = sorted(candidate_ids - baseline_ids)
        raise ValueError(
            "Baseline and candidate use different episode sets. "
            f"Missing in candidate: {missing[:10]}; extra in candidate: {extra[:10]}."
        )
    if baseline.get("skip_context") != candidate.get("skip_context"):
        raise ValueError(
            "Baseline and candidate use different skip-context values: "
            f"{baseline.get('skip_context')} vs {candidate.get('skip_context')}."
        )
    if baseline.get("schema_version") != candidate.get("schema_version"):
        raise ValueError(
            "Baseline and candidate batch schemas differ: "
            f"{baseline.get('schema_version')} vs {candidate.get('schema_version')}."
        )


def _episode_ids(payload: dict[str, Any]) -> list[str]:
    ids = payload.get("episode_ids")
    if isinstance(ids, list):
        return [str(item) for item in ids]
    return [str(episode["episode_id"]) for episode in payload.get("episodes", [])]


def _metric_deltas(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    max_metric_drop: float,
    failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    baseline_metrics = baseline["aggregate"]["metrics"]
    candidate_metrics = candidate["aggregate"]["metrics"]
    deltas: list[dict[str, Any]] = []
    for name in sorted(set(baseline_metrics) & set(candidate_metrics)):
        left = baseline_metrics[name]
        right = candidate_metrics[name]
        if left.get("status") != "available" or right.get("status") != "available":
            continue
        baseline_mean = _stat_mean(left)
        candidate_mean = _stat_mean(right)
        change = candidate_mean - baseline_mean
        row = {
            "metric": name,
            "baseline": baseline_mean,
            "candidate": candidate_mean,
            "change": change,
            "available_count_baseline": left.get("available_count"),
            "available_count_candidate": right.get("available_count"),
        }
        deltas.append(row)
        if baseline_mean - candidate_mean > max_metric_drop + UNCHANGED_TOLERANCE:
            failures.append(
                {
                    "kind": "metric",
                    "metric": name,
                    "baseline": baseline_mean,
                    "candidate": candidate_mean,
                    "change": change,
                    "allowed_drop": max_metric_drop,
                }
            )
    return deltas


def _horizon_deltas(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    max_horizon_drop: float,
    failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    deltas: list[dict[str, Any]] = []
    baseline_horizon = baseline.get("horizon", {})
    candidate_horizon = candidate.get("horizon", {})
    for label in sorted(set(baseline_horizon) & set(candidate_horizon), key=_horizon_key):
        base_metrics = baseline_horizon[label].get("metrics", {})
        cand_metrics = candidate_horizon[label].get("metrics", {})
        for metric in sorted(set(base_metrics) & set(cand_metrics)):
            baseline_mean = _stat_mean(base_metrics[metric])
            candidate_mean = _stat_mean(cand_metrics[metric])
            change = candidate_mean - baseline_mean
            row = {
                "horizon": label,
                "metric": metric,
                "baseline": baseline_mean,
                "candidate": candidate_mean,
                "change": change,
                "baseline_count": base_metrics[metric].get("count"),
                "candidate_count": cand_metrics[metric].get("count"),
            }
            deltas.append(row)
            if baseline_mean - candidate_mean > max_horizon_drop + UNCHANGED_TOLERANCE:
                failures.append(
                    {
                        "kind": "horizon",
                        "horizon": label,
                        "metric": metric,
                        "baseline": baseline_mean,
                        "candidate": candidate_mean,
                        "change": change,
                        "allowed_drop": max_horizon_drop,
                    }
                )
    return deltas


def _episode_deltas(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    baseline_map = {episode["episode_id"]: episode for episode in baseline["episodes"]}
    candidate_map = {episode["episode_id"]: episode for episode in candidate["episodes"]}
    deltas = []
    for episode_id in sorted(baseline_map):
        baseline_score = float(baseline_map[episode_id]["score"])
        candidate_score = float(candidate_map[episode_id]["score"])
        deltas.append(
            {
                "episode_id": episode_id,
                "baseline": baseline_score,
                "candidate": candidate_score,
                "change": candidate_score - baseline_score,
            }
        )
    improved = [item for item in deltas if item["change"] > UNCHANGED_TOLERANCE]
    regressed = [item for item in deltas if item["change"] < -UNCHANGED_TOLERANCE]
    unchanged = [
        item for item in deltas if abs(float(item["change"])) <= UNCHANGED_TOLERANCE
    ]
    return {
        "improved_count": len(improved),
        "regressed_count": len(regressed),
        "unchanged_count": len(unchanged),
        "deltas": deltas,
        "worst_regressions": sorted(deltas, key=lambda item: float(item["change"]))[:5],
        "best_improvements": sorted(
            deltas,
            key=lambda item: float(item["change"]),
            reverse=True,
        )[:5],
    }


def _stat_mean(payload: dict[str, Any]) -> float:
    value = payload.get("mean")
    if not isinstance(value, (int, float)):
        raise ValueError("Cannot compare aggregate without a numeric mean.")
    return float(value)


def _horizon_key(label: str) -> int:
    if label.startswith("t+"):
        try:
            return int(label[2:])
        except ValueError:
            return 0
    return 0


def _safe_artifact_name(episode_id: str) -> str:
    safe = []
    for char in episode_id:
        if char.isalnum() or char in {"-", "_", "."}:
            safe.append(char)
        else:
            safe.append("_")
    return "".join(safe).strip("._") or "episode"
