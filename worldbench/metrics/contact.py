"""Contact realism checks for object interaction rollouts."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from worldbench.dataset import Episode
from worldbench.schemas import MetricResult
from worldbench.utils import clamp, detect_object_centroid, detect_robot_centroid, load_rgb, vector_norm


class ContactRealismMetric:
    """Penalize object motion before robot/object contact."""

    name = "contact_realism"

    def __init__(self, contact_threshold_px: float = 23.0, motion_threshold_px: float = 3.0) -> None:
        self.contact_threshold_px = contact_threshold_px
        self.motion_threshold_px = motion_threshold_px

    def evaluate(self, episode: Episode, prediction_frames: list[Path]) -> MetricResult:
        del episode
        if len(prediction_frames) < 2:
            return MetricResult(name=self.name, score=0.0, issues=["Need at least two predicted frames."])

        images = [load_rgb(path) for path in prediction_frames]
        robot = [detect_robot_centroid(image) for image in images]
        obj = [detect_object_centroid(image) for image in images]

        premature: list[int] = []
        distances: list[float | None] = []
        object_motion: list[float] = []
        first_object = next((point for point in obj if point is not None), None)
        if first_object is None:
            return MetricResult(name=self.name, score=0.0, issues=["Object centroid was never detected."])

        for idx in range(1, len(images)):
            if robot[idx - 1] is None or obj[idx - 1] is None or obj[idx] is None:
                distances.append(None)
                object_motion.append(0.0)
                continue
            distance = vector_norm(robot[idx - 1][0] - obj[idx - 1][0], robot[idx - 1][1] - obj[idx - 1][1])
            distances.append(distance)
            moved = vector_norm(obj[idx][0] - first_object[0], obj[idx][1] - first_object[1])
            object_motion.append(moved)
            if distance > self.contact_threshold_px and moved > self.motion_threshold_px:
                premature.append(idx)

        contact_like_frames = [
            idx
            for idx, distance in enumerate(distances, start=1)
            if distance is not None and distance <= self.contact_threshold_px
        ]
        object_motion_frames = [
            idx
            for idx, motion in enumerate(object_motion, start=1)
            if motion > self.motion_threshold_px
        ]
        first_contact_frame = contact_like_frames[0] if contact_like_frames else None
        first_object_motion_frame = object_motion_frames[0] if object_motion_frames else None
        moved_before_contact = (
            first_object_motion_frame is not None
            and (first_contact_frame is None or first_object_motion_frame < first_contact_frame)
        )
        penalty = min(85.0, len(premature) * 22.0)
        missing_penalty = 15.0 if not contact_like_frames and max(object_motion, default=0.0) > self.motion_threshold_px else 0.0
        score = clamp(100.0 - penalty - missing_penalty)

        issues = []
        if premature:
            issues.append(f"Object moved before contact in predicted frame(s): {premature[:8]}.")
            if first_object_motion_frame is not None:
                if first_contact_frame is None:
                    issues.append(f"Object began moving at frame {first_object_motion_frame}; no contact was detected.")
                else:
                    issues.append(
                        f"Object began moving at frame {first_object_motion_frame}; estimated contact occurred at frame {first_contact_frame}."
                    )
        if missing_penalty:
            issues.append("Object motion occurred without any detected robot/object contact.")

        return MetricResult(
            name=self.name,
            score=score,
            details={
                "premature_motion_frames": premature,
                "contact_frames": contact_like_frames,
                "object_motion_frames": object_motion_frames,
                "first_contact_frame": first_contact_frame,
                "first_object_motion_frame": first_object_motion_frame,
                "moved_before_contact": moved_before_contact,
                "contact_threshold_px": self.contact_threshold_px,
                "max_object_motion_px": float(np.max(object_motion)) if object_motion else 0.0,
            },
            issues=issues,
        )
