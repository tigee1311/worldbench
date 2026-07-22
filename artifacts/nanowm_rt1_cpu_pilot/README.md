# NanoWM RT-1 CPU Pilot Artifacts

These compact JSON artifacts record a one-episode NanoWM RT-1 checkpoint-regression reproduction through the adapter in `examples/nanowm_rt1/`.

Included:

- `manifest.json`: sanitized adapter manifest.
- `baseline_result.json`: WorldBench batch result for `knightnemo/nanowm-b2-rt1-abl-pred-v-50k`.
- `candidate_result.json`: WorldBench batch result for `knightnemo/nanowm-b2-rt1-300k`.
- `gate.json`: WorldBench gate result comparing candidate against baseline.

Excluded:

- NanoWM checkpoints.
- RT-1 / Fractal dataset files.
- Generated ground-truth and prediction videos.
- Any local Hugging Face cache.

The pilot ran one fixed episode on a 16 GB CPU-only macOS arm64 machine. It demonstrates reproducibility of the WorldBench preparation, evaluation, and gate workflow; it is not a broad model-quality claim and does not replace the 10-episode checkpoint-validation proof under `artifacts/checkpoint_validation/`.
