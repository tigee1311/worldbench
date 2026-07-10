"""WorldBench: robotics world-model evaluation made practical."""

from worldbench.core import Metrics, WorldBench, WorldModelRun, evaluate, load_dataset
from worldbench.schemas import EvaluationResult, MetricResult
from worldbench.version import WORLD_BENCH_VERSION

__all__ = [
    "EvaluationResult",
    "MetricResult",
    "Metrics",
    "WorldBench",
    "WorldModelRun",
    "evaluate",
    "load_dataset",
]

__version__ = WORLD_BENCH_VERSION
