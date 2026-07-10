# Python API

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
