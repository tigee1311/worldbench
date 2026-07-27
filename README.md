# WorldBench

Regression testing for video-based robotics world models.

WorldBench compares baseline and candidate checkpoints on the same prediction suite, then surfaces the individual episodes and future horizons that became worse.

**Main question:** did this new world-model checkpoint improve, and what became worse?

```text
same fixed episodes
  -> baseline predictions vs candidate predictions
  -> per-episode and per-horizon deltas
  -> reproducible PASS or FAIL gate
```

[![Tests](https://github.com/tigee1311/worldbench/actions/workflows/tests.yml/badge.svg)](https://github.com/tigee1311/worldbench/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![Version](https://img.shields.io/badge/version-0.4.1-blue)
![License](https://img.shields.io/github/license/tigee1311/worldbench)

Demo video: [artifacts/demo/worldbench-demo-web.mp4](artifacts/demo/worldbench-demo-web.mp4)

## Flagship Proof

The strongest committed proof compares two NanoWM-B/2 checkpoints on the same fixed 10-episode RT-1 / Fractal suite.

| Field | Value |
| --- | --- |
| Baseline checkpoint | `knightnemo/nanowm-b2-rt1-abl-pred-v-50k` |
| Candidate checkpoint | `knightnemo/nanowm-b2-rt1-300k` |
| Fixed episodes | 10, IDs 0 through 9 |
| Composite Score mean | baseline 85.67, candidate 87.28 |
| Composite Score delta | +1.61 |
| Improved / regressed / unchanged episodes | 9 / 1 / 0 |
| Gate result | strict PASS; engineering-threshold PASS |

WorldBench detected aggregate improvement while surfacing the regressed episode: `episode_002.mp4` changed by -0.33. This is a fixed-suite validation proof, not a public model ranking and not evidence of universal robot capability.

Artifacts: [artifacts/checkpoint_validation/](artifacts/checkpoint_validation/)
Method: [docs/checkpoint_validation.md](docs/checkpoint_validation.md), [docs/checkpoint_regression.md](docs/checkpoint_regression.md)

## One Video Pair

If you have one ground-truth future video and one generated prediction video:

```bash
python -m pip install "worldbench[video]"

worldbench eval-videos \
  --ground-truth ground_truth.mp4 \
  --prediction predicted_future.mp4 \
  --output results/
```

This writes:

```text
results/
  result.json
  summary.md
  artifacts/comparison.png
```

`eval-videos` is a beginner-friendly single-prediction evaluation. It is not checkpoint regression by itself.

Try the local synthetic demo:

```bash
worldbench eval-videos --demo --output results/demo
```

## Checkpoint Regression

```bash
worldbench eval-batch \
  --ground-truth eval_suite \
  --predictions baseline_predictions \
  --name baseline \
  --skip-context 4 \
  --output baseline.json

worldbench eval-batch \
  --ground-truth eval_suite \
  --predictions candidate_predictions \
  --name candidate \
  --skip-context 4 \
  --output candidate.json

worldbench gate \
  --baseline baseline.json \
  --candidate candidate.json \
  --strict-config-match \
  --max-episode-regressions 0
```

Optional paired bootstrap uncertainty is available in `gate` with `--bootstrap-samples`; confidence-bound gating is opt-in so existing gates remain backward compatible.

## Example Output

```text
Composite Score: 96.10/100
Metric coverage: 2 of 5 configured metrics
Available configured weight: 45%
Available: Visual Similarity, Temporal Stability
Unavailable: Action Consistency, Object Permanence, Contact Realism
```

The Composite Score is a weighted summary over available configured metrics. It is not accuracy, not task success, and not a universal robotics capability score.

## Compatibility

Directly compatible:

- aligned predicted future RGB frames or videos
- action-conditioned robot video predictors
- image-to-video robot models
- latent models with deterministic RGB decoders
- simulator-rendered futures exported as videos

Adapter required:

- robot-specific action vectors
- dataset layouts outside WorldBench's current readers
- prediction folders or latent/state outputs that need conversion to aligned RGB futures
- 3D, point-cloud, or occupancy outputs that need deterministic rendering

Unsupported as direct targets:

- action-only VLAs
- closed-loop real-robot policies
- text-only environment models
- task-success evaluation without saved future observations

Matrix: [docs/COMPATIBILITY_MATRIX.md](docs/COMPATIBILITY_MATRIX.md)

## Installation

```bash
python -m pip install worldbench
python -m pip install "worldbench[video]"
```

From a checkout:

```bash
python -m pip install -e ".[dev,video]"
```

## Documentation

- CLI: [docs/CLI.md](docs/CLI.md)
- Python API: [docs/PYTHON_API.md](docs/PYTHON_API.md)
- Saved-video evaluation: [docs/SAVED_VIDEO_EVALUATION.md](docs/SAVED_VIDEO_EVALUATION.md)
- Metric cards: [docs/METRIC_CARDS.md](docs/METRIC_CARDS.md)
- Extension API: [docs/EXTENDING_WORLDBENCH.md](docs/EXTENDING_WORLDBENCH.md)
- LeRobot: [docs/LEROBOT.md](docs/LEROBOT.md)
- NanoWM RT-1: [docs/NANOWM_RT1.md](docs/NANOWM_RT1.md)
- Reproducibility and verification: run `worldbench verify-run result.json`
- Roadmap: [docs/ROADMAP.md](docs/ROADMAP.md)
- External pilot protocol: [docs/EXTERNAL_PILOT.md](docs/EXTERNAL_PILOT.md)

## Honest Limits

WorldBench evaluates saved predicted visual futures. It does not run robot control, execute real-world tasks, infer undocumented action semantics, or prove scientific validity by repository edits alone.

External adoption, human calibration, second-model validation, and commercial validation require evidence outside this repository. Protocols for that work are documented, but not claimed complete.
