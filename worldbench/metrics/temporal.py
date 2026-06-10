"""Temporal stability metrics for generated futures."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from worldbench.dataset import Episode
from worldbench.schemas import MetricResult
from worldbench.utils import clamp, load_rgb


class TemporalStabilityMetric:
    """Penalize flicker, high variance, and sudden frame jumps."""

    name = "temporal_stability"

    def evaluate(self, episode: Episode, prediction_frames: list[Path]) -> MetricResult:
        del episode
        if len(prediction_frames) < 2:
            return MetricResult(name=self.name, score=0.0, issues=["Need at least two predicted frames."])

        images = [load_rgb(path) for path in prediction_frames]
        diffs = [float(np.mean(np.abs(images[idx + 1] - images[idx]))) for idx in range(len(images) - 1)]
        median_diff = float(np.median(diffs))
        max_diff = float(np.max(diffs))
        std_diff = float(np.std(diffs))
        jump_threshold = max(18.0, median_diff * 3.0 + 8.0)
        jump_indices = [idx for idx, diff in enumerate(diffs) if diff > jump_threshold]

        jump_penalty = min(60.0, len(jump_indices) * 20.0 + max(0.0, max_diff - jump_threshold) * 0.8)
        variance_penalty = min(35.0, std_diff * 1.8)
        baseline_penalty = min(20.0, max(0.0, median_diff - 8.0) * 1.5)
        score = clamp(100.0 - jump_penalty - variance_penalty - baseline_penalty)

        issues = []
        if jump_indices:
            spans = ", ".join(f"t={idx}->t={idx + 1}" for idx in jump_indices[:5])
            issues.append(f"Sudden frame jump or flicker detected around {spans}.")
        if std_diff > 12:
            issues.append("Frame-to-frame differences have high variance, indicating unstable prediction dynamics.")

        return MetricResult(
            name=self.name,
            score=score,
            details={
                "mean_frame_delta": float(np.mean(diffs)),
                "median_frame_delta": median_diff,
                "max_frame_delta": max_diff,
                "std_frame_delta": std_diff,
                "jump_indices": jump_indices,
            },
            issues=issues,
        )

