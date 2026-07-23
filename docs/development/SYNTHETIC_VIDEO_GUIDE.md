# Synthetic Fixture Video Guide

This guide is for maintainers who need to capture local synthetic-fixture assets for development docs or regression tests. It is not part of the public WorldBench product proof.

## Goal

Record a short local fixture walkthrough that shows:

- a deterministic synthetic robot rollout fixture
- a deliberately corrupted prediction that fails control checks
- fixture output comparison
- the generated Markdown report
- the local dashboard
- the real-model proof artifact
- native LeRobot import status

Do not claim ROS support, cloud sharing, a hosted public ranking, standardized benchmark status, or that the synthetic fixture is WorldBench's main validation proof.

## Recording Outline

1. Confirm the repo and environment:

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

2. Generate the fixture and run local commands:

```bash
python scripts/dev/make_synthetic_fixture.py
worldbench validate examples/demo_dataset
worldbench eval examples/demo_dataset --predictions examples/demo_dataset/bad_model
worldbench eval examples/demo_dataset --predictions examples/demo_dataset/good_model
worldbench compare examples/demo_dataset --models good_model bad_model
worldbench report .worldbench/runs/latest/result.json
worldbench dashboard .worldbench/runs/latest/result.json --no-open
```

3. Point out the main failure:

```text
bad_model produces plausible frames but violates robot action/contact dynamics.
```

4. Open the dashboard and show:

- Composite Score
- metric cards
- evidence
- suggested fixes
- frame comparison

5. Close with the positioning:

```text
WorldBench helps detect regressions in saved predictions from video-based robot world-model checkpoints before a team accepts a candidate.
```

## Suggested Narration

WorldBench is regression testing for video-based robotics world models. It compares baseline and candidate predictions on the same episodes and reports aggregate changes, episode-level regressions, and horizon-level degradation.

In this fixture, the corrupted output produces frames that look plausible at a glance, but the robot motion does not follow the action log and the cube moves before contact. The fixture is useful for development checks, not as a real-model benchmark.

The README and website should lead with the real NanoWM 50k to 300k checkpoint comparison. Synthetic assets belong in development docs and tests.

## Capture Settings

- Resolution: 1280x720 or 1920x1080
- Duration: 90-120 seconds
- Use a large terminal font
- Keep the dashboard at 100% browser zoom
- Hide unrelated desktop windows
- Do not show credentials, tokens, or private repos
- Start from the repository root, not from a nested `worldbench/` package folder

## Where To Link It

Keep synthetic fixture recordings in development docs or maintainer notes. Do not add them near the README quickstart or website hero.
