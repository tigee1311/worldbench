# NanoWM RT-1 Integration

WorldBench includes a lightweight NanoWM RT-1 adapter for preparing already-generated RGB rollout clips for checkpoint regression. The adapter standardizes files and metadata; it does not run NanoWM inference.

```text
NanoWM inference outside WorldBench
        ↓
adapter standardizes videos and metadata
        ↓
worldbench eval-batch evaluates baseline
        ↓
worldbench eval-batch evaluates candidate
        ↓
worldbench gate compares checkpoints
```

## What This Supports

- Public NanoWM RT-1 checkpoints when their generated RGB future clips are already available.
- Fixed RT-1 / Fractal episodes exported as ground-truth and prediction videos or frame directories.
- Baseline-versus-candidate checkpoint comparison with `worldbench gate`.
- Per-episode result JSON.
- Per-horizon visual and temporal result summaries.
- PASS or FAIL gate output using the normal WorldBench checkpoint-regression path.

## What This Does Not Support

- Automatic NanoWM checkpoint downloads.
- Automatic full-dataset downloads.
- NanoWM training.
- Hugging Face authentication.
- Silent large model inference.
- Bundled model weights or datasets.
- Arbitrary latent-only predictions.
- Arbitrary robot action-vector interpretation.
- Universal model ranking.
- Treating WorldBench scores as accuracy.

WorldBench remains responsible for input standardization, validation, metrics, checkpoint comparison, and reporting. NanoWM remains responsible for model inference.

## Adapter Layout

The adapter lives at:

```text
examples/nanowm_rt1/prepare_worldbench_inputs.py
```

It accepts generated ground-truth clips, baseline prediction clips, and optional candidate prediction clips. Sources can be video files, directories of videos, or frame directories. The output layout is:

```text
prepared_run/
  ground_truth/
    rt1/episode_000000.mp4
  baseline/
    rt1/episode_000000.mp4
  candidate/
    rt1/episode_000000.mp4
  manifest.json
```

`worldbench eval-batch` pairs videos by identical relative POSIX paths, so every episode must appear under the same relative path in `ground_truth`, `baseline`, and `candidate`.

## Adapter Command

Example after NanoWM inference has produced RGB clips:

```bash
python examples/nanowm_rt1/prepare_worldbench_inputs.py \
  --ground-truth <nanowm-run>/ground_truth \
  --baseline <nanowm-run>/50k_predictions \
  --candidate <nanowm-run>/300k_predictions \
  --baseline-checkpoint knightnemo/nanowm-b2-rt1-abl-pred-v-50k \
  --candidate-checkpoint knightnemo/nanowm-b2-rt1-300k \
  --context-frames 1 \
  --prediction-frames 3 \
  --fps 3 \
  --dataset "RT-1 / Fractal" \
  --dataset-source IPEC-COMMUNITY/fractal20220817_data_lerobot \
  --camera observation.images.image \
  --output-dir .worldbench/nanowm_rt1_prepared
```

The adapter validates:

- every prediction has matching ground truth
- baseline and candidate episode names match
- no duplicate episode identifiers are used
- videos and frame directories are non-empty
- frame count equals `context_frames + prediction_frames`
- width and height match within each episode
- FPS matches when video metadata provides FPS
- unsupported file extensions are rejected
- source files are never modified in place
- the output directory is separate from all input sources, including when `--overwrite` is used

It writes `manifest.json` with:

```text
schema_version
adapter
dataset
dataset_source
episodes
camera
baseline_checkpoint
candidate_checkpoint
context_frames
prediction_frames
fps
resolution
ground_truth_directory
baseline_directory
candidate_directory
source_files
created_at
worldbench_version
worldbench_commit
known_limitations
```

Unavailable optional fields are written as `null`. The adapter does not infer action semantics from numeric vectors.

## Evaluate And Gate

Run the normal WorldBench commands:

```bash
worldbench eval-batch \
  --ground-truth .worldbench/nanowm_rt1_prepared/ground_truth \
  --predictions .worldbench/nanowm_rt1_prepared/baseline \
  --name nanowm_rt1_cpu_pilot \
  --skip-context 1 \
  --output .worldbench/nanowm_rt1_prepared/baseline_result.json

worldbench eval-batch \
  --ground-truth .worldbench/nanowm_rt1_prepared/ground_truth \
  --predictions .worldbench/nanowm_rt1_prepared/candidate \
  --name nanowm_rt1_300k_cpu_pilot \
  --skip-context 1 \
  --output .worldbench/nanowm_rt1_prepared/candidate_result.json

worldbench gate \
  --baseline .worldbench/nanowm_rt1_prepared/baseline_result.json \
  --candidate .worldbench/nanowm_rt1_prepared/candidate_result.json \
  --strict-config-match \
  --min-metric-count 2 \
  --min-configured-weight-coverage 0.45 \
  --max-overall-drop 0 \
  --max-episode-regressions 0
```

## Existing Main Proof

WorldBench's stronger committed proof remains the 10-episode NanoWM checkpoint comparison:

```text
10 fixed RT-1 episodes
NanoWM 50k versus 300k
9 improved
1 regressed
Gate PASS
```

That proof is documented in [checkpoint_validation.md](checkpoint_validation.md) and stored under [../artifacts/checkpoint_validation/](../artifacts/checkpoint_validation/).

## CPU Reproducibility Pilot

A separate one-episode pilot was reproduced on a macOS arm64 machine with 16 GB RAM using CPU inference and no paid compute.

```text
1 fixed RT-1 episode
NanoWM 50k versus 300k
93.05 to 93.66 composite
Composite delta +0.61
No episode regression
Gate PASS
```

This pilot demonstrates reproducibility of the workflow on a constrained local machine. It is not a broad model-quality claim and should not be treated as stronger than the 10-episode proof.

Compact artifacts are committed under [../artifacts/nanowm_rt1_cpu_pilot/](../artifacts/nanowm_rt1_cpu_pilot/). Raw videos, datasets, and NanoWM checkpoints are not committed.

## Hardware Evidence

The pilot was reproduced on a macOS arm64 machine with 16 GB RAM using CPU inference and no paid compute.

This does not imply that every NanoWM configuration or full evaluation protocol will run efficiently on that hardware. The CPU pilot used one fixed episode and reduced NanoWM sampling steps; production-style NanoWM evaluation should be run in NanoWM's own environment.

## Metric Availability

The pilot provides RGB ground-truth and prediction videos. WorldBench therefore evaluates Visual Similarity and Temporal Stability. Action Consistency, Object Permanence, and Contact Realism remain N/A because no action adapter or reliable object/robot tracker is provided for these videos.

N/A metrics are not averaged as zero. Available metric weights are renormalized according to the normal WorldBench configuration.
