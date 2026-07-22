# NanoWM RT-1 Adapter Example

This directory contains a lightweight adapter for already-generated NanoWM RT-1 clips. It does not download checkpoints, download datasets, run NanoWM inference, or import NanoWM dependencies.

The adapter prepares this layout for the existing WorldBench CLI:

```text
output_run/
  ground_truth/
    episode_000.mp4
  baseline/
    episode_000.mp4
  candidate/
    episode_000.mp4
  manifest.json
```

Run it after producing NanoWM ground-truth and prediction clips:

```bash
python examples/nanowm_rt1/prepare_worldbench_inputs.py \
  --ground-truth /path/to/nanowm/ground_truth \
  --baseline /path/to/nanowm/50k_predictions \
  --candidate /path/to/nanowm/300k_predictions \
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

Then evaluate and gate:

```bash
worldbench eval-batch \
  --ground-truth .worldbench/nanowm_rt1_prepared/ground_truth \
  --predictions .worldbench/nanowm_rt1_prepared/baseline \
  --name nanowm_rt1_50k \
  --skip-context 1 \
  --output .worldbench/nanowm_rt1_prepared/baseline_result.json

worldbench eval-batch \
  --ground-truth .worldbench/nanowm_rt1_prepared/ground_truth \
  --predictions .worldbench/nanowm_rt1_prepared/candidate \
  --name nanowm_rt1_300k \
  --skip-context 1 \
  --output .worldbench/nanowm_rt1_prepared/candidate_result.json

worldbench gate \
  --baseline .worldbench/nanowm_rt1_prepared/baseline_result.json \
  --candidate .worldbench/nanowm_rt1_prepared/candidate_result.json \
  --strict-config-match
```
