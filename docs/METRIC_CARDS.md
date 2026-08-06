# Metric Cards

These cards document the production metrics shipped in WorldBench v0.4.1 and preserved in this hardening pass. They describe current behavior; they do not introduce new formulas or change released result artifacts.

## Composite Score

Purpose: summarize configured metrics that are available for the current input.

Inputs: per-metric scores, metric weights, and metric availability.

Formula:

```text
sum(score_i * configured_weight_i for available metric_i)
/
sum(configured_weight_i for available metric_i)
```

Version: schema v2 composite behavior.

Supported situations: runs where at least one configured metric returns an available numeric score.

Unsupported situations: if no metrics are available, the Composite Score is `0.0` and should be treated as a failed evaluation setup, not a meaningful model score.

Known failure modes: a high composite can hide missing metrics when coverage is low.

Interpretation: a weighted summary for this specific evaluation configuration.

What it does not establish: accuracy, task success, physical correctness, universal robot capability, or cross-protocol benchmark superiority.

## Visual Similarity

Purpose: compare predicted RGB frames against aligned ground-truth RGB future frames.

Inputs: ground-truth frames, prediction frames, and at least one aligned frame pair.

Formula:

```text
mean_mse = mean(pixel MSE over aligned pairs)
mean_psnr = mean(PSNR over aligned pairs)
mean_ssim = mean(SSIM or fallback SSIM over aligned pairs)
mse_score = 100 * (1 - mean_mse / 255^2)
psnr_score = 100 * mean_psnr / 40
ssim_score = 100 * mean_ssim
score = 0.35 * mse_score + 0.30 * psnr_score + 0.35 * ssim_score
```

Version: `visual_similarity` plugin version `1.0`.

Supported situations: aligned RGB ground truth and prediction frames.

Unsupported situations: no aligned frame pairs. The metric returns N/A (`status="unsupported"`) rather than a score.

Known failure modes: visually plausible but action-wrong predictions may score well; perceptual quality can differ from pixel/SSIM similarity; multimodal valid futures can be penalized.

Interpretation: frame-level visual closeness to the recorded future.

What it does not establish: task success, action fidelity, object identity persistence, contact realism, or physical correctness.

## Temporal Stability

Purpose: penalize flicker, abrupt frame jumps, and high variance in predicted future frames.

Inputs: at least two predicted frames.

Formula:

```text
diff_t = mean(abs(frame_t+1 - frame_t))
median_diff = median(diff_t)
max_diff = max(diff_t)
std_diff = std(diff_t)
jump_threshold = max(18, median_diff * 3 + 8)
jump_penalty = min(60, jump_count * 20 + max(0, max_diff - jump_threshold) * 0.8)
variance_penalty = min(35, std_diff * 1.8)
baseline_penalty = min(20, max(0, median_diff - 8) * 1.5)
score = 100 - jump_penalty - variance_penalty - baseline_penalty
```

Version: `temporal_stability` plugin version `1.0`.

Supported situations: two or more predicted future frames.

Unsupported situations: one predicted frame has no temporal transition. Both the full run and per-horizon `t+1` report N/A (`status="unsupported"`).

Known failure modes: a smooth but wrong video can score well; severe temporal scrambling has shown smaller deltas than frame freezing in existing corruption artifacts.

Interpretation: smoothness and local temporal consistency of the prediction.

What it does not establish: correct motion, task progress, action compliance, or physically plausible dynamics.

## Action Consistency

Purpose: check whether predicted visual robot motion follows logged action direction.

Inputs: at least two predicted frames, aligned action records, and supported action semantics.

Formula:

```text
expected_motion = direction implied by string action or explicit dx/dy
observed_motion = robot centroid displacement between predicted frames
if expected stationary:
  step_score = 100 - observed_norm * 25
else:
  direction_score = (cosine(expected, observed) + 1) * 50
  magnitude_score = 100 * observed_norm / 4
  step_score = 0.8 * direction_score + 0.2 * magnitude_score
score = mean(step_score)
```

Version: `action_consistency` plugin version `1.0`.

Supported situations: string actions such as `move_right`, `move_left`, `move_up`, `move_down`, `hold`, `open_gripper`, or explicit nonzero `dx`/`dy`.

Unsupported situations: raw numeric action vectors without an explicit action adapter; no aligned actions; too few predicted frames.

Known failure modes: screen-space centroid detection is simple; real robot kinematics and camera geometry are not modeled.

Interpretation: directional visual consistency for supported action semantics.

What it does not establish: true control success, torque/force correctness, gripper-state semantics for undocumented vectors, or real-robot policy quality.

## Object Permanence

Purpose: check whether a task-relevant object remains visible and size-stable across predicted frames.

Inputs: predicted frames from a rollout explicitly labeled as synthetic, with detectable object pixels.

Formula:

```text
area_t = green object-pixel area per predicted frame
reference_area = median(positive area_t)
missing_t = area_t < max(10, reference_area * 0.35)
visible_ratio = 1 - missing_count / frame_count
area_cv = std(positive area_t) / reference_area
score = 100 * visible_ratio - min(25, area_cv * 25)
```

Version: `object_permanence` plugin version `1.0`.

Supported situations: synthetic-labeled rollouts compatible with the current color/blob tracker.

Unsupported situations: real-world or unlabeled rollouts without reliable object tracking.

Known failure modes: color/blob tracking is brittle and not identity-aware.

Interpretation: synthetic-object visibility under the current tracker.

What it does not establish: general real-world object permanence, occlusion reasoning, semantic identity, or task completion.

## Contact Realism

Purpose: penalize object motion before plausible robot/object contact.

Inputs: at least two predicted frames from a synthetic-labeled rollout with detectable robot and object centroids.

Formula:

```text
distance_t = robot/object centroid distance at previous frame
object_motion_t = object displacement from first detected object position
premature_t = distance_t > contact_threshold_px and object_motion_t > motion_threshold_px
missing_penalty = 15 if object moved and no contact-like frame was detected
score = 100 - min(85, premature_count * 22) - missing_penalty
```

Version: `contact_realism` plugin version `1.0`.

Supported situations: synthetic-labeled robot/object interaction rollouts compatible with current centroid heuristics.

Unsupported situations: real-world or unlabeled rollouts without reliable robot/object tracking.

Known failure modes: no 3D contact model, no force/compliance model, no occlusion model, and brittle color/blob tracking.

Interpretation: synthetic pre-contact object-motion plausibility under the current heuristic.

What it does not establish: real contact physics, manipulation success, force correctness, or closed-loop task performance.
