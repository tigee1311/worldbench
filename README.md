# WorldBench

**Not another world model. The test suite for world models.**

WorldBench evaluates robotics world models for action consistency, temporal stability, object permanence, contact realism, and visual prediction quality.

World models can generate realistic-looking futures, but robot teams need to know whether those futures are useful for decision-making. WorldBench turns generated robot rollouts into control-relevant scores, evidence, reports, and a local dashboard that runs on a normal laptop.

## Why World-Model Eval Matters

Robotics world models are increasingly used to predict how a scene will evolve under candidate actions. A video can look plausible while still being wrong in the ways that matter for control: the robot moves opposite the command, objects teleport before contact, the scene flickers, or state/action logs no longer match the generated frames.

WorldBench is built around the idea that a robotics world model should be:

- **Action-consistent:** visual motion should follow logged robot actions.
- **Temporally stable:** futures should not flicker or jump without cause.
- **Physically plausible:** contact and object motion should respect simple interaction constraints.
- **Object-persistent:** task-relevant objects should remain trackable.
- **Visually faithful:** predictions should still match held-out future frames.

## Install

```bash
git clone https://github.com/worldbench/worldbench.git
cd worldbench
pip install -e .
```

For development:

```bash
pip install -e ".[dev,vision]"
pytest
```

`scikit-image` is optional. If it is installed, WorldBench uses SSIM from `skimage`; otherwise it falls back to a lightweight NumPy implementation.

## Quickstart

```bash
pip install -e .
worldbench demo
worldbench validate examples/demo_dataset
worldbench eval examples/demo_dataset --predictions examples/demo_dataset/good_model
worldbench eval examples/demo_dataset --predictions examples/demo_dataset/bad_model
worldbench dashboard .worldbench/runs/<run>/result.json
```

The demo creates two synthetic model outputs:

- `good_model`: follows the robot actions and contact sequence.
- `bad_model`: looks superficially similar but moves the robot in the wrong direction, moves objects before contact, drops an object, and flickers.

The good model should score higher than the bad model.

## Python SDK

```python
from worldbench import WorldBench, WorldModelRun

bench = WorldBench(dataset="examples/demo_dataset")
result = bench.evaluate(predictions="examples/demo_dataset/episode_001/predictions")
result.print_summary()
result.save_report("report.md")
```

Convenience API:

```python
from worldbench import load_dataset, evaluate

dataset = load_dataset("examples/demo_dataset")
result = evaluate(dataset)
print(result.score)
```

Cadenza-style composable metrics:

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

Named model runs:

```python
from worldbench import WorldBench, WorldModelRun

bench = WorldBench("examples/demo_dataset")
good = WorldModelRun("examples/demo_dataset/good_model", name="good_model")
result = bench.evaluate(good)
```

## CLI Usage

```bash
worldbench init <path>
worldbench demo
worldbench validate <dataset_path>
worldbench eval <dataset_path> --predictions <predictions_path>
worldbench compare <run_a/result.json> <run_b/result.json>
worldbench report <result_json>
worldbench dashboard <result_json_or_dataset_path>
```

Evaluation results are saved to:

```text
.worldbench/runs/<timestamp>/result.json
```

Reports are Markdown files suitable for experiment notes, pull requests, or benchmark artifacts.

## Dataset Format

WorldBench expects rollout episodes with aligned image frames, actions, states, and metadata:

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

Prediction folders can be either per-episode:

```text
predictions/episode_001/000.png
```

or the dataset-native:

```text
episode_001/predictions/000.png
```

## Metrics

WorldBench computes a weighted score from five MVP evaluators:

| Metric | Weight | What it checks |
| --- | --- | --- |
| Visual Similarity | 25% | MSE, PSNR, and SSIM-style structural similarity against ground-truth frames. |
| Action Consistency | 30% | Whether visual robot motion follows action logs such as `move_right`, `move_left`, or stationary commands. |
| Temporal Stability | 20% | Frame-to-frame flicker, sudden jumps, and high variance in generated futures. |
| Object Permanence | 15% | Whether the main task object remains visible and stable across predicted frames. |
| Contact Realism | 10% | Whether object motion occurs before plausible robot/object contact. |

The default overall score is:

```text
0.25 * visual_similarity
+ 0.30 * action_consistency
+ 0.20 * temporal_stability
+ 0.15 * object_permanence
+ 0.10 * contact_realism
```

The MVP implementation uses simple image processing so the project works immediately without GPUs, cloud services, model training, or large datasets. The metric modules are intentionally small and replaceable for teams that want to add optical flow, segmentation, pose estimation, ROS logs, or simulator-specific contacts.

## Dashboard

```bash
worldbench dashboard .worldbench/runs/<run>/result.json
```

The local dashboard is served by a lightweight standard-library HTTP server and shows:

- Overall score and metric cards
- Per-episode score table
- Issue list
- Ground-truth vs prediction frame viewer
- Metric timeline chart
- Main failure summary
- Raw JSON payload

## Repository Layout

```text
worldbench/
  worldbench/
    cli.py
    core.py
    dataset.py
    schemas.py
    metrics/
    runners/
    backends/
    dashboard.py
  examples/
  tests/
```

The package is organized like a robotics SDK: clean top-level imports, backend modules, CLI commands, synthetic demo mode, examples, and evaluation runners that can be embedded into larger experiment stacks.

## Roadmap

1. Real robot rollout support
2. ROS bag import
3. LeRobot dataset import
4. RLBench/ManiSkill support
5. Cosmos-style video prediction eval adapter
6. Multi-model benchmark leaderboard
7. Cloud run sharing
8. Training-loop orchestration

## License

Apache-2.0
