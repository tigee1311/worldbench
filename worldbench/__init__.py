"""WorldBench: robotics world-model evaluation made practical."""

from worldbench.core import Metrics, WorldBench, WorldModelRun, evaluate, load_dataset
from worldbench.schemas import EvaluationResult, MetricResult

__all__ = [
    "EvaluationResult",
    "MetricResult",
    "Metrics",
    "WorldBench",
    "WorldModelRun",
    "evaluate",
    "load_dataset",
]

__version__ = "0.3.0"
