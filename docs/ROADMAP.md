# Roadmap

This roadmap separates completed capabilities from future work. Completed items should not be re-listed as planned features.

## Working Now

1. Synthetic demo dataset and good/bad prediction generation.
2. External prediction evaluation against WorldBench datasets.
3. Native Hugging Face LeRobot import through the optional `lerobot` extra.
4. Video and control timeline export modes.
5. Real robot rollout evaluation through imported LeRobot data.
6. Model comparison from prediction folders or saved result files.
7. Unsupported metric handling with N/A status and reasons.
8. Weighted overall score renormalization across available metrics.
9. Frame-freeze corruption validation.
10. Temporal-scramble corruption validation.
11. Single-rollout NanoWM RT-1 real-model evaluation artifact.
12. Markdown reports.
13. Local dashboard.

## Next

1. Direct video-pair evaluation for teams that only have ground-truth and predicted videos.
2. Multi-episode aggregation with clearer per-episode availability reporting.
3. Per-horizon curves for visual and temporal metrics.
4. Regression gate command for CI and model-development workflows.
5. Explicit action-adapter registry for robot-specific numeric action spaces.
6. Second real world model evaluation.
7. External user validation and feedback from teams outside this repository.

## Later

1. ManiSkill/RLBench adapters.
2. ROS bag import.
3. Shared run reports.
4. Standardized leaderboard.

## Not Prioritized Ahead Of Core Evaluation

These are useful later, but should not displace the core evaluation workflow:

- cloud sharing
- leaderboard infrastructure
- ROS support
- large web application work
