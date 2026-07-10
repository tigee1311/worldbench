# Checkpoint Regression

WorldBench checkpoint regression answers one question:

```text
When I train a new checkpoint, did it actually improve?
```

The workflow is model-agnostic. Your model code generates videos. WorldBench evaluates and compares those videos.

```text
ground-truth evaluation episodes
        +
baseline checkpoint predictions
        +
candidate checkpoint predictions
        ↓
WorldBench
        ↓
PASS or FAIL
```

## Directory Structure

`worldbench eval-batch` pairs videos by relative POSIX path under each root.

```text
eval_suite/
  episode_001.mp4
  episode_002.mp4
  tasks/pick_cube/episode_003.mp4

checkpoint_183/
  episode_001.mp4
  episode_002.mp4
  tasks/pick_cube/episode_003.mp4

checkpoint_184/
  episode_001.mp4
  episode_002.mp4
  tasks/pick_cube/episode_003.mp4
```

The ground-truth and prediction sets must match. WorldBench reports missing predictions and prediction-only files instead of silently skipping episodes.

Supported video extensions are:

```text
.mp4, .mov, .avi, .mkv, .webm
```

## Evaluate One Video

```bash
worldbench eval-video \
  --ground-truth sample_0000_gt.mp4 \
  --prediction sample_0000_gen.mp4 \
  --skip-context 4
```

`--skip-context` removes leading context frames from both videos. Only future frames are scored.

For a 12-frame ground-truth video and 12-frame prediction video with `--skip-context 4`, WorldBench evaluates 8 future frame pairs.

The command rejects:

- missing files
- unreadable videos
- empty videos
- negative `--skip-context`
- `--skip-context` values that leave no future frames
- different future frame counts after context removal
- incompatible frame dimensions
- meaningfully incompatible FPS

It does not resize, resample, pad, repeat, or silently truncate videos.

## Evaluate One Checkpoint

```bash
worldbench eval-batch \
  --ground-truth eval_suite/ \
  --predictions checkpoint_183/ \
  --name checkpoint_183
```

Outputs:

- timestamped batch artifact under `.worldbench/batches/`
- `.worldbench/batches/latest/batch.json`
- `<name>.json` when `--name` is provided
- per-episode result JSON files under the timestamped batch directory

The aggregate artifact includes:

- checkpoint name
- roots and pairing rule
- evaluated episode IDs
- per-episode scores
- per-episode metric availability
- per-episode horizon data
- aggregate overall statistics
- aggregate metric statistics
- aggregate horizon curves
- worst episodes

Numeric aggregates exclude N/A values. Each metric reports how many episodes contributed valid scores.

## Per-Horizon Results

WorldBench reports cumulative horizon prefixes:

```text
t+1
t+2
t+3
...
```

Each horizon entry records:

- horizon index
- sample count
- available metric values or aggregates
- unavailable metrics and reasons

WorldBench only reports metrics that can honestly be evaluated for that horizon prefix. For raw video pairs, visual similarity is available per frame. Temporal stability becomes available once at least two predicted frames exist. Action consistency, object permanence, and contact realism remain N/A unless the rollout provides the semantics those metrics require.

Aggregate horizon curves keep sample counts because episodes may have different future lengths:

```text
Horizon      Mean Visual      Episodes
t+1             96.2             100
t+2             93.1             100
t+3             88.4              98
```

## Gate A Candidate

```bash
worldbench gate \
  --baseline checkpoint_183.json \
  --candidate checkpoint_184.json
```

`gate` compares batch artifacts produced by `eval-batch`.

It validates compatibility before comparing:

- same episode set
- same `skip-context`
- same batch schema version

It compares:

- aggregate Composite Score mean
- aggregate metric means available in both runs
- per-horizon metric means available in both runs
- per-episode overall deltas

N/A is never treated as zero. Metrics unavailable in either run are not used for regression failures.

## Thresholds

The first version uses engineering thresholds, not statistically validated benchmark thresholds.

```bash
worldbench gate \
  --baseline checkpoint_183.json \
  --candidate checkpoint_184.json \
  --max-overall-drop 2 \
  --max-metric-drop 5 \
  --max-horizon-drop 5
```

Defaults:

| Option | Default | Meaning |
| --- | ---: | --- |
| `--max-overall-drop` | 0.0 | Backward-compatible maximum allowed Composite Score mean drop. |
| `--max-metric-drop` | 0.0 | Maximum allowed comparable metric mean drop. |
| `--max-horizon-drop` | 0.0 | Maximum allowed comparable per-horizon metric mean drop. |

WorldBench uses a 0.01-point tolerance for unchanged episode scores and threshold comparisons to avoid floating-point noise.

## Exit Codes

| Outcome | Exit code |
| --- | ---: |
| PASS | 0 |
| Valid regression FAIL | 1 |
| Invalid input or incompatible batch results | 2 |

This makes the gate usable in CI:

```bash
worldbench gate \
  --baseline checkpoint_183.json \
  --candidate checkpoint_184.json \
  --max-overall-drop 2 \
  --max-metric-drop 5 \
  --max-horizon-drop 5
```

A regression FAIL exits nonzero and fails the CI job.

## Limitations

- WorldBench does not run model inference or load checkpoints.
- The video workflow requires videos with matching future lengths after context removal.
- The command does not resample FPS, resize frames, or repair mismatched inputs.
- Raw video pairs do not provide action semantics, object tracks, or robot/object contact tracks, so those metrics remain N/A.
- No hypothesis testing or statistical significance model is included yet.
- The gate compares batch artifacts from the same evaluation suite; it intentionally rejects mismatched episode sets.
