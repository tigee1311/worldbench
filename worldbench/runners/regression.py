"""Checkpoint regression evaluation and gating."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any

from worldbench.config import WorldBenchConfig, coverage_for, default_config
from worldbench.runners.evaluator import aggregate_horizon_results, numeric_summary
from worldbench.runners.video import collect_video_files, evaluate_video_pair
from worldbench.utils import read_json, write_json
from worldbench.version import RESULT_SCHEMA_VERSION, WORLD_BENCH_VERSION


UNCHANGED_TOLERANCE = 0.01


def evaluate_video_batch(
    ground_truth_root: str | Path,
    predictions_root: str | Path,
    *,
    name: str | None = None,
    skip_context: int = 0,
    output_root: str | Path = ".worldbench/batches",
    output: str | Path | None = None,
    config: WorldBenchConfig | None = None,
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

    effective_config = config or default_config()
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
            config=effective_config,
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

    aggregate_metrics = _aggregate_batch_metrics(episode_payloads)
    available_metrics = [
        name
        for name, stats in aggregate_metrics.items()
        if stats.get("status") == "available"
    ]
    coverage = coverage_for(
        effective_config.enabled_metrics,
        effective_config.configured_weights,
        available_metrics,
    )
    payload = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "result_type": "batch_evaluation",
        "worldbench_version": WORLD_BENCH_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": checkpoint_name,
        "ground_truth_root": str(gt_root),
        "predictions_root": str(pred_root),
        "skip_context": skip_context,
        "pairing_rule": "Videos are paired by relative POSIX path under each root.",
        "episode_count": len(episode_payloads),
        "episode_ids": matched,
        "dataset_identifier": _dataset_identifier(ground_truth),
        "episodes": episode_payloads,
        "aggregate": {
            "composite_score": numeric_summary(
                [float(item["score"]) for item in episode_payloads]
            ),
            "overall": numeric_summary(
                [float(item["score"]) for item in episode_payloads]
            ),
            "metrics": aggregate_metrics,
        },
        "coverage": coverage,
        "enabled_metrics": effective_config.enabled_metrics,
        "required_metrics": effective_config.required_metrics,
        "configured_weights": effective_config.configured_weights,
        "effective_normalized_weights": coverage["effective_normalized_weights"],
        "configuration_hash": effective_config.configuration_hash,
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
            **effective_config.model_dump(mode="json"),
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
    timestamped = (
        Path(run_dir)
        if run_dir is not None
        else root / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    )
    paths = {
        "json": timestamped / "batch.json",
        "latest_json": latest / "batch.json",
        "markdown": timestamped / "report.md",
        "latest_markdown": latest / "report.md",
    }
    write_json(paths["json"], payload)
    write_json(paths["latest_json"], payload)
    paths["markdown"].parent.mkdir(parents=True, exist_ok=True)
    paths["markdown"].write_text(_batch_markdown(payload), encoding="utf-8")
    paths["latest_markdown"].parent.mkdir(parents=True, exist_ok=True)
    paths["latest_markdown"].write_text(_batch_markdown(payload), encoding="utf-8")
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
    return _with_legacy_compatibility(payload)


def build_gate_comparison(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    max_overall_drop: float = 0.0,
    max_metric_drop: float = 0.0,
    max_horizon_drop: float = 0.0,
    required_metrics: list[str] | None = None,
    min_metric_count: int = 1,
    min_metric_coverage: float = 0.0,
    min_configured_weight_coverage: float = 0.0,
    strict_config_match: bool = True,
    max_episode_regressions: int | None = None,
    min_composite_improvement: float | None = None,
) -> dict[str, Any]:
    """Compare two batch results and return a PASS/FAIL gate payload."""

    baseline = _with_legacy_compatibility(baseline)
    candidate = _with_legacy_compatibility(candidate)
    warnings = _validate_gate_compatibility(
        baseline, candidate, strict_config_match=strict_config_match
    )

    baseline_overall = _stat_mean(baseline["aggregate"]["overall"])
    candidate_overall = _stat_mean(candidate["aggregate"]["overall"])
    overall_delta = candidate_overall - baseline_overall

    failures: list[dict[str, Any]] = []
    coverage_failures, coverage_warnings = _coverage_failures(
        baseline,
        candidate,
        required_metrics=required_metrics or [],
        min_metric_count=min_metric_count,
        min_metric_coverage=min_metric_coverage,
        min_configured_weight_coverage=min_configured_weight_coverage,
        strict_config_match=strict_config_match,
    )
    failures.extend(coverage_failures)
    warnings.extend(coverage_warnings)
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
    if (
        max_episode_regressions is not None
        and episode_deltas["regressed_count"] > max_episode_regressions
    ):
        failures.append(
            {
                "kind": "episode_regressions",
                "actual": episode_deltas["regressed_count"],
                "allowed": max_episode_regressions,
            }
        )
    if (
        min_composite_improvement is not None
        and overall_delta + UNCHANGED_TOLERANCE < min_composite_improvement
    ):
        failures.append(
            {
                "kind": "composite_improvement",
                "baseline": baseline_overall,
                "candidate": candidate_overall,
                "change": overall_delta,
                "required_improvement": min_composite_improvement,
            }
        )
    status = "FAIL" if failures else "PASS"
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "result_type": "gate_comparison",
        "worldbench_version": WORLD_BENCH_VERSION,
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
            "required_metrics": required_metrics or [],
            "min_metric_count": min_metric_count,
            "min_metric_coverage": min_metric_coverage,
            "min_configured_weight_coverage": min_configured_weight_coverage,
            "strict_config_match": strict_config_match,
            "max_episode_regressions": max_episode_regressions,
            "min_composite_improvement": min_composite_improvement,
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
        "coverage": candidate["coverage"],
        "warnings": warnings,
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
        "markdown": run_dir / "gate.md",
        "latest_markdown": latest / "gate.md",
    }
    write_json(paths["json"], payload)
    write_json(paths["latest_json"], payload)
    paths["markdown"].parent.mkdir(parents=True, exist_ok=True)
    paths["markdown"].write_text(_gate_markdown(payload), encoding="utf-8")
    paths["latest_markdown"].parent.mkdir(parents=True, exist_ok=True)
    paths["latest_markdown"].write_text(_gate_markdown(payload), encoding="utf-8")
    return paths


def _batch_markdown(payload: dict[str, Any]) -> str:
    stats = payload["aggregate"]["overall"]
    coverage = payload.get("coverage", {})
    available = coverage.get("available_metrics", [])
    unsupported = coverage.get("unsupported_metrics", [])
    return "\n".join(
        [
            "# WorldBench Checkpoint Evaluation",
            "",
            f"**Checkpoint:** {payload.get('checkpoint_name')}",
            f"**Composite Score:** {float(stats['mean']):.2f}/100",
            f"**Episodes:** {payload.get('episode_count')}",
            f"**Metric coverage:** {coverage.get('available_metric_count', 0)} of {coverage.get('configured_metric_count', 0)} configured metrics",
            f"**Configured weight coverage:** {float(coverage.get('configured_weight_coverage', 0.0)):.0%}",
            "",
            "## Available Metrics",
            *(
                [f"- {name.replace('_', ' ').title()}" for name in available]
                or ["- None"]
            ),
            "",
            "## Unsupported Metrics",
            *(
                [f"- {name.replace('_', ' ').title()}" for name in unsupported]
                or ["- None"]
            ),
            "",
            f"Configuration hash: `{payload.get('configuration_hash') or 'legacy artifact'}`",
            "",
        ]
    )


def _gate_markdown(payload: dict[str, Any]) -> str:
    overall = payload["overall"]
    episodes = payload["episodes"]
    coverage = payload.get("coverage", {})
    return "\n".join(
        [
            f"# WorldBench Gate: {payload['status']}",
            "",
            f"- Composite change: {float(overall['change']):+.2f}",
            f"- Episodes improved: {episodes['improved_count']}",
            f"- Episodes regressed: {episodes['regressed_count']}",
            f"- Metric coverage: {coverage.get('available_metric_count', 0)} of {coverage.get('configured_metric_count', 0)}",
            f"- Configured weight coverage: {float(coverage.get('configured_weight_coverage', 0.0)):.0%}",
            "",
            "## Failures",
            *(
                f"- {_failure_display_label(item)}: {item}"
                for item in payload.get("failure_reasons", [])
            ),
            *(["- None"] if not payload.get("failure_reasons") else []),
            "",
        ]
    )


def _with_legacy_compatibility(payload: dict[str, Any]) -> dict[str, Any]:
    """Add schema-v2 comparison metadata without rewriting a loaded artifact."""

    migrated = dict(payload)
    aggregate = dict(migrated.get("aggregate", {}))
    if "composite_score" not in aggregate and "overall" in aggregate:
        aggregate["composite_score"] = aggregate["overall"]
    migrated["aggregate"] = aggregate
    metrics = aggregate.get("metrics", {})
    available = sorted(
        name
        for name, item in metrics.items()
        if isinstance(item, dict) and item.get("status") == "available"
    )
    configured = list(migrated.get("enabled_metrics") or sorted(metrics))
    configured_weights = migrated.get("configured_weights")
    if not isinstance(configured_weights, dict):
        defaults = default_config().configured_weights
        configured_weights = {name: defaults.get(name, 0.0) for name in configured}
    migrated["enabled_metrics"] = configured
    migrated["configured_weights"] = configured_weights
    migrated.setdefault("required_metrics", [])
    migrated.setdefault(
        "coverage", coverage_for(configured, configured_weights, available)
    )
    migrated.setdefault(
        "effective_normalized_weights",
        migrated["coverage"].get("effective_normalized_weights", {}),
    )
    return migrated


def _failure_display_label(failure: dict[str, Any]) -> str:
    kind = str(failure.get("kind", "failure"))
    if kind == "overall":
        return "Composite Score"
    if kind == "composite_improvement":
        return "Composite Score improvement"
    return kind.replace("_", " ").title()


def _coverage_failures(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    required_metrics: list[str],
    min_metric_count: int,
    min_metric_coverage: float,
    min_configured_weight_coverage: float,
    strict_config_match: bool,
) -> tuple[list[dict[str, Any]], list[str]]:
    failures: list[dict[str, Any]] = []
    warnings: list[str] = []
    base_coverage = baseline["coverage"]
    candidate_coverage = candidate["coverage"]
    base_available = set(base_coverage.get("available_metrics", []))
    candidate_available = set(candidate_coverage.get("available_metrics", []))

    disappeared = sorted(base_available - candidate_available)
    if disappeared:
        failures.append({"kind": "metric_disappeared", "metrics": disappeared})

    all_required = sorted(
        set(required_metrics)
        | set(baseline.get("required_metrics", []))
        | set(candidate.get("required_metrics", []))
    )
    missing_required = sorted(set(all_required) - candidate_available)
    if missing_required:
        failures.append({"kind": "required_metric", "metrics": missing_required})

    available_count = int(candidate_coverage.get("available_metric_count", 0))
    if available_count < min_metric_count:
        failures.append(
            {
                "kind": "metric_count",
                "actual": available_count,
                "minimum": min_metric_count,
            }
        )
    metric_coverage = float(candidate_coverage.get("metric_coverage", 0.0))
    if metric_coverage + 1e-12 < min_metric_coverage:
        failures.append(
            {
                "kind": "metric_coverage",
                "actual": metric_coverage,
                "minimum": min_metric_coverage,
            }
        )
    weight_coverage = float(candidate_coverage.get("configured_weight_coverage", 0.0))
    if weight_coverage + 1e-12 < min_configured_weight_coverage:
        failures.append(
            {
                "kind": "configured_weight_coverage",
                "actual": weight_coverage,
                "minimum": min_configured_weight_coverage,
            }
        )

    mismatch_messages: list[str] = []
    if baseline.get("schema_version") != candidate.get("schema_version"):
        mismatch_messages.append("result schema versions differ")
    if set(baseline.get("enabled_metrics", [])) != set(
        candidate.get("enabled_metrics", [])
    ):
        mismatch_messages.append("enabled metric sets differ")
    if baseline.get("configured_weights") != candidate.get("configured_weights"):
        mismatch_messages.append("configured metric weights differ")
    base_hash = baseline.get("configuration_hash")
    candidate_hash = candidate.get("configuration_hash")
    if base_hash and candidate_hash and base_hash != candidate_hash:
        mismatch_messages.append("configuration hashes differ")
    elif not base_hash or not candidate_hash:
        warnings.append(
            "Configuration hash is unavailable in one or both legacy artifacts; metric sets and weights were inferred."
        )

    base_horizons = set(baseline.get("horizon", {}))
    candidate_horizons = set(candidate.get("horizon", {}))
    if base_horizons != candidate_horizons:
        mismatch_messages.append("evaluated horizon sets differ")

    for name in sorted(base_available & candidate_available):
        left = baseline["aggregate"]["metrics"][name]
        right = candidate["aggregate"]["metrics"][name]
        if left.get("available_count") != right.get("available_count"):
            mismatch_messages.append(f"available episode counts differ for {name}")

    if mismatch_messages:
        if strict_config_match:
            failures.append(
                {"kind": "configuration_mismatch", "details": mismatch_messages}
            )
        else:
            warnings.extend(
                f"Configuration warning: {message}." for message in mismatch_messages
            )
    return failures, warnings


def _dataset_identifier(files: dict[str, Path]) -> str:
    digest = hashlib.sha256()
    for episode_id, path in sorted(files.items()):
        digest.update(episode_id.encode("utf-8"))
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


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


def _format_pairing_error(
    matched: list[str], missing: list[str], extra: list[str]
) -> str:
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
            if metric.get("status") == "available" and isinstance(
                metric.get("score"), (int, float)
            ):
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


def _validate_gate_compatibility(
    baseline: dict[str, Any], candidate: dict[str, Any], *, strict_config_match: bool
) -> list[str]:
    warnings: list[str] = []
    if (
        baseline.get("schema_version") != RESULT_SCHEMA_VERSION
        or candidate.get("schema_version") != RESULT_SCHEMA_VERSION
    ):
        warnings.append(
            "This result predates schema v2, so full configuration compatibility could not be verified."
        )
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
        message = (
            "Baseline and candidate use different skip-context values: "
            f"{baseline.get('skip_context')} vs {candidate.get('skip_context')}."
        )
        if strict_config_match:
            raise ValueError(message)
        warnings.append(message)
    base_dataset = baseline.get("dataset_identifier")
    candidate_dataset = candidate.get("dataset_identifier")
    if base_dataset and candidate_dataset and base_dataset != candidate_dataset:
        raise ValueError(
            "Baseline and candidate use different ground-truth dataset content."
        )
    if not base_dataset or not candidate_dataset:
        warnings.append(
            "Dataset content identity is unavailable in one or both legacy artifacts; episode IDs were matched."
        )
    if (
        baseline.get("schema_version") != candidate.get("schema_version")
        and not strict_config_match
    ):
        warnings.append(
            "Baseline and candidate originated from different schema versions; compatibility fields were inferred."
        )
    return warnings


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
    for label in sorted(
        set(baseline_horizon) & set(candidate_horizon), key=_horizon_key
    ):
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


def _episode_deltas(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    baseline_map = {episode["episode_id"]: episode for episode in baseline["episodes"]}
    candidate_map = {
        episode["episode_id"]: episode for episode in candidate["episodes"]
    }
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
