"""WorldBench: robotics world-model evaluation made practical."""

from worldbench.core import Metrics, WorldBench, WorldModelRun, evaluate, load_dataset
from worldbench.plugins import (
    ActionAdapter,
    DatasetAdapter,
    MetricPlugin,
    MetricRequirements,
    NormalizedActions,
    PluginCapabilities,
    PluginErrorPolicy,
    PluginRegistry,
    PredictionFormatAdapter,
    UnsupportedPluginResult,
)
from worldbench.schemas import EvaluationResult, MetricResult
from worldbench.statistics import PairedBootstrapResult, paired_bootstrap_interval
from worldbench.verification import VerificationResult, verify_result_file
from worldbench.version import WORLD_BENCH_VERSION

__all__ = [
    "EvaluationResult",
    "MetricResult",
    "ActionAdapter",
    "DatasetAdapter",
    "MetricPlugin",
    "MetricRequirements",
    "NormalizedActions",
    "PluginCapabilities",
    "PluginErrorPolicy",
    "PluginRegistry",
    "PredictionFormatAdapter",
    "UnsupportedPluginResult",
    "PairedBootstrapResult",
    "VerificationResult",
    "Metrics",
    "WorldBench",
    "WorldModelRun",
    "evaluate",
    "load_dataset",
    "paired_bootstrap_interval",
    "verify_result_file",
]

__version__ = WORLD_BENCH_VERSION
