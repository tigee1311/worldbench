"""Object permanence metrics for generated futures."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from worldbench.dataset import Episode
from worldbench.schemas import MetricResult
from worldbench.utils import (
    clamp,
    load_rgb,
    object_area,
    rollout_supports_synthetic_tracking,
)


class ObjectPermanenceMetric:
    """Track whether the main object remains visible over the rollout."""

    name = "object_permanence"

    def evaluate(self, episode: Episode, prediction_frames: list[Path]) -> MetricResult:
        if not rollout_supports_synthetic_tracking(episode):
            return MetricResult(
                name=self.name,
                score=None,
                status="unsupported",
                reason="Reliable object tracking is unavailable for this rollout.",
                issues=["Reliable object tracking is unavailable for this rollout."],
            )
        if not prediction_frames:
            return MetricResult(
                name=self.name,
                score=None,
                status="unsupported",
                reason="No predicted frames available.",
                issues=["No predicted frames available."],
            )

        areas = [object_area(load_rgb(path)) for path in prediction_frames]
        positive_areas = [area for area in areas if area > 10]
        if not positive_areas:
            return MetricResult(
                name=self.name,
                score=None,
                status="unsupported",
                reason="Reliable object tracking is unavailable for this rollout.",
                details={
                    "visible_frames": 0,
                    "total_frames": len(areas),
                    "areas": areas,
                },
                issues=["Reliable object tracking is unavailable for this rollout."],
            )

        reference_area = float(np.median(positive_areas))
        threshold = max(10.0, reference_area * 0.35)
        missing = [idx for idx, area in enumerate(areas) if area < threshold]
        disappearance_percentage = (len(missing) / len(areas)) * 100.0
        visible_ratio = 1.0 - len(missing) / len(areas)
        area_cv = float(np.std(positive_areas) / max(reference_area, 1.0))
        score = clamp(100.0 * visible_ratio - min(25.0, area_cv * 25.0))

        issues = []
        if missing:
            issues.append(
                f"Object disappeared or became too small in {len(missing)} frame(s) "
                f"({disappearance_percentage:.0f}% of prediction): {missing[:8]}."
            )
        if area_cv > 0.35:
            issues.append("Object blob size changes abruptly across frames.")

        return MetricResult(
            name=self.name,
            score=score,
            status="available",
            details={
                "visible_frames": len(areas) - len(missing),
                "total_frames": len(areas),
                "missing_frames": missing,
                "disappearance_percentage": disappearance_percentage,
                "reference_area": reference_area,
                "area_cv": area_cv,
            },
            issues=issues,
        )
