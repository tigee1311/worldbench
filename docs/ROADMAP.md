# Roadmap

This roadmap separates verified current behavior from future work. It does not mark unimplemented items complete.

WorldBench is intentionally scoped to regression testing for saved predictions from video-based robotics world models:

```text
same episodes -> baseline predictions vs candidate predictions -> episode and horizon deltas -> reproducible PASS or FAIL gate
```

## Working Now

- Frame-dataset evaluation with `worldbench eval`.
- Direct saved-video pair evaluation with `worldbench eval-video` and `worldbench eval-videos`.
- Multi-episode checkpoint evaluation with `worldbench eval-batch`.
- Baseline-versus-candidate regression gates with `worldbench gate`.
- Per-episode, per-horizon, and metric-level deltas.
- Metric coverage and unavailable-metric reporting.
- Paired bootstrap uncertainty estimates for checkpoint comparisons when explicitly enabled.
- Run provenance for inputs, configuration, versions, decoder metadata, and environment metadata.
- Result verification with `worldbench verify-run`.
- Explicit extension protocols for metrics, action adapters, dataset adapters, and prediction-format adapters.
- Local Markdown reports and dashboard artifacts.
- LeRobot import for supported saved visual rollouts.
- Committed NanoWM RT-1 validation artifact and small synthetic corruption artifacts.

## Near-Term

1. Harden adapter examples for common saved-video export layouts.
2. Evaluate a second unrelated public video world model under a documented protocol.
3. Run external pilot evaluations with teams that already produce saved robot-video predictions.
4. Compare experimental metrics against corruptions and human judgments before any production metric change.
5. Add richer provenance verification for codec metadata, decoder versions, and plugin compatibility.

## Research Required Before Production

- Learned visual embeddings.
- Optical-flow or trajectory metrics.
- Object-track displacement metrics.
- Physical-consistency or task-plausibility metrics.
- Metric weight changes.
- Any claim that a video metric predicts real-robot task success.

## External Evidence Required

- Independent users.
- Repeated team usage.
- Human judgment calibration.
- Second-team replication.
- Commercial willingness to pay.
- Testimonials or adoption claims.

## Out Of Scope Until Validated

- Universal robotics leaderboards.
- Cloud sharing as a default product surface.
- Generic ROS support.
- Simulator orchestration.
- Real-robot execution.
- VLA policy evaluation when no future observations are produced.
