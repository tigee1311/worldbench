"""Action-conditioned motion consistency metrics."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from worldbench.dataset import Episode
from worldbench.schemas import ActionRecord, MetricResult
from worldbench.utils import clamp, cosine_similarity, detect_robot_centroid, load_rgb, vector_norm


class ActionConsistencyMetric:
    """Check whether predicted visual motion follows logged robot actions."""

    name = "action_consistency"

    def evaluate(self, episode: Episode, prediction_frames: list[Path]) -> MetricResult:
        if len(prediction_frames) < 2:
            return MetricResult(name=self.name, score=0.0, issues=["Need at least two predicted frames."])

        centroids = [detect_robot_centroid(load_rgb(path)) for path in prediction_frames]
        step_scores: list[float] = []
        failures: list[dict[str, float | int | str]] = []
        directions: list[dict[str, float | int | str]] = []

        for idx, action in enumerate(episode.actions[: len(centroids) - 1]):
            current = centroids[idx]
            nxt = centroids[idx + 1]
            if current is None or nxt is None:
                step_scores.append(0.0)
                failures.append({"t": action.t, "action": action.action, "reason": "robot centroid missing"})
                directions.append(
                    {
                        "t": action.t,
                        "action": action.action,
                        "commanded_direction": _direction_label(_expected_motion(action)),
                        "predicted_motion_direction": "missing",
                    }
                )
                continue

            observed = (nxt[0] - current[0], nxt[1] - current[1])
            expected = _expected_motion(action)
            score = _score_motion(expected, observed)
            step_scores.append(score)
            directions.append(
                {
                    "t": action.t,
                    "action": action.action,
                    "commanded_direction": _direction_label(expected),
                    "predicted_motion_direction": _direction_label(observed),
                    "observed_dx": round(observed[0], 3),
                    "observed_dy": round(observed[1], 3),
                }
            )
            if score < 50.0:
                failures.append(
                    {
                        "t": action.t,
                        "action": action.action,
                        "expected_dx": expected[0],
                        "expected_dy": expected[1],
                        "observed_dx": round(observed[0], 3),
                        "observed_dy": round(observed[1], 3),
                    }
                )

        if not step_scores:
            return MetricResult(name=self.name, score=0.0, issues=["No actions aligned to predicted frames."])

        score = clamp(float(np.mean(step_scores)))
        failure_rate = len(failures) / len(step_scores)
        move_right = [item for item in failures if item.get("action") == "move_right"]
        issues = []
        if failures:
            issues.append(f"{failure_rate:.0%} of action steps did not produce matching visual robot motion.")
            if move_right:
                issues.append(f"{len(move_right)} move_right action(s) failed to move right.")

        return MetricResult(
            name=self.name,
            score=score,
            details={
                "steps": len(step_scores),
                "failed_steps": len(failures),
                "mismatch_count": len(failures),
                "mismatch_percentage": failure_rate * 100.0,
                "failure_rate": failure_rate,
                "commanded_vs_predicted": directions[:20],
                "failures": failures[:10],
            },
            issues=issues,
        )


def _expected_motion(action: ActionRecord) -> tuple[float, float]:
    name = str(action.action).lower()
    dx = action.dx
    dy = action.dy
    if "right" in name:
        dx = max(abs(dx), 1.0)
    elif "left" in name:
        dx = -max(abs(dx), 1.0)
    if "down" in name:
        dy = max(abs(dy), 1.0)
    elif "up" in name:
        dy = -max(abs(dy), 1.0)
    if "stationary" in name or "hold" in name or "close_gripper" in name or "open_gripper" in name:
        dx = 0.0
        dy = 0.0
    return float(dx), float(dy)


def _score_motion(expected: tuple[float, float], observed: tuple[float, float]) -> float:
    expected_norm = vector_norm(*expected)
    observed_norm = vector_norm(*observed)
    if expected_norm < 0.1:
        return clamp(100.0 - observed_norm * 25.0)
    if observed_norm < 0.75:
        return 10.0
    direction_score = (cosine_similarity(expected, observed) + 1.0) * 50.0
    magnitude_score = clamp((observed_norm / 4.0) * 100.0)
    return clamp(0.8 * direction_score + 0.2 * magnitude_score)


def _direction_label(vector: tuple[float, float]) -> str:
    dx, dy = vector
    if vector_norm(dx, dy) < 0.5:
        return "stationary"
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"
