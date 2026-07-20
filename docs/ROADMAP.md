# Roadmap

This roadmap separates verified current behavior from future work. It does not mark unimplemented items complete.

## Working Now

- frame-dataset evaluation with `worldbench eval`
- direct video-pair evaluation with `worldbench eval-video`
- multi-episode checkpoint evaluation with `worldbench eval-batch`
- per-horizon metric summaries for evaluated video/frame prefixes
- baseline-vs-candidate regression gate with `worldbench gate`
- result comparison with `worldbench compare`
- Markdown reporting with `worldbench report`
- local dashboard with `worldbench dashboard`
- native LeRobot import with video and control timelines
- unsupported metric reporting and available-weight renormalization
- committed single-rollout NanoWM integration artifact
- committed frame-freeze and temporal-scramble corruption artifacts

## Next

1. explicit action-adapter registry
2. evaluate more real-model rollouts
3. evaluate a second real model
4. get an external user

## Later

- simulator adapters
- ROS bags
- shared reports
- standardized leaderboard
