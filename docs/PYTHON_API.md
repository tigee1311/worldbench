# Python API

## Basic Evaluation

```python
from worldbench import WorldBench

result = WorldBench("dataset").evaluate(predictions="checkpoint_predictions")
print(result.composite_score)
print(result.coverage)
result.save_json("result.json")
result.save_report("report.md")
```

Choose metrics explicitly when embedding WorldBench:

```python
from worldbench import Metrics, WorldBench

result = WorldBench("dataset").run(
    metrics=[Metrics.visual_similarity(), Metrics.temporal_stability()],
    predictions="checkpoint_predictions",
)
```

`result.score` remains a compatibility alias for the numeric composite. Unsupported metrics use `status="unsupported"`, `score=None`, and a reason. Consumers should branch on `metric.is_available`, not coerce `None` into a score.

For production checkpoint gates, prefer batch JSON artifacts through the CLI so dataset identities, episode identities, configuration, and exit codes are preserved consistently.

## Stable Result Types

```python
from worldbench import EvaluationResult, MetricResult

result = EvaluationResult.model_validate_json(open("result.json").read())
for name, metric in result.metrics.items():
    if metric.is_available:
        print(name, metric.score)
    else:
        print(name, "N/A", metric.reason)
```

Important fields:

- `result.composite_score` and `result.score`: weighted summary over available configured metrics.
- `result.coverage`: configured metrics, available metrics, unavailable metrics, and configured-weight coverage.
- `result.provenance`: input hashes, environment metadata, plugin versions, decoder metadata, and configuration hash when available.
- `result.horizon`: cumulative per-horizon summaries when enough frames are available.

## Extension Interfaces

WorldBench plugins are explicit Python objects. WorldBench does not install or download plugins dynamically.

```python
from pathlib import Path

from worldbench import MetricRequirements, MetricResult, PluginRegistry


class ConstantMetric:
    name = "constant_metric"
    version = "0.1.0"
    requirements = MetricRequirements(input_modalities=("rgb_frames",))

    def evaluate(self, episode, prediction_frames: list[Path]) -> MetricResult:
        return MetricResult(name=self.name, score=100.0, status="available")


registry = PluginRegistry()
registry.register_metric(ConstantMetric())
print(registry.provenance())
```

See [EXTENDING_WORLDBENCH.md](EXTENDING_WORLDBENCH.md) for metric, action-adapter, dataset-adapter, and prediction-format-adapter examples.

## Bootstrap Intervals

Paired bootstrap intervals are available for fixed episode deltas and are opt-in in the CLI gate.

```python
from worldbench import paired_bootstrap_interval

interval = paired_bootstrap_interval(
    [1.0, 2.0, -0.5, 3.0],
    bootstrap_samples=5000,
    bootstrap_seed=42,
    confidence_level=0.95,
)
print(interval.to_dict())
```

The interval is an uncertainty estimate over paired episode deltas. It is not proof of formal significance, especially for small episode counts.

## Result Verification

```python
from worldbench import verify_result_file

verification = verify_result_file("result.json")
print(verification.status)
for issue in verification.issues:
    print(issue.severity, issue.message)
```

`verify_result_file` checks bounded JSON structure, input-file existence and hashes when paths are available, package-version compatibility, configuration hash consistency, and built-in metric plugin versions. Status is one of `verified`, `partially_verified`, `verification_failed`, or `not_verifiable`; redacted paths and legacy reports with missing hashes are partial, not fully verified.
