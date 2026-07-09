"""WorldBench evaluation orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import numpy as np

from worldbench.dataset import Episode, RolloutDataset, load_dataset
from worldbench.metrics import (
    ActionConsistencyMetric,
    ContactRealismMetric,
    ObjectPermanenceMetric,
    TemporalStabilityMetric,
    VisualSimilarityMetric,
)
from worldbench.schemas import EpisodeResult, EvaluationResult, MetricResult
from worldbench.utils import clamp, list_image_files, write_json

DEFAULT_WEIGHTS = {
    "visual_similarity": 0.25,
    "action_consistency": 0.30,
    "temporal_stability": 0.20,
    "object_permanence": 0.15,
    "contact_realism": 0.10,
}


class EvaluatorMetric(Protocol):
    name: str

    def evaluate(self, episode: Episode, prediction_frames: list[Path]) -> MetricResult:
        ...


def default_metrics() -> list[EvaluatorMetric]:
    return [
        VisualSimilarityMetric(),
        ActionConsistencyMetric(),
        TemporalStabilityMetric(),
        ObjectPermanenceMetric(),
        ContactRealismMetric(),
    ]


class EvaluationRunner:
    """Run WorldBench metrics over a rollout dataset and prediction folder."""

    def __init__(self, dataset: RolloutDataset | str | Path, predictions: str | Path | None = None) -> None:
        self.dataset = load_dataset(dataset) if isinstance(dataset, (str, Path)) else dataset
        self.predictions = Path(predictions) if predictions is not None else None

    def run(self, metrics: list[EvaluatorMetric] | None = None, weights: dict[str, float] | None = None) -> EvaluationResult:
        selected_metrics = metrics or default_metrics()
        selected_weights = weights or DEFAULT_WEIGHTS
        episode_results: list[EpisodeResult] = []
        global_issues: list[str] = []

        for episode in self._episodes_to_evaluate():
            prediction_frames = resolve_prediction_frames(episode, self.predictions)
            metric_results: dict[str, MetricResult] = {}
            episode_issues: list[str] = []

            if not prediction_frames:
                issue = f"No predictions found for {episode.name}."
                episode_issues.append(issue)
                global_issues.append(issue)

            if prediction_frames and len(prediction_frames) != len(episode.frames):
                issue = (
                    f"{episode.name} has {len(episode.frames)} ground-truth frame(s) but "
                    f"{len(prediction_frames)} prediction frame(s); scoring aligned prefix."
                )
                episode_issues.append(issue)
                global_issues.append(issue)

            for metric in selected_metrics:
                result = metric.evaluate(episode, prediction_frames)
                metric_results[metric.name] = result
                episode_issues.extend(result.issues)
                if not result.is_available and result.reason:
                    episode_issues.append(result.reason)
                    global_issues.append(f"{episode.name}: {result.reason}")

            episode_score = weighted_score(metric_results, selected_weights)
            episode_horizon = compute_episode_horizon(
                episode,
                prediction_frames,
                selected_metrics,
                selected_weights,
            )
            episode_results.append(
                EpisodeResult(
                    episode=episode.name,
                    score=episode_score,
                    metrics=metric_results,
                    horizon=episode_horizon,
                    issues=episode_issues,
                )
            )

        aggregate_metrics = aggregate_metric_results(episode_results, selected_metrics)
        overall = weighted_score(aggregate_metrics, selected_weights)
        main_failure = infer_main_failure(aggregate_metrics)
        return EvaluationResult(
            dataset_path=str(self.dataset.path),
            predictions_path=str(self.predictions) if self.predictions is not None else None,
            created_at=datetime.now(timezone.utc).isoformat(),
            score=overall,
            metrics=aggregate_metrics,
            episodes=episode_results,
            horizon=aggregate_horizon_results(episode_results),
            weights=selected_weights,
            issues=global_issues,
            main_failure=main_failure,
        )

    def run_and_save(self, output_root: str | Path = ".worldbench/runs") -> Path:
        result = self.run()
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        root = Path(output_root)
        output_dir = root / timestamp
        output_path = output_dir / "result.json"
        write_json(output_path, result.to_dict())
        latest_dir = root / "latest"
        write_json(latest_dir / "result.json", result.to_dict())
        return output_path

    def _episodes_to_evaluate(self) -> list[Episode]:
        if self.predictions is None:
            return list(self.dataset)
        if self.predictions.name == "predictions" and self.predictions.parent.name.startswith("episode_"):
            requested = self.predictions.parent.name
            return [episode for episode in self.dataset if episode.name == requested]
        return list(self.dataset)


def resolve_prediction_frames(episode: Episode, predictions: Path | None) -> list[Path]:
    """Resolve predictions for an episode from flexible WorldBench prediction layouts."""

    if predictions is None:
        return episode.predictions

    root = Path(predictions)
    if not root.exists():
        return []

    direct_images = list_image_files(root)
    if direct_images:
        if root.name == "predictions" and root.parent.name.startswith("episode_") and root.parent.name != episode.name:
            return []
        return direct_images

    episode_dir = root / episode.name
    if (episode_dir / "predictions").is_dir():
        return list_image_files(episode_dir / "predictions")
    if episode_dir.is_dir():
        images = list_image_files(episode_dir)
        if images:
            return images

    if root.name == "predictions" and root.parent.name == episode.name:
        return list_image_files(root)

    return []


def weighted_score(results: dict[str, MetricResult], weights: dict[str, float]) -> float:
    total_weight = sum(
        weight
        for name, weight in weights.items()
        if name in results and results[name].is_available
    )
    if total_weight <= 0:
        return 0.0
    return clamp(
        sum(
            float(results[name].score) * weights[name]
            for name in results
            if name in weights and results[name].is_available and results[name].score is not None
        )
        / total_weight
    )


def aggregate_metric_results(
    episode_results: list[EpisodeResult], metrics: list[EvaluatorMetric]
) -> dict[str, MetricResult]:
    aggregate: dict[str, MetricResult] = {}
    for metric in metrics:
        metric_results = [episode.metrics[metric.name] for episode in episode_results if metric.name in episode.metrics]
        values = [result.score for result in metric_results if result.is_available and result.score is not None]
        if not values or any(not result.is_available for result in metric_results):
            reasons = []
            for episode in episode_results:
                metric_result = episode.metrics.get(metric.name)
                if metric_result is not None and not metric_result.is_available and metric_result.reason:
                    reasons.append(f"{episode.episode}: {metric_result.reason}")
            aggregate[metric.name] = MetricResult(
                name=metric.name,
                score=None,
                status="unsupported",
                reason=reasons[0].split(": ", 1)[1] if reasons else "Unsupported metric for one or more episodes.",
                details={"available_episode_scores": values, "unsupported_episodes": reasons},
                issues=reasons[:20],
            )
            continue
        issues = []
        for episode in episode_results:
            metric_result = episode.metrics.get(metric.name)
            if metric_result is not None:
                issues.extend(f"{episode.episode}: {issue}" for issue in metric_result.issues)
        aggregate[metric.name] = MetricResult(
            name=metric.name,
            score=clamp(float(np.mean(values))),
            status="available",
            details={"episode_scores": values},
            issues=issues[:20],
        )
    return aggregate


def infer_main_failure(metrics: dict[str, MetricResult]) -> str:
    if not metrics:
        return "No metrics were run."
    available_metrics = [result for result in metrics.values() if result.is_available and result.score is not None]
    if not available_metrics:
        return "No available metrics were scored."
    lowest = min(available_metrics, key=lambda result: result.score)
    unsupported_count = len([result for result in metrics.values() if not result.is_available])
    if float(lowest.score) >= 85:
        if unsupported_count:
            return f"No dominant failure among available metrics; {unsupported_count} metrics were unsupported."
        return "No dominant failure detected; the run is strong across core world-model checks."
    messages = {
        "visual_similarity": "The model does not visually match held-out future frames closely enough.",
        "action_consistency": "The model generates plausible-looking frames, but predicted motion does not consistently follow robot actions.",
        "temporal_stability": "The model flickers or jumps between future frames instead of producing stable dynamics.",
        "object_permanence": "The model loses track of persistent scene objects during prediction.",
        "contact_realism": "The model moves objects before plausible robot/object contact.",
    }
    return messages.get(lowest.name, f"The weakest metric is {lowest.name}.")


def compute_episode_horizon(
    episode: Episode,
    prediction_frames: list[Path],
    metrics: list[EvaluatorMetric],
    weights: dict[str, float],
) -> dict[str, dict[str, object]]:
    """Evaluate honest per-horizon metric prefixes for one episode.

    Horizon entries are cumulative through t+N. Metrics that cannot produce a
    meaningful value for the available prefix remain unavailable instead of
    receiving fabricated values.
    """

    horizon: dict[str, dict[str, object]] = {}
    max_pairs = min(len(episode.frames), len(prediction_frames))
    for index in range(1, max_pairs + 1):
        label = f"t+{index}"
        prefix_episode = Episode(
            name=episode.name,
            path=episode.path,
            frames=episode.frames[:index],
            predictions=episode.predictions[:index],
            actions=episode.actions[: max(0, index - 1)],
            states=episode.states[:index],
            metadata=episode.metadata,
        )
        prefix_predictions = prediction_frames[:index]
        available: dict[str, object] = {}
        unavailable: dict[str, object] = {}
        metric_results: dict[str, MetricResult] = {}
        for metric in metrics:
            result = _evaluate_horizon_metric(metric, prefix_episode, prefix_predictions)
            metric_results[metric.name] = result
            if result.is_available:
                available[metric.name] = result.model_dump(mode="json")
            else:
                unavailable[metric.name] = {
                    "status": result.status,
                    "reason": result.reason,
                    "issues": result.issues,
                }

        horizon[label] = {
            "horizon_index": index,
            "sample_count": 1,
            "frame_pairs": index,
            "mode": "cumulative_prefix",
            "score": weighted_score(metric_results, weights),
            "metrics": available,
            "unavailable_metrics": unavailable,
        }
    return horizon


def _evaluate_horizon_metric(
    metric: EvaluatorMetric,
    episode: Episode,
    prediction_frames: list[Path],
) -> MetricResult:
    if metric.name == "temporal_stability" and len(prediction_frames) < 2:
        return MetricResult(
            name=metric.name,
            score=None,
            status="unsupported",
            reason="Temporal stability requires at least one future-frame transition.",
            issues=["Temporal stability requires at least one future-frame transition."],
        )
    return metric.evaluate(episode, prediction_frames)


def aggregate_horizon_results(episode_results: list[EpisodeResult]) -> dict[str, dict[str, object]]:
    """Aggregate per-horizon metric values across episodes."""

    labels = sorted(
        {label for episode in episode_results for label in episode.horizon},
        key=_horizon_sort_key,
    )
    aggregate: dict[str, dict[str, object]] = {}
    for label in labels:
        entries = [episode.horizon[label] for episode in episode_results if label in episode.horizon]
        metric_names = sorted(
            {
                name
                for entry in entries
                for name in _as_dict(entry.get("metrics")).keys()
            }
        )
        metric_stats: dict[str, object] = {}
        for name in metric_names:
            values = []
            for entry in entries:
                metric_payload = _as_dict(_as_dict(entry.get("metrics")).get(name))
                score = metric_payload.get("score")
                if isinstance(score, (int, float)):
                    values.append(float(score))
            if values:
                metric_stats[name] = numeric_summary(values)

        unavailable: dict[str, object] = {}
        unavailable_names = sorted(
            {
                name
                for entry in entries
                for name in _as_dict(entry.get("unavailable_metrics")).keys()
            }
        )
        for name in unavailable_names:
            reasons = []
            for entry in entries:
                payload = _as_dict(_as_dict(entry.get("unavailable_metrics")).get(name))
                reason = payload.get("reason")
                if isinstance(reason, str) and reason not in reasons:
                    reasons.append(reason)
            unavailable[name] = {
                "count": sum(1 for entry in entries if name in _as_dict(entry.get("unavailable_metrics"))),
                "reasons": reasons[:5],
            }

        aggregate[label] = {
            "horizon_index": _horizon_sort_key(label),
            "sample_count": len(entries),
            "metrics": metric_stats,
            "unavailable_metrics": unavailable,
        }
    return aggregate


def numeric_summary(values: list[float]) -> dict[str, float | int]:
    """Return numeric statistics for available values only."""

    if not values:
        return {"count": 0}
    arr = np.asarray(values, dtype=float)
    return {
        "count": int(arr.size),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "p10": float(np.percentile(arr, 10)),
        "p25": float(np.percentile(arr, 25)),
        "p50": float(np.percentile(arr, 50)),
        "p75": float(np.percentile(arr, 75)),
        "p90": float(np.percentile(arr, 90)),
    }


def _horizon_sort_key(label: str) -> int:
    if label.startswith("t+"):
        try:
            return int(label[2:])
        except ValueError:
            return 0
    return 0


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}
