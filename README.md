# WorldBench

### Evaluate robotics world models with one command.

[![tests](https://github.com/tigee1311/worldbench/actions/workflows/tests.yml/badge.svg)](https://github.com/tigee1311/worldbench/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)

WorldBench catches when a robot world model looks right but is actually wrong: it checks whether generated futures follow robot actions, contact physics, temporal consistency, and object permanence.

<p align="center">
  <img src="assets/demo/worldbench_demo.gif" width="850" alt="WorldBench demo showing robot world-model evaluation" />
</p>

```bash
git clone https://github.com/tigee1311/worldbench.git
cd worldbench
pip install -e ".[dev,video]"
worldbench demo
worldbench eval examples/demo_dataset --predictions examples/demo_dataset/bad_model
worldbench dashboard .worldbench/runs/latest/result.json
```

```text
WorldBench Report
Overall Score: 42/100
Action Consistency: 31/100
Contact Realism: 20/100
Object Permanence: 55/100

Main failure:
The model generates plausible frames but ignores the robot action sequence.
```

**Not another world model. The test suite for world models.**

Features • Quickstart • CLI • Python SDK • Metrics • Roadmap

## Quickstart

```bash
git clone https://github.com/tigee1311/worldbench.git
cd worldbench
pip install -e ".[dev,video]"

worldbench demo
worldbench validate examples/demo_dataset
worldbench eval examples/demo_dataset --predictions examples/demo_dataset/good_model
worldbench eval examples/demo_dataset --predictions examples/demo_dataset/bad_model
worldbench report .worldbench/runs/latest/result.json
worldbench dashboard .worldbench/runs/latest/result.json
```

`worldbench eval` writes timestamped runs under `.worldbench/runs/` and also updates `.worldbench/runs/latest/result.json` for quick iteration.

## What It Does

WorldBench is a Python SDK, CLI, and local dashboard for evaluating robotics world-model rollouts. It takes a robot rollout dataset plus predicted future frames and produces:

- Control-aware metric scores
- Per-episode failure evidence
- Good vs bad model comparisons
- Markdown reports
- A zero-dependency local HTML dashboard
- A synthetic demo that works without robots, GPUs, or model training

## Why WorldBench?

Robotics world models can make futures that look realistic while still being wrong for control. A prediction is not useful if it moves opposite the commanded action, teleports a cube before contact, drops a task object, or flickers across the rollout.

WorldBench focuses on the failure modes that matter when a robot planner consumes generated futures.

## Why Not Just SSIM/PSNR?

Traditional video metrics can say a prediction is good even when it is useless for robotics.

A world model can score high visually while:

- moving the robot opposite the commanded action
- teleporting objects before contact
- dropping task-relevant objects
- flickering across frames
- breaking state/action alignment

WorldBench adds control-aware metrics for robotics world models.

## Installation

```bash
pip install -e .
```

For tests and local development:

```bash
pip install -e ".[dev]"
pytest
```

For regenerating the README demo video:

```bash
pip install -e ".[video]"
python scripts/make_demo_video.py
```

`scikit-image` is optional for SSIM:

```bash
pip install -e ".[vision]"
```

If `scikit-image` is not installed, WorldBench uses a lightweight NumPy fallback.

## CLI Usage

```bash
worldbench init <path>
worldbench demo
worldbench validate <dataset_path>
worldbench eval <dataset_path> --predictions <predictions_path>
worldbench compare <run_a/result.json> <run_b/result.json>
worldbench report <result_json>
worldbench dashboard <result_json_or_dataset_path>
worldbench make-demo-video
```

Example:

```bash
worldbench demo
worldbench eval examples/demo_dataset --predictions examples/demo_dataset/bad_model
worldbench report .worldbench/runs/latest/result.json
worldbench dashboard .worldbench/runs/latest/result.json
```

## Python SDK Usage

```python
from worldbench import WorldBench, WorldModelRun

bench = WorldBench(dataset="examples/demo_dataset")
result = bench.evaluate(predictions="examples/demo_dataset/good_model")
result.print_summary()
result.save_report("report.md")
```

Convenience API:

```python
from worldbench import evaluate, load_dataset

dataset = load_dataset("examples/demo_dataset")
result = evaluate(dataset)
print(result.score)
```

Composable metrics:

```python
from worldbench import Metrics, WorldBench

bench = WorldBench("examples/demo_dataset")
result = bench.run(
    metrics=[
        Metrics.visual_similarity(),
        Metrics.action_consistency(),
        Metrics.temporal_stability(),
    ],
    predictions="examples/demo_dataset/good_model",
)
```

## Dataset Format

```text
dataset/
  episode_001/
    frames/
      000.png
      001.png
      002.png
    predictions/
      000.png
      001.png
      002.png
    actions.json
    states.json
    metadata.json
```

`actions.json`:

```json
[
  {"t": 0, "action": "move_right", "dx": 1.0, "dy": 0.0, "gripper": "open"},
  {"t": 1, "action": "move_right", "dx": 1.0, "dy": 0.0, "gripper": "open"},
  {"t": 2, "action": "close_gripper", "dx": 0.0, "dy": 0.0, "gripper": "closed"}
]
```

`states.json`:

```json
[
  {"t": 0, "robot_x": 20, "robot_y": 50, "object_x": 80, "object_y": 50},
  {"t": 1, "robot_x": 30, "robot_y": 50, "object_x": 80, "object_y": 50},
  {"t": 2, "robot_x": 40, "robot_y": 50, "object_x": 80, "object_y": 50}
]
```

`metadata.json`:

```json
{
  "name": "push_cube_demo",
  "robot": "synthetic_2d_arm",
  "task": "push cube",
  "fps": 5,
  "description": "Synthetic robot rollout for world-model evaluation"
}
```

Prediction folders can be dataset-native:

```text
episode_001/predictions/000.png
```

or model-run style:

```text
predictions/episode_001/000.png
```

## Metrics

| Metric | Weight | What it checks |
| --- | ---: | --- |
| Visual similarity | 25% | MSE, PSNR, and SSIM-style structure against ground-truth frames. |
| Action consistency | 30% | Whether visual robot motion follows action logs such as `move_right` or `move_left`. |
| Temporal stability | 20% | Flicker, sudden jumps, and unstable frame-to-frame deltas. |
| Object permanence | 15% | Whether the main task object remains visible and stable. |
| Contact realism | 10% | Whether object motion starts before plausible robot/object contact. |

The default overall score is a weighted average across these metrics.

## Example Outputs

### Example Benchmark

| Model | Overall | Action consistency | Contact realism | Object permanence |
| --- | ---: | ---: | ---: | ---: |
| `good_model` | 88 | 91 | 84 | 95 |
| `bad_model` | 42 | 31 | 20 | 55 |

This toy benchmark is generated by `worldbench demo`, but it shows the type of failure WorldBench is designed to catch: realistic-looking predictions that do not follow robot actions or contact physics.

Sample reports:

- [good_model_report.md](examples/sample_reports/good_model_report.md)
- [bad_model_report.md](examples/sample_reports/bad_model_report.md)

## Supported Now Vs Roadmap

| Feature | Status |
| --- | --- |
| Synthetic demo dataset | Supported |
| Good vs bad model comparison | Supported |
| CLI evaluation | Supported |
| Markdown reports | Supported |
| Local dashboard | Supported |
| Action consistency scoring | Supported |
| Object permanence scoring | Supported |
| Contact realism scoring | Supported |
| ROS bag import | Planned |
| LeRobot dataset import | Planned |
| ManiSkill/RLBench adapters | Planned |
| Real robot rollout support | Planned |
| Cloud run sharing | Planned |
| Benchmark leaderboard | Planned |

## Demo Video Generation

The README animation is generated from code, not an external recording.

```bash
python scripts/make_demo_video.py
```

Outputs:

- `assets/demo/worldbench_demo.mp4`
- `assets/demo/worldbench_demo.gif`
- `assets/demo/thumbnail.png`

The generator uses Pillow for drawing. It writes MP4 via `imageio` if installed, or a local `ffmpeg` binary if available. If neither is available, it prints a clear error explaining how to install the `video` extra.

## Name Note

WorldBench is currently an open-source robotics world-model evaluation toolkit in this repository. The name may overlap with research benchmarks using the same name, and the project may be renamed later if needed.

## Contributing

WorldBench is intentionally small and easy to inspect. Useful contributions include:

- New control-aware metrics
- Dataset import adapters
- Better synthetic rollout scenarios
- Dashboard/report polish
- Tests for metric edge cases

Before opening a PR:

```bash
pip install -e ".[dev]"
pytest
```

## License

Apache-2.0. See [LICENSE](LICENSE).
