# Saved Video Evaluation

WorldBench can evaluate one saved predicted robot future against its matching ground-truth future without requiring a dataset manifest, actions, states, adapters, or repository knowledge.

```bash
python -m pip install "worldbench[video]"

worldbench eval-videos \
  --ground-truth ground_truth.mp4 \
  --prediction predicted_future.mp4 \
  --output results/
```

Use this workflow when you have matching ground-truth future frames and model-generated future frames saved as videos. It evaluates the predicted future against the ground-truth future. It is not, by itself, checkpoint regression testing.

To test whether a new checkpoint improved, evaluate each checkpoint prediction against the same ground truth and compare the resulting batch artifacts with `worldbench gate`.

`--ground-truth` is the preferred input flag. `--reference` remains available as a backward-compatible alias, but pass exactly one of those flags.

## Supported Formats

The video extra installs `imageio` and `imageio-ffmpeg`. WorldBench accepts files with these extensions when the local video backend can decode them:

- `.mp4`
- `.mov`
- `.avi`
- `.mkv`
- `.webm`

MP4 with H.264-compatible encoding is the most portable choice.

## Alignment Behavior

`eval-videos` uses the safe beginner alignment policy:

1. Decode both videos into RGB frames.
2. Remove `--skip-context` leading frames from both videos.
3. Compare frames by index, not by timestamp interpolation.
4. If one future has a small number of extra frames, score the common future-frame prefix and report exactly how many future frames were trimmed from each input.
5. If the future-frame mismatch is too large, fail instead of silently scoring unrelated horizons.
6. If resolutions differ, resize prediction frames to the ground-truth resolution before scoring and report an alignment note.
7. If FPS metadata differs or is missing, continue with frame-index alignment and report an alignment note.

The strict backward-compatible command remains available:

```bash
worldbench eval-video --ground-truth gt.mp4 --prediction pred.mp4
```

`eval-video` requires matching future-frame counts, matching resolution, and compatible FPS metadata.

## Video-Only Metric Availability

For saved videos without actions, state, object tracks, or synthetic tracking metadata, WorldBench normally reports:

| Metric | Video-only status | Why |
| --- | --- | --- |
| Visual Similarity | available | Uses aligned RGB ground-truth/prediction frame pairs. |
| Temporal Stability | available with at least two predicted future frames | Uses frame-to-frame changes in the prediction. |
| Action Consistency | N/A | Requires action semantics such as string actions or explicit `dx`/`dy`. |
| Object Permanence | N/A | Requires reliable object tracking metadata or a supported synthetic tracking setup. |
| Contact Realism | N/A | Requires reliable robot/object contact tracking. |

Unsupported metrics are excluded from the weighted Composite Score. Available metric weights are renormalized, and every N/A metric includes a reason in the terminal summary and JSON output.

The Composite Score is not accuracy, task success, or a universal measure of robot capability. It summarizes the configured available metrics for this specific aligned ground-truth/prediction pair.

## Outputs

`--output results/` writes:

```text
results/
  result.json
  summary.md
  artifacts/
    comparison.png
```

`result.json` is the machine-readable artifact. It uses the standard WorldBench evaluation schema and includes:

| Field | Meaning |
| --- | --- |
| `result_type` | `evaluation` for a single evaluation result. |
| `schema_version` | WorldBench result schema version. |
| `score` / `composite_score` | Weighted score over available metrics only. |
| `metrics` | Per-metric score, status, details, issues, and N/A reason. |
| `episodes` | The temporary single episode used for evaluation. |
| `horizon` | Per-horizon cumulative-prefix summaries when enough frames exist. |
| `coverage` | Available/configured metric counts and configured weight coverage. |
| `effective_normalized_weights` | Renormalized weights used for available metrics. |
| `provenance` | Source paths, original frame counts, evaluated frame count, trim counts, original and evaluated resolution, original FPS, FPS mismatch flag, alignment method, and warnings. |
| `issues` | Alignment notes and metric issues. |

`summary.md` is a human-readable report generated from the same result. `artifacts/comparison.png` is a small side-by-side contact sheet labeled `Ground truth` and `Prediction` for visual inspection. Disable it with `--no-save-comparison`.

## Tiny Demo

Run a complete demo without providing videos:

```bash
worldbench eval-videos --demo --output results/demo
```

The command creates a tiny deterministic synthetic ground-truth/prediction MP4 pair under `results/demo/demo_inputs/`, evaluates it, and writes the normal result artifacts. The output is labeled synthetic demonstration data, not a model-quality result, and not a benchmark result.

## Exit Codes

| Exit code | Meaning |
| ---: | --- |
| `0` | Evaluation completed and artifacts were written. Low scores or N/A metrics do not fail the command. |
| nonzero | Genuine execution or usage failure, such as missing files, unreadable videos, unsafe frame-count mismatch, invalid output path, or missing video dependencies. |

`eval-videos` is not a regression gate. Use `eval-batch` plus `gate` when you want PASS/FAIL behavior for baseline-versus-candidate checkpoint regression.

## Troubleshooting

### `No such file` or `does not exist`

Check that both paths are local files and quote paths that contain spaces:

```bash
worldbench eval-videos \
  --ground-truth "my clips/ground_truth.mp4" \
  --prediction "my clips/predicted_future.mp4" \
  --output results/
```

### `unsupported extension`

Use one of the supported video extensions. If your file is valid but has a different extension, remux or rename it to a supported container such as `.mp4`.

### `video is unreadable`

The file exists, but the local decoder could not read frames. Re-encode to a simple MP4/H.264 file and try again.

### `Frame-count mismatch is too large`

WorldBench will not silently compare unrelated horizons. Export the same prediction horizon for both videos, adjust `--skip-context`, or use the advanced mismatch options only when you understand the alignment.

### Resolution mismatch note

The beginner command resizes prediction frames to the ground-truth resolution before scoring. For stricter auditing, pre-render both videos at the same resolution or use `eval-video`.

### FPS mismatch note

The beginner command compares frames by index. If your ground truth and prediction represent different time intervals, resample them upstream so frame `t+n` means the same future horizon in both videos.

### Missing video dependencies

Install the video extra:

```bash
python -m pip install "worldbench[video]"
```
