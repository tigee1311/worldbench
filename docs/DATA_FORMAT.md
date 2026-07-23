# Data Format

The checkpoint workflow accepts one video per episode. Ground truth, baseline predictions, and candidate predictions must use identical relative filenames.

```text
eval_suite/episode_001.mp4
baseline/episode_001.mp4
candidate/episode_001.mp4
```

Videos must have matching future-frame counts after `--skip-context`, resolution, and FPS. WorldBench rejects silent truncation and resampling. Batch artifacts store episode IDs, skip-context settings, horizon identities, and a SHA-256 identity of the ground-truth video set.

## Compatibility

WorldBench is directly compatible with models that export aligned predicted future RGB frames or videos for robot episodes. This includes action-conditioned robot video predictors, image-to-video robot world models, visual dynamics models, latent world models with an RGB decoder, and simulators or learned models that render predicted visual futures.

These outputs require an adapter before WorldBench can score them correctly:

- robot-specific action vectors
- state-trajectory predictions
- latent-only outputs
- native 3D, 4D, or point-cloud predictions

Without a converter to aligned RGB futures, those formats are not valid `eval-video` or `eval-batch` inputs. WorldBench is not currently a target for action-only policies, VLAs that do not predict future observations, text-only environment models, symbolic planners, or closed-loop robot-task evaluation.

The advanced frame dataset layout is:

```text
dataset/episode_001/
  frames/000001.png
  predictions/000001.png
  actions.json
  states.json
  metadata.json
```

Actions may contain timestamps, source indices, an `action` value, explicit `dx`/`dy`, and gripper state. States may include source provenance, arbitrary `observation_state`, and fixture tracker coordinates. See [LeRobot import](LEROBOT.md) for alignment behavior.

Evaluation schema v2 retains the legacy `score` and `weights` fields and adds canonical `composite_score`, coverage, effective weights, WorldBench version, effective configuration, and configuration hash. See [migration](MIGRATION_V0_4.md).
