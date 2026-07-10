# CLI Reference

WorldBench's primary workflow is checkpoint evaluation and gating.

## Primary commands

## Configuration Precedence

WorldBench resolves runtime policy in this order:

1. Command-line gate flags, such as `--require-metric`, `--min-metric-coverage`, and `--strict-config-match`
2. An explicit `--config PATH`
3. `worldbench.yml` in the current working directory
4. Built-in defaults

Evaluation commands use the selected configuration file or built-in defaults. Gate commands then apply CLI gate flags over the selected configuration.

### `eval-video`

Evaluate one aligned ground-truth/prediction video pair. Context frames are removed from both inputs and only the future is scored.

```bash
worldbench eval-video --ground-truth gt.mp4 --prediction pred.mp4 --skip-context 4 --config worldbench.yml
```

### `eval-batch`

Evaluate one checkpoint folder against a fixed suite. Videos are paired by relative POSIX path; missing or extra predictions are rejected.

```bash
worldbench eval-batch --ground-truth suite/ --predictions checkpoint/ --name checkpoint --config worldbench.yml
```

Outputs include timestamped and `latest/` JSON and Markdown artifacts. A named run also writes `<name>.json` unless `--output` is provided.

### `gate`

Compare baseline and candidate batch artifacts:

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
