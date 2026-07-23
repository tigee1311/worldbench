# CLI Reference

WorldBench's primary workflow is checkpoint regression testing for video-based robotics world models: evaluate baseline and candidate predictions on the same fixed episode suite, then gate the candidate.

## Primary commands

## Configuration Precedence

WorldBench resolves runtime policy in this order:

1. Command-line gate flags, such as `--require-metric`, `--min-metric-coverage`, and `--strict-config-match`
2. An explicit `--config PATH`
3. `worldbench.yml` in the current working directory
4. Built-in defaults

Evaluation commands use the selected configuration file or built-in defaults. Gate commands then apply CLI gate flags over the selected configuration.

### `eval-videos`

Beginner-friendly evaluation for one saved predicted robot future against its matching ground-truth future:

```bash
worldbench eval-videos --ground-truth ground_truth.mp4 --prediction predicted_future.mp4 --output results/
```

This command decodes both videos, uses safe frame-index alignment, resizes prediction frames to the ground-truth resolution when needed, rejects major frame-count mismatches, prints a readable summary, and writes:

- `results/result.json`
- `results/summary.md`
- `results/artifacts/comparison.png`

It returns `0` when evaluation completes, even if some metrics are N/A. It returns nonzero for genuine execution failures such as missing files, unreadable videos, unsafe alignment, invalid output paths, or missing video dependencies.

`--ground-truth` is preferred. `--reference` remains as a backward-compatible alias, but do not pass both.

`eval-videos` is not a checkpoint-regression command by itself. For checkpoint regression, evaluate baseline and candidate predictions against the same ground-truth suite with `eval-batch`, then compare the batch artifacts with `gate`.

Run a no-file smoke test:

```bash
worldbench eval-videos --demo --output results/demo
```

Details: [SAVED_VIDEO_EVALUATION.md](SAVED_VIDEO_EVALUATION.md)

### `eval-video`

Evaluate one aligned ground-truth/prediction video pair. Context frames are removed from both inputs and only the future is scored.

```bash
worldbench eval-video --ground-truth gt.mp4 --prediction pred.mp4 --skip-context 4 --config worldbench.yml
```

This strict command is retained for backward compatibility. It requires matching future-frame counts, resolution, and FPS metadata. New users with only two saved MP4 files should usually start with `eval-videos`.

### `eval-batch`

Evaluate one checkpoint folder against a fixed suite of ground-truth robot episode videos. Videos are paired by relative POSIX path; missing or extra predictions are rejected.

```bash
worldbench eval-batch --ground-truth suite/ --predictions checkpoint/ --name checkpoint --config worldbench.yml
```

Outputs include timestamped and `latest/` JSON and Markdown artifacts. A named run also writes `<name>.json` unless `--output` is provided.

### `gate`

Compare baseline and candidate batch artifacts produced from the same suite:

```bash
worldbench gate --baseline baseline.json --candidate candidate.json \
  --require-metric visual_similarity \
  --require-metric temporal_stability \
  --min-metric-coverage 0.40 \
  --min-configured-weight-coverage 0.45 \
  --strict-config-match
```

Useful thresholds include `--min-composite-improvement`, `--max-episode-regressions`, `--max-metric-drop`, and `--max-horizon-drop`. Exit codes are `0` for pass, `1` for a completed gate failure, and `2` for usage or incompatible episode errors.

## Secondary commands

- `report`: render an evaluation JSON as Markdown.
- `dashboard`: inspect an evaluation or comparison locally.
- `import-lerobot`: import a native Hugging Face LeRobot dataset or legacy local layout.
- `validate`: validate the frame dataset format.
- `compare`: advanced result or prediction-folder comparison.
- `eval`: advanced frame-folder evaluation retained for compatibility.

## Deprecated development commands

`demo`, `benchmark`, `make-demo-video`, and `make-screenshots` are hidden from normal help. They remain callable in 0.4 with deprecation guidance and are planned for removal in 0.5. Synthetic fixtures and asset generation live under `scripts/dev/` and remain available to contributors.

Run `worldbench COMMAND --help` for the installed version's exact options.
