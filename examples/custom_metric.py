"""Example custom metric for WorldBench.

Run `worldbench demo` first to create examples/demo_dataset.
"""

from pathlib import Path

import numpy as np

from worldbench.dataset import Episode
from worldbench.runners.evaluator import EvaluationRunner
from worldbench.schemas import MetricResult
from worldbench.utils import load_rgb, object_area


class CubeVisibilityMetric:
    """Penalize rollouts where the green cube is not visible enough."""

    name = "cube_visibility"

    def evaluate(self, episode: Episode, prediction_frames: list[Path]) -> MetricResult:
        del episode
        if not prediction_frames:
            return MetricResult(name=self.name, score=0.0, issues=["No prediction frames found."])

        areas = [object_area(load_rgb(path)) for path in prediction_frames]
        visible_ratio = float(np.mean([area > 50 for area in areas]))
        score = visible_ratio * 100.0
        issues = [] if score > 90 else ["Cube was missing or too small in multiple predicted frames."]
        return MetricResult(
            name=self.name,
            score=score,
            details={"visible_ratio": visible_ratio, "frame_count": len(prediction_frames)},
            issues=issues,
        )


runner = EvaluationRunner("examples/demo_dataset", predictions="examples/demo_dataset/bad_model")
result = runner.run(
    metrics=[CubeVisibilityMetric()],
    weights={"cube_visibility": 1.0},
)
result.print_summary()
