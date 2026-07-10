# Metric Support

WorldBench scores only the metrics that the rollout can support. Unsupported metrics return N/A and are excluded from the Composite Score denominator.

Default weights:

| Metric | Weight |
| --- | ---: |
| Visual Similarity | 0.25 |
| Action Consistency | 0.30 |
| Temporal Stability | 0.20 |
| Object Permanence | 0.15 |
| Contact Realism | 0.10 |

## Visual Similarity

What it measures:

- pixel-level and structural similarity between ground-truth rollout frames and predicted frames
- mean squared error
- PSNR
- SSIM-style structure

Required signals:

- ground-truth image frames
- predicted image frames

Available when:

- at least one aligned ground-truth/prediction pair can be loaded

N/A behavior:

- this metric currently does not return N/A for missing pairs
- if no aligned frame pairs exist, it returns 0 with an issue

Known limitations:

- it can rate visually plausible but control-useless predictions highly
- it does not understand actions, contact, or object identity
- if `scikit-image` is not installed, WorldBench uses a lightweight NumPy SSIM fallback

## Temporal Stability

What it measures:

- frame-to-frame prediction stability
- sudden jumps
- flicker-like high deltas
- variance in frame deltas

Required signals:

- predicted image frames

Available when:

- at least two predicted frames are available

N/A behavior:

- this metric currently does not return N/A for short predictions
- if fewer than two predicted frames exist, it returns 0 with an issue

Known limitations:

- smooth but wrong videos can score well
- temporal scrambling currently produces a weaker score response than frame freezing on the compact Yaskawa validation artifacts
- the metric is not a replacement for per-horizon analysis

## Action Consistency

What it measures:

- whether predicted visual robot motion follows the logged action direction

Required signals:

- predicted image frames
- action records
- either string actions such as `move_right`/`move_left` or explicit `dx` and `dy`
- visible robot centroid under the current lightweight detector

Available when:

- at least two predicted frames exist
- actions can be interpreted by the current motion adapter logic

Returns N/A when:

- fewer than two predicted frames exist
- raw arbitrary numeric action vectors are provided without explicit `dx`/`dy`
- no actions align to predicted frames

Known limitations:

- raw 7D robot action vectors require an explicit adapter
- current string/dx/dy behavior is appropriate for synthetic and simple screen-space tests, not general robot kinematics

## Object Permanence

What it measures:

- whether a task-relevant object remains visible and stable across predicted frames

Required signals:

- predicted image frames
- rollout metadata that explicitly marks the rollout as synthetic
- object pixels detectable by the current green-object heuristic

Available when:

- the rollout is synthetic or explicitly labeled as synthetic in metadata
- predicted frames contain detectable object pixels

Returns N/A when:

- the rollout is real-world data or otherwise not labeled for synthetic tracking
- no predictions are available
- reliable object pixels cannot be detected

Known limitations:

- current implementation is a lightweight synthetic color/blob heuristic
- real-world object permanence needs a tracking adapter before scoring

## Contact Realism

What it measures:

- whether an object starts moving before plausible robot/object contact

Required signals:

- predicted image frames
- rollout metadata that explicitly marks the rollout as synthetic
- detectable robot and object centroids

Available when:

- the rollout is synthetic or explicitly labeled as synthetic in metadata
- at least two predicted frames exist
- robot and object tracking can be estimated by the current detector

Returns N/A when:

- the rollout is real-world data or otherwise not labeled for synthetic tracking
- fewer than two predicted frames exist
- reliable object or robot tracking is unavailable

Known limitations:

- current implementation is a lightweight synthetic heuristic
- real-world contact realism requires reliable robot and object tracking
- it does not model 3D contact, force, compliance, or occlusion

## Composite Score And Coverage

The Composite Score is computed with available metrics only:

```text
sum(score_i * weight_i for available metric_i) / sum(weight_i for available metric_i)
```

If no metrics are available, the Composite Score is 0. Schema-v2 results also report available/configured metric count, configured-weight coverage, effective normalized weights, and unsupported metric names so the number is never presented as full coverage when it is not.

Unsupported metrics are preserved in reports with `status: unsupported`, `score: null`, a reason, and any supporting details.
