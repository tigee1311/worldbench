"""Run a minimal custom WorldBench metric plugin."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from worldbench import MetricRequirements, PluginRegistry, WorldBench
from worldbench.dataset import Episode
from worldbench.schemas import MetricResult
from worldbench.utils import load_rgb


class MeanBrightnessMetric:
    name = "mean_brightness"
    version = "0.1.0"
    requirements = MetricRequirements(input_modalities=("rgb_frames",))

    def evaluate(self, episode: Episode, prediction_frames: list[Path]) -> MetricResult:
        del episode
        if not prediction_frames:
            return MetricResult(
                name=self.name,
                score=None,
                status="unsupported",
                reason="No predicted frames are available.",
            )
        values = [float(load_rgb(path).mean()) for path in prediction_frames]
        return MetricResult(
            name=self.name,
            score=float(np.clip(np.mean(values) / 255.0 * 100.0, 0.0, 100.0)),
            details={"frame_count": len(values)},
        )


registry = PluginRegistry()
registry.register_metric(MeanBrightnessMetric())

result = WorldBench("examples/demo_dataset").evaluate(
    predictions="examples/demo_dataset/good_model",
    metrics=list(registry.metrics.items()),
)

print(result.score)
print(result.provenance["metric_plugins"])
