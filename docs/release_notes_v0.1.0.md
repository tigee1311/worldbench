# WorldBench v0.1.0

Initial public MVP for evaluating robotics world-model predictions locally.

WorldBench catches when generated robot futures look plausible but regress under the available saved-prediction checks: action consistency, temporal stability, object permanence, contact realism, and visual similarity against ground truth.

## Highlights

- `worldbench demo` creates a runnable synthetic robot/cube benchmark.
- `worldbench eval` scores model predictions and writes `.worldbench/runs/latest/result.json`.
- `worldbench compare examples/demo_dataset --models good_model bad_model` compares two model folders and writes comparison JSON/Markdown artifacts.
- `worldbench benchmark --demo` generates and runs lightweight synthetic benchmark scenarios.
- `worldbench dashboard` launches a local HTML dashboard with metric cards, issues, frame comparison, and raw JSON.
- `worldbench report` generates Markdown reports.
- `worldbench import-lerobot --demo --out examples/lerobot_push_cube` demonstrates the experimental LeRobot-style local import path.

## Included Metrics

- Visual similarity
- Action consistency
- Temporal stability
- Object permanence
- Contact realism

## Notes

The LeRobot adapter is experimental and local-folder-only. This release does not include official LeRobot integration, ROS bag import, real robot support, cloud run sharing, or a public ranking.
