# WorldBench Evaluation Report

**Composite Score:** 96.10/100

**Metric coverage:** 2 of 5 configured metrics

**Configured weight coverage:** 45%

**Main failure:** No dominant failure among available metrics; 3 metrics were unsupported.

## Metric Scores

| Metric | Score | Effective Weight |
| --- | --- | --- |
| Visual Similarity | 94.7/100 | 56% |
| Action Consistency | N/A | N/A |
| Temporal Stability | 97.9/100 | 44% |
| Object Permanence | N/A | N/A |
| Contact Realism | N/A | N/A |

### Unsupported Metrics

- Action Consistency
- Object Permanence
- Contact Realism

## Per-Episode Scores

| Episode | Score | Metric Breakdown |
| --- | --- | --- |
| episode_001 | 96.1/100 | visual_similarity=94.7, action_consistency=N/A, temporal_stability=97.9, object_permanence=N/A, contact_realism=N/A |

## Evidence

- No actions aligned to predicted frames.
- episode_001: No actions aligned to predicted frames.
- Reliable object tracking is unavailable for this rollout.
- episode_001: Reliable object tracking is unavailable for this rollout.
- Reliable robot and object tracking are unavailable for this rollout.
- episode_001: Reliable robot and object tracking are unavailable for this rollout.

## Suggested Next Steps

- Improve visual reconstruction quality before relying on generated futures for planning.
- Audit prediction rollout recurrence and add losses that discourage flicker.
- Review action consistency support for the current action format.
- Run WorldBench on a held-out robot-object interaction split before comparing models.

## Run Metadata

- Dataset: `tests/fixtures/v0_4_1/saved_video/demo_inputs/ground_truth.mp4`
- Predictions: `tests/fixtures/v0_4_1/saved_video/demo_inputs/predicted_future.mp4`
- Created: `2026-07-27T23:06:45.539284+00:00`
- WorldBench version: `0.4.1`
- Schema version: `2`
- Configuration hash: `9efc6fa61da4df5d701a5cd6338f4ad73ff3e50f661c6a9ed03bdb0032cf783e`

## Saved Video Provenance

- Ground truth path: `tests/fixtures/v0_4_1/saved_video/demo_inputs/ground_truth.mp4`
- Prediction path: `tests/fixtures/v0_4_1/saved_video/demo_inputs/predicted_future.mp4`
- Original ground-truth frame count: `8`
- Original prediction frame count: `8`
- Evaluated frame count: `8`
- Frames trimmed from ground truth: `0`
- Frames trimmed from prediction: `0`
- Original ground-truth resolution: `48x32`
- Original prediction resolution: `48x32`
- Evaluated resolution: `48x32`
- Resizing occurred: `False`
- Original ground-truth FPS: `6.0`
- Original prediction FPS: `6.0`
- FPS differed: `False`
- Alignment method: `safe_common_future_prefix_frame_index_alignment`
- Metric coverage: `2 of 5 configured metrics`

### Alignment Details

- `alignment_method`: `safe_common_future_prefix_frame_index_alignment`
- `evaluated_frame_count`: `8`
- `evaluated_resolution`: `48x32`
- `fps_differed`: `False`
- `fps_mismatch`: `False`
- `fps_policy`: `frame_index_alignment_with_warning`
- `frame_alignment`: `common_future_prefix`
- `frame_count_mismatch`: `0`
- `frame_count_policy`: `trim_common_prefix_with_major_mismatch_rejection`
- `ground_truth_frames_trimmed`: `0`
- `ground_truth_future_frame_count`: `8`
- `ground_truth_original_fps`: `6.0`
- `ground_truth_original_frame_count`: `8`
- `ground_truth_original_resolution`: `48x32`
- `max_allowed_frame_count_mismatch`: `8`
- `mode`: `safe`
- `prediction_frames_trimmed`: `0`
- `prediction_future_frame_count`: `8`
- `prediction_original_fps`: `6.0`
- `prediction_original_frame_count`: `8`
- `prediction_original_resolution`: `48x32`
- `resized_prediction`: `False`
- `resizing_occurred`: `False`
- `resolution_policy`: `resize_prediction_to_ground_truth`

### Warnings

- None

### Demo Notice

- Synthetic demonstration data.
- Not a model-quality result.
- Not a benchmark result.
