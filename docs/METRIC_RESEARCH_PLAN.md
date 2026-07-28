# Metric Research Plan

Production metrics were not changed in this hardening pass.

The `research_metrics/` namespace contains non-production experiments for comparing candidate metrics against controlled corruptions:

- current visual similarity
- temporal motion similarity
- frame-difference trajectory similarity
- object-track displacement similarity

Corruptions currently covered:

- frame freeze
- temporal scramble
- blur
- dropped frames
- speed changes
- spatial shifts

The harness reports:

- monotonicity under corruption severity
- repeat stability
- runtime practicality
- sensitivity relative to current metrics
- likely risk of penalizing valid multimodal futures

Run:

```bash
python -m research_metrics.corruption_harness --output-dir artifacts/metric_research
```

## Promotion Criteria

A research metric should not move into `worldbench.metrics` unless there is written evidence that it:

- is deterministic and practical on CPU or Apple Silicon
- improves sensitivity for target failure modes
- does not over-penalize plausible alternative futures
- has clear unsupported-result behavior
- is documented with formula, inputs, failure modes, and limitations
- preserves backward compatibility or introduces an explicit schema version

## Current Limitations

The harness uses synthetic corruptions and does not establish scientific validity, human preference alignment, or real-robot task success. It is a screening tool for deciding which metric ideas deserve deeper validation.
