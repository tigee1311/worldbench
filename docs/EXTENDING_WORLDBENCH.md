# Extending WorldBench

WorldBench extensions are explicit Python objects registered by the caller. WorldBench does not download, install, or import remote plugin code automatically.

## Supported Extension Points

| Extension | Use when | Production status |
| --- | --- | --- |
| Metric plugin | A saved prediction has additional signals that can be scored without changing built-in metric formulas. | Supported through explicit registration. |
| Action adapter | Raw robot actions need deterministic normalization before Action Consistency can be meaningful. | Interface documented; built-in metrics still use current conservative behavior. |
| Dataset adapter | A dataset format should be converted into WorldBench episodes. | Interface documented for stable third-party packages. |
| Prediction-format adapter | A model writes predictions in a non-WorldBench layout. | Interface documented for stable third-party packages. |

## Metric Plugin Contract

Metric plugins expose a stable name, version, requirements, and `evaluate` method:

```python
from pathlib import Path

from worldbench import MetricRequirements
from worldbench.dataset import Episode
from worldbench.schemas import MetricResult


class MeanBrightnessMetric:
    name = "mean_brightness"
    version = "0.1.0"
    requirements = MetricRequirements(input_modalities=("rgb_frames",))

    def evaluate(self, episode: Episode, prediction_frames: list[Path]) -> MetricResult:
        ...
```

Names must be unique within a registry. Versions appear in result provenance so a saved artifact can later be checked against installed plugins.

If a plugin cannot honestly score an episode, it should return:

```python
MetricResult(
    name="mean_brightness",
    score=None,
    status="unsupported",
    reason="required signal is unavailable",
)
```

It may also raise `UnsupportedPluginResult`; WorldBench converts that into N/A. Unexpected plugin exceptions are isolated by default as `status="error"` with a sanitized `error_type` and reason, not as ordinary unsupported metrics. Strict callers can request fail-fast plugin execution when programming errors should stop the run.

## Explicit Registration

```python
from worldbench import PluginRegistry

registry = PluginRegistry()
registry.register_metric(MeanBrightnessMetric())

plugins = list(registry.metrics.items())
```

For the current Python API, pass metric instances directly to `WorldBench(...).evaluate(...)` or `EvaluationRunner(...).run(...)`. The registry is useful for deterministic ordering, duplicate checks, and provenance.

```python
from worldbench import WorldBench

result = WorldBench("dataset").evaluate(
    predictions="candidate_predictions",
    metrics=list(registry.metrics.items()),
)
```

## Action Adapter Contract

Action adapters normalize raw action formats into explicit `ActionRecord` values. They must not infer semantics from undocumented vector positions.

```python
from worldbench import NormalizedActions, PluginCapabilities
from worldbench.schemas import ActionRecord


class ExampleActionAdapter:
    name = "example_action_adapter"
    version = "0.1.0"
    supported_schema = "example.v1"
    capabilities = PluginCapabilities(
        inputs=("example.v1",),
        outputs=("worldbench.actions.v1",),
        limitations=("demo mapping only",),
    )

    def normalize(self, actions: object) -> NormalizedActions:
        records = tuple(ActionRecord(t=i, action=item) for i, item in enumerate(actions))
        return NormalizedActions(
            schema="worldbench.actions.v1",
            actions=records,
            adapter_name=self.name,
            adapter_version=self.version,
        )
```

Action adapters should fail closed. If the input schema is unknown or ambiguous, return a clear unsupported result or raise a normal exception during explicit conversion. Do not guess that element `3` in an arbitrary vector means gripper state unless the upstream schema documents it.

## Provenance

Evaluation results include a provenance block similar to:

```json
{
  "metric_plugins": {
    "visual_similarity": "1.0",
    "temporal_stability": "1.0"
  },
  "adapter_plugins": {}
}
```

Third-party tools should store their own adapter versions in the same shape when they produce WorldBench-compatible artifacts.

## Compatibility Rules

- Do not change built-in metric formulas in a plugin.
- Do not reuse a built-in metric name for a different formula.
- Do not coerce unsupported results into zero unless the metric definition explicitly says zero is meaningful.
- Keep plugin evaluation deterministic for the same episode, predictions, configuration, and random seed.
- Keep dependencies optional and document them clearly.
