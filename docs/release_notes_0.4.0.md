# WorldBench 0.4.0 Release Notes

## Highlights

WorldBench 0.4.0 sharpens the project around regression testing for video-based robotics world-model checkpoints. It adds schema-v2 Composite Score transparency, `worldbench.yml` metric and gate policy, configuration and dataset identities, coverage-safe gates, Markdown batch/gate evidence, and a CI checkpoint-gate example.

## Real Checkpoint-Regression Proof

The primary public proof is the committed NanoWM-B/2 checkpoint comparison on 10 fixed RT-1 / Fractal episodes:

| Field | Value |
| --- | --- |
| Baseline checkpoint | `knightnemo/nanowm-b2-rt1-abl-pred-v-50k` |
| Candidate checkpoint | `knightnemo/nanowm-b2-rt1-300k` |
| Episodes | 0 through 9 |
| Composite Score mean | 85.67 -> 87.28 (`+1.61`) |
| Visual Similarity mean | +2.19 |
| Temporal Stability mean | +0.89 |
| Episode outcomes | 9 improved, 1 regressed, 0 unchanged |
| Gate result | strict PASS; engineering-threshold PASS |

WorldBench detected that the candidate improved in aggregate while still surfacing `episode_002.mp4` as the regressed episode at -0.33.

## Real-Model Integration Proof

The single-rollout NanoWM RT-1 artifact remains committed separately. It evaluates one rollout with eight generated future frames and reports Composite Score 92.39, Visual Similarity 89.24, and Temporal Stability 96.33. Action Consistency, Object Permanence, and Contact Realism are N/A for that artifact.

This single-rollout artifact is not a public cross-model ranking and is not a claim that NanoWM is 92.4% accurate.

## Metric Honesty

Unsupported metrics are reported as N/A and are excluded from the Composite Score denominator. Schema-v2 artifacts record configured metrics, available metrics, configured-weight coverage, effective normalized weights, WorldBench version, and configuration hashes.

## LeRobot And Real-Data Support

The release keeps the verified LeRobot importer and real-data timeline documentation for video and control timelines. Network LeRobot integration tests remain outside the default offline test run.

## Validation

The release is validated with offline unit tests, linting, package build checks, wheel installation smoke tests, and committed checkpoint-validation artifacts. The checkpoint-validation artifacts are under `artifacts/checkpoint_validation/`.

## Installation

After the trusted PyPI publishing workflow completes:

```bash
python -m pip install "worldbench[video]==0.4.0"
```

## Limitations

- The checkpoint proof covers 10 fixed episodes and is not a public cross-model ranking or a claim of universal model quality.
- The single-rollout NanoWM artifact covers one rollout and eight generated future frames.
- Raw video-pair evaluations support Visual Similarity and Temporal Stability; action, object, and contact metrics require reliable semantics or tracking inputs.
- WorldBench evaluates saved visual rollouts and predictions. It does not run model inference or closed-loop robot tasks.

See [migration guidance](MIGRATION_V0_4.md) for field compatibility and stricter gate behavior.
