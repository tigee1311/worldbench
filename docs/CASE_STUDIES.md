# Case Studies

## NanoWM Checkpoint Regression

WorldBench compared saved video predictions from NanoWM-B/2 checkpoints at 50k and 300k using the same 10 RT-1 / Fractal episodes. The Composite Score changed from 85.67 to 87.28 (`+1.61`), 9 episodes improved, 1 regressed, and the candidate passed the aggregate gate.

Only Visual Similarity and Temporal Stability were supported. The configured default profile therefore had 2 of 5 metrics and 45% configured-weight coverage. Action Consistency, Object Permanence, and Contact Realism remained `N/A`.

The key result is not only the higher aggregate: WorldBench exposed `episode_002.mp4` at `-0.33` while still making the overall release decision explicit.

- [Full methodology](checkpoint_validation.md)
- [Batch and gate artifacts](../artifacts/checkpoint_validation/)

## Earlier Single-Rollout Integration

An earlier NanoWM 300k integration verified that real generated frames could pass through WorldBench. It covered one rollout and is retained as integration history, not primary product proof. See [real model evaluation](real_model_evaluation.md).
