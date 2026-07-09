# Demo Video Guide

WorldBench already has a generated README GIF. A short narrated video or Loom can add proof that the CLI, reports, comparison command, and local dashboard actually run.

## Goal

Record a 90-120 second demo that shows:

- a synthetic robot rollout dataset
- a bad world-model prediction that looks plausible but fails control checks
- `good_model` beating `bad_model`
- the generated Markdown report
- the local dashboard
- the real-model proof artifact
- native LeRobot import status

Do not claim ROS support, cloud sharing, a hosted leaderboard, or standardized benchmark status. Native LeRobot import and real robot rollout evaluation are current capabilities; direct video-pair evaluation, multi-episode aggregation, and leaderboard work remain future roadmap items.

## Recording Outline

1. Open the README and show the GIF for 5-10 seconds.
2. Confirm the repo and environment:

```bash
cd ~/worldbench
source .venv/bin/activate
python --version
which python
python -m pip --version
worldbench --help
```

If `worldbench` is not found, reinstall into the active virtual environment:

```bash
python -m pip install -e ".[dev,video]"
worldbench --help
```

3. Run the demo commands:

```bash
worldbench demo
worldbench validate examples/demo_dataset
worldbench eval examples/demo_dataset --predictions examples/demo_dataset/bad_model
worldbench eval examples/demo_dataset --predictions examples/demo_dataset/good_model
worldbench compare examples/demo_dataset --models good_model bad_model
worldbench benchmark --demo
worldbench report .worldbench/runs/latest/result.json
worldbench dashboard .worldbench/runs/latest/result.json --no-open
```

4. Point out the main failure:

```text
bad_model produces plausible frames but violates robot action/contact dynamics.
```

5. Open the dashboard and show:

- overall score
- metric cards
- evidence
- suggested fixes
- frame comparison

6. Close with the positioning:

```text
WorldBench catches when a robot world model looks right but is actually wrong.
```

## Suggested Narration

WorldBench is a local evaluation toolkit for robotics world models. Instead of only asking whether predicted futures look similar to ground truth, it checks whether they are useful for robot control.

In this demo, the bad model produces frames that look plausible at a glance, but the robot motion does not follow the action log and the cube moves before contact. WorldBench catches that with action consistency, contact realism, object permanence, temporal stability, and visual similarity scores.

The comparison command turns this into a benchmark-style local result: the good model beats the bad model, and the largest gaps explain why. The README also links a compact NanoWM RT-1 artifact, which is a single-rollout integration proof rather than a leaderboard result.

## Capture Settings

- Resolution: 1280x720 or 1920x1080
- Duration: 90-120 seconds
- Use a large terminal font
- Keep the dashboard at 100% browser zoom
- Hide unrelated desktop windows
- Do not show credentials, tokens, or private repos
- Start from the repository root, not from a nested `worldbench/` package folder

## Where To Link It

After recording, add the Loom, YouTube, or GitHub release asset link near the README quickstart. Keep the generated GIF as the README hero.
