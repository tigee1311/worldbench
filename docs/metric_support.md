# Metric Support

WorldBench scores only the metrics that the rollout can support. Unsupported metrics are reported as `status: unsupported`, `score: null`, and display as N/A. Unsupported metrics are excluded from the Composite Score denominator, and remaining available weights are renormalized.

Default weights from [../worldbench/config.py](../worldbench/config.py):

| Metric | Weight |
| --- | ---: |
| Visual Similarity | 0.25 |
| Action Consistency | 0.30 |
| Temporal Stability | 0.20 |
| Object Permanence | 0.15 |
| Contact Realism | 0.10 |

## Visual Similarity

Purpose: compare predicted RGB frames against ground-truth rollout frames using MSE, PSNR, and SSIM-style structure.

Required inputs:

- ground-truth image frames
- predicted image frames
- at least one aligned frame pair

Availability rule:

- all aligned pairs returned by `load_aligned_pairs(episode.frames, prediction_frames)` are scored
- predictions are resized to the ground-truth frame size before scoring

Unavailable behavior:

- this metric currently does not return N/A for missing frame pairs
- if no aligned pairs exist, it returns `0.0` with issue `No aligned frame pairs available.`

Known limitations:

- visually plausible but control-useless predictions can score highly
- the metric does not understand actions, object identity, or contact
- if `scikit-image` is unavailable, WorldBench uses its NumPy SSIM fallback

## Temporal Stability

Purpose: penalize frame-to-frame jumps, flicker-like deltas, and high variance across predicted future frames.

Required inputs:

- at least two predicted image frames

Availability rule:

- the full metric scores frame-to-frame differences across all predicted frames
- per-horizon evaluation marks `t+1` unavailable because one frame has no future-frame transition

Unavailable behavior:

- the full metric currently returns `0.0` with issue `Need at least two predicted frames.` when fewer than two frames exist
- the per-horizon wrapper returns N/A with reason `Temporal stability requires at least one future-frame transition.`

Known limitations:

- smooth but wrong videos can score well
- temporal scrambling currently causes a smaller score decrease than frame freezing in the committed corruption artifacts

## Action Consistency

Purpose: check whether predicted visual robot motion follows logged action direction.

Required inputs:

- at least two predicted frames
- action records aligned to predicted frame transitions
- string actions such as `move_right`, `move_left`, `move_up`, `move_down`, `hold`, `open_gripper`, or `close_gripper`, or explicit nonzero `dx`/`dy`
- a visible robot centroid under the current image detector

Availability rule:

- string actions are interpreted by name
- non-string actions are supported only when explicit `dx` or `dy` is nonzero
- no action adapter registry exists yet

N/A behavior:

- fewer than two predicted frames: `Need at least two predicted frames.`
- raw arbitrary numeric action vectors: `unsupported raw numeric action vectors require an action adapter.`
- no actions aligned to predictions: `No actions aligned to predicted frames.`

Known limitations:

- raw 7D robot action vectors require an explicit adapter before scoring is meaningful
- current motion logic is screen-space and suitable for synthetic/simple fixtures, not general robot kinematics

## Object Permanence

Purpose: check whether a task-relevant object remains visible and stable across predicted frames.

Required inputs:

- predicted image frames
- rollout metadata explicitly labeled as synthetic
- object pixels detectable by the current green-object heuristic

Availability rule:

- `rollout_supports_synthetic_tracking` must return true from the episode metadata
- at least one predicted frame must contain detectable object pixels

N/A behavior:

- non-synthetic or real-world rollout: `Reliable object tracking is unavailable for this rollout.`
- no predicted frames: `No predicted frames available.`
- no detectable object pixels: `Reliable object tracking is unavailable for this rollout.`

Known limitations:

- current implementation is a lightweight synthetic color/blob heuristic
- real-world object permanence needs a tracking adapter before scoring

## Contact Realism

Purpose: penalize object motion before plausible robot/object contact.

Required inputs:

- at least two predicted image frames
- rollout metadata explicitly labeled as synthetic
- detectable robot and object centroids

Availability rule:

- `rollout_supports_synthetic_tracking` must return true from the episode metadata
- robot/object centroids are estimated from lightweight image heuristics

N/A behavior:

- non-synthetic or real-world rollout: `Reliable robot and object tracking are unavailable for this rollout.`
- fewer than two predicted frames: `Need at least two predicted frames.`
- missing tracked object: `Reliable robot and object tracking are unavailable for this rollout.`

Known limitations:

- current implementation is a lightweight synthetic heuristic
- real-world contact realism requires reliable robot and object tracking
- it does not model 3D contact, force, compliance, or occlusion

## Composite Score And Coverage

The Composite Score is computed from available metrics only:

```text
sum(score_i * weight_i for available metric_i) / sum(weight_i for available metric_i)
```

If no metrics are available, the Composite Score is `0.0`.

Schema-v2 results report:

- available and unsupported metrics
- available/configured metric count
- configured-weight coverage
- effective normalized weights
- enabled and required metrics
- effective configuration and configuration hash

The committed NanoWM single-rollout artifact predates schema v2, but its score still follows the same available-weight denominator:

```text
(89.24097498284189 * 0.25 + 96.32682361785054 * 0.20) / 0.45 = 92.39024104284573
```
