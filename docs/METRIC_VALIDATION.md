# Metric Validation

WorldBench validates metrics with deterministic fixture corruption tests and compact real-data corruption artifacts. Synthetic content is test infrastructure, not public product proof.

Current checks cover frame freezing, temporal scrambling, action mismatch, object disappearance, and premature object motion. Unsupported real-world tracking and action cases explicitly return `N/A`.

Committed real-data summaries:

- [Frame-freeze results](../artifacts/frame_freeze_benchmark.json)
- [Temporal-scramble results](../artifacts/temporal_scramble_benchmark.json)

Frame freezing produces the clearer current Temporal Stability response. Temporal scrambling is directionally detected but remains a known sensitivity limitation. These corruption checks validate expected response direction; they do not establish a universal threshold or standardized robotics benchmark.

See [metric support](metric_support.md) for required signals and current adapters.
