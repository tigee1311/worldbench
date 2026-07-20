# WorldBench Robotics

Testing and regression infrastructure for robotics world models.

Bring your own robot rollout and predicted futures. WorldBench evaluates the checks supported by the available data, marks unsupported metrics N/A, and saves reproducible results.

[![Tests](https://github.com/tigee1311/worldbench/actions/workflows/tests.yml/badge.svg)](https://github.com/tigee1311/worldbench/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![Version](https://img.shields.io/badge/version-0.4.0-blue)
![License](https://img.shields.io/github/license/tigee1311/worldbench)

## Real-Model Integration Proof

A single-rollout integration proof using one NanoWM RT-1 rollout and eight generated future frames.

| Field | Verified value |
| --- | --- |
| Model | NanoWM B2 RT-1 300K (`knightnemo/nanowm-b2-rt1-300k`) |
| Dataset | RT-1 / Fractal |
| Scope | one rollout |
| Generated future frames evaluated | eight |
| Resolution | 256x256 RGB |
| FPS | 3 |

| Metric | Result |
| --- | ---: |
| Overall | 92.4 |
| Visual Similarity | 89.2 |
| Temporal Stability | 96.3 |
| Action Consistency | N/A |
| Object Permanence | N/A |
| Contact Realism | N/A |

This is a single-rollout integration proof, not a standardized leaderboard result and not a claim that NanoWM is 92.4% accurate.

Artifact: [artifacts/real_model_eval/nanowm_rt1_episode0.json](artifacts/real_model_eval/nanowm_rt1_episode0.json)

## Quickstart

From a repository checkout, install the package and run the committed sample dataset:

```bash
python -m pip install -e ".[video]"
worldbench validate examples/demo_dataset
worldbench eval examples/demo_dataset --predictions examples/demo_dataset/good_model --output-root .worldbench/readme-quickstart
worldbench report artifacts/real_model_eval/nanowm_rt1_episode0.json --output .worldbench/readme-quickstart/nanowm_report.md
```

The sample dataset is synthetic and exists to verify the local setup. The real-model proof above is the committed NanoWM artifact.

## How It Works

WorldBench has three verified evaluation paths:

- `eval` scores a WorldBench frame dataset and an optional prediction folder.
- `eval-video` scores one aligned ground-truth/prediction video pair after removing `--skip-context` frames.
- `eval-batch` scores a checkpoint folder across matching episode videos, and `gate` compares baseline and candidate batch artifacts.

Results include JSON output, metric coverage, effective normalized weights, unavailable metric reasons, and per-horizon metric summaries when enough frames are available. `compare`, `report`, and `dashboard` provide local comparison, Markdown, and HTML inspection surfaces.

## Supported Metrics And N/A Behavior

WorldBench does not invent semantic scores. A metric returns N/A when the rollout does not provide the semantics or signals needed for reliable evaluation. Unsupported metrics are excluded from the weighted overall score, and the remaining available weights are renormalized.

| Metric | Required input | Current unavailable behavior |
| --- | --- | --- |
| Visual Similarity | aligned ground-truth and predicted RGB frames | if no frame pairs exist, returns `0.0` with issue `No aligned frame pairs available.` |
| Temporal Stability | at least two predicted future frames | if fewer than two frames exist, returns `0.0` with issue `Need at least two predicted frames.`; per-horizon `t+1` marks it unsupported |
| Action Consistency | at least two predicted frames plus string actions or explicit `dx`/`dy` | N/A for raw numeric action vectors without an adapter, too few frames, or no aligned actions |
| Object Permanence | synthetic-labeled rollout and detectable object pixels | N/A when reliable object tracking is unavailable |
| Contact Realism | synthetic-labeled rollout and detectable robot/object centroids | N/A when reliable robot and object tracking are unavailable |

Default weights are Visual Similarity `0.25`, Action Consistency `0.30`, Temporal Stability `0.20`, Object Permanence `0.15`, and Contact Realism `0.10`.

The NanoWM artifact had Visual Similarity and Temporal Stability available. Its rounded score comes from:

```text
(89.24097498284189 * 0.25 + 96.32682361785054 * 0.20) / 0.45 = 92.39024104284573
```

Details: [docs/metric_support.md](docs/metric_support.md)

## Real-Data Validation

The repository records native LeRobot validation against `chocolat-nya/yaskawa-untangle-dataset` episode `0` in network-marked integration tests. Those tests are not part of the default offline `pytest` run.

| Recorded check | Video timeline | Control timeline |
| --- | ---: | ---: |
| Video timeline frames | 900 | 4,952 exported rows |
| Control timeline rows | 4,952 source rows | 4,952 exported rows |
| Actions | 7D | 7D |
| States | 7D | 7D |
| Source video | 640x480 RGB | 640x480 RGB |

Source evidence: [tests/test_lerobot_integration.py](tests/test_lerobot_integration.py) and [docs/real_data_validation.md](docs/real_data_validation.md).

## LeRobot Support

`import-lerobot` supports native Hugging Face LeRobot datasets through the optional `lerobot` extra and a legacy local LeRobot-style folder converter.

```bash
worldbench import-lerobot --repo-id chocolat-nya/yaskawa-untangle-dataset --episodes 0:1 --camera observation.images.fixed_cam1 --timeline video --out examples/yaskawa_video
worldbench import-lerobot --repo-id chocolat-nya/yaskawa-untangle-dataset --episodes 0:1 --camera observation.images.fixed_cam1 --timeline control --out examples/yaskawa_control
```

`--timeline video` exports one timestep per unique source camera frame. It aligns actions with `latest_at_or_before_timestamp` and states with `nearest_timestamp`.

`--timeline control` exports one timestep per source control row. It aligns actions and states with `source_control_row`.

Imported actions, states, and metadata preserve source control indices, source control timestamps, source video frame indices, source video timestamps, repo id, camera key, timeline, and alignment strategy when available.

Details: [docs/real_data_validation.md](docs/real_data_validation.md)

## Corruption Validation

Committed corruption artifacts were generated from the recorded Yaskawa video-timeline dataset. Scores decreased monotonically across the tested corruption severities. Temporal scrambling produced a smaller effect than frame freezing in these artifacts.

Frame-freeze artifact: [artifacts/frame_freeze_benchmark.json](artifacts/frame_freeze_benchmark.json)

| Severity | Overall | Temporal |
| ---: | ---: | ---: |
| 0% | 99.68 | 99.28 |
| 5% | 99.40 | 98.66 |
| 15% | 99.09 | 97.97 |
| 30% | 98.81 | 97.36 |

Temporal-scramble artifact: [artifacts/temporal_scramble_benchmark.json](artifacts/temporal_scramble_benchmark.json)

| Severity | Overall | Temporal |
| ---: | ---: | ---: |
| 0% | 99.68 | 99.28 |
| 5% | 99.64 | 99.19 |
| 15% | 99.58 | 99.07 |
| 30% | 99.51 | 98.96 |

## CLI Reference Summary

| Command | Verified purpose |
| --- | --- |
| `worldbench validate DATASET_PATH` | validate a WorldBench frame dataset |
| `worldbench eval DATASET_PATH --predictions PATH` | score a frame dataset against prediction frames |
| `worldbench eval-video --ground-truth PATH --prediction PATH --skip-context INTEGER` | score one matching video pair |
| `worldbench eval-batch --ground-truth PATH --predictions PATH --name TEXT` | score a checkpoint folder across matching episode videos |
| `worldbench gate --baseline PATH --candidate PATH` | compare batch artifacts and return PASS or FAIL |
| `worldbench import-lerobot --out PATH` | import LeRobot data into WorldBench format |
| `worldbench compare TARGET RUN_B` | compare result files or two model folders |
| `worldbench report RESULT_JSON --output PATH` | generate a Markdown report |
| `worldbench dashboard RESULT_JSON_OR_DATASET_PATH --no-open` | launch a local dashboard |

Run `worldbench COMMAND --help` for the installed version's exact options.

## Python API Summary

```python
from worldbench import WorldBench

result = WorldBench("examples/demo_dataset").evaluate(
    predictions="examples/demo_dataset/good_model"
)
print(result.score)
result.save_json(".worldbench/readme-quickstart/result.json")
```

Public SDK exports include `WorldBench`, `WorldModelRun`, `Metrics`, `evaluate`, `load_dataset`, `EvaluationResult`, and `MetricResult`.

## Dataset Format

The frame-dataset layout is:

```text
dataset/
  episode_001/
    frames/
    predictions/
    actions.json
    states.json
    metadata.json
```

`actions.json` records timestep `t`, optional timestamps/provenance, an `action` value, optional `dx`/`dy`, and optional gripper state. `states.json` records timestep `t`, optional timestamps/provenance, optional `observation_state`, and optional synthetic tracker coordinates. `metadata.json` stores episode identity, robot/task labels, FPS, and optional LeRobot provenance fields.

The video workflow accepts one video per episode. Ground truth and prediction folders are paired by identical relative POSIX paths, with matching future-frame count after `--skip-context`, resolution, and FPS.

Details: [docs/DATA_FORMAT.md](docs/DATA_FORMAT.md)

## Current Limitations

- The public single-rollout NanoWM artifact covers one rollout and eight generated future frames.
- The NanoWM artifact is not a standardized leaderboard result or model accuracy claim.
- Arbitrary numeric robot actions require explicit semantics or an action adapter before Action Consistency is meaningful.
- Real-world Object Permanence and Contact Realism require reliable tracking support.
- Temporal scrambling currently causes a smaller score decrease than frame freezing in the committed corruption artifacts.
- WorldBench evaluates saved predictions; it does not run arbitrary model inference.
- Normal CI does not download LeRobot datasets or run network integration tests.

## Roadmap

### Working now

- direct video-pair evaluation
- multi-episode batch evaluation
- per-horizon metric summaries
- regression gate
- native LeRobot import
- single-rollout NanoWM integration artifact
- frame-freeze and temporal-scramble corruption artifacts

### Next

1. explicit action-adapter registry
2. evaluate more real-model rollouts
3. evaluate a second real model
4. get an external user

### Later

- simulator adapters
- ROS bags
- shared reports
- standardized leaderboard

Details: [docs/ROADMAP.md](docs/ROADMAP.md)

## Contributing

Use a supported Python version, install the development dependencies, and run the local checks before sending changes:

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
python -m build
```

Network LeRobot tests are marked `integration` and are excluded from the default test command.

## License

WorldBench is licensed under Apache-2.0. See [LICENSE](LICENSE).
