# v0.4.1 Compatibility Report

This report records compatibility checks for the `hardening/core-statistics`
split against the public `worldbench[video]==0.4.1` release.

## Fixture Generation

Fixtures live under `tests/fixtures/v0_4_1/` and were generated with the
published package in:

```text
/Users/ayush/worldbench-review/v041-fixture-env-py311
```

The fixture environment used Python 3.11 because `worldbench==0.4.1` declares
`Requires-Python >=3.10`.

Fixture commands are recorded in
`tests/fixtures/v0_4_1/README.md`.

## Artifacts Covered

- v0.4.1 saved-video `result.json`
- v0.4.1 saved-video `summary.md`
- v0.4.1 batch baseline result
- v0.4.1 batch candidate result
- v0.4.1 gate result
- v0.4.1-compatible evaluation and gate configuration files
- existing small NanoWM result sample

## Loading Behavior

Compatibility tests assert that:

- v0.4.1 evaluation results load through `EvaluationResult`.
- v0.4.1 batch results load through `load_batch_result`.
- v0.4.1 gate semantics remain unchanged by default.
- Missing new provenance fields remain missing evidence and are reported by
  `verify-run` as warnings where applicable.
- Missing bootstrap fields do not affect old gates.
- The old `eval-videos --reference` alias still works.
- Non-batch results are not silently treated as batch results.

## Numerical Comparison

Representative evaluation:

```bash
worldbench eval-videos \
  --ground-truth /Users/ayush/worldbench/tests/fixtures/v0_4_1/saved_video/demo_inputs/ground_truth.mp4 \
  --prediction /Users/ayush/worldbench/tests/fixtures/v0_4_1/saved_video/demo_inputs/predicted_future.mp4 \
  --output /Users/ayush/worldbench-review/output-comparison/<side> \
  --no-save-comparison
```

The v0.4.1 side was run from `/Users/ayush/worldbench-review` to avoid importing
the checkout from the repository working directory. The core branch side was run
with `PYTHONPATH=/Users/ayush/worldbench` from the same review directory.

Machine-readable comparison:

```text
/Users/ayush/worldbench-review/output-comparison/comparison.json
```

Summary:

| Classification | Count |
| --- | ---: |
| expected additive | 10 |
| expected formatting | 4 |
| breaking | 0 |
| unexpected | 0 |

Protected numerical fields were compared recursively:

- `score`
- `composite_score`
- `metrics`
- `episodes`
- `horizon`

No protected numerical field changed.

## JSON Differences

| Path | Classification | Reason |
| --- | --- | --- |
| `/created_at` | expected formatting | Run timestamp differs. |
| `/provenance/created_at` | expected formatting | Run timestamp differs. |
| `/provenance/ground_truth_path` | expected formatting | Core branch redacts private absolute paths by default. |
| `/provenance/prediction_path` | expected formatting | Core branch redacts private absolute paths by default. |
| `/provenance/adapter_plugins` | expected additive | New adapter-version provenance. |
| `/provenance/decoder_backend` | expected additive | New decoder provenance. |
| `/provenance/environment` | expected additive | New package, Python, OS, and toolchain provenance. |
| `/provenance/ground_truth_codec_metadata` | expected additive | Optional codec metadata. |
| `/provenance/ground_truth_sha256` | expected additive | New input hash. |
| `/provenance/input_files` | expected additive | New verifiable input records. |
| `/provenance/metric_plugins` | expected additive | New metric plugin-version provenance. |
| `/provenance/prediction_codec_metadata` | expected additive | Optional codec metadata. |
| `/provenance/prediction_sha256` | expected additive | New input hash. |
| `/provenance/report_configuration_sha256` | expected additive | New report configuration hash. |

## Verdict

The core split preserves v0.4.1 numerical behavior for the representative
saved-video evaluation. Differences are limited to expected provenance additions,
timestamps, and privacy-preserving path redaction.
