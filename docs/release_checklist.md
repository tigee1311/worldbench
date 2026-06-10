# Release Checklist

WorldBench v0.1.0 is the first public MVP for local robotics world-model evaluation.

## v0.1.0 Scope

- CLI evaluation for WorldBench rollout datasets
- SDK entry point with composable metrics
- Synthetic good/bad model demo dataset
- Benchmark-style model comparison
- Experimental LeRobot-style local import
- Local HTML dashboard
- Markdown reports
- Demo GIF/video and screenshot generation scripts
- Tests and GitHub Actions CI

## Pre-Release Checks

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,video]"
python -m pytest
worldbench demo
worldbench validate examples/demo_dataset
worldbench eval examples/demo_dataset --predictions examples/demo_dataset/good_model
worldbench eval examples/demo_dataset --predictions examples/demo_dataset/bad_model
worldbench compare examples/demo_dataset --models good_model bad_model
worldbench benchmark --demo
worldbench report .worldbench/runs/latest/result.json
worldbench dashboard .worldbench/runs/latest/result.json
worldbench import-lerobot --demo --out examples/lerobot_push_cube
worldbench validate examples/lerobot_push_cube
python -m pip install --upgrade build twine
python -m build
twine check dist/*
```

Confirm README links and images render on GitHub.
Confirm the README hero GIF and screenshots render on GitHub.
Use `docs/demo_video_guide.md` if recording a short Loom or release demo.

## GitHub Release

1. Confirm `pyproject.toml` has `version = "0.1.0"`.
2. Confirm the README badges, links, and quickstart point to `https://github.com/tigee1311/worldbench`.
3. Confirm demo media exists under `assets/demo/`.
4. Confirm release notes in `docs/release_notes_v0.1.0.md`.
5. Confirm package build artifacts pass `twine check`.
6. Create GitHub release `v0.1.0` with title:

```text
WorldBench v0.1.0 — Initial public MVP
```

Suggested release notes:

```text
WorldBench is a control-aware evaluation toolkit for robotics world models. This first release includes a synthetic robot rollout demo, CLI evaluation, local dashboard, Markdown reports, good/bad model comparison, benchmark scenarios, action consistency scoring, object permanence scoring, contact realism scoring, and an experimental LeRobot-style import path.
```

Tag and publish:

```bash
git tag v0.1.0
git push origin v0.1.0
gh release create v0.1.0 --title "WorldBench v0.1.0 — Initial public MVP" --notes-file docs/release_notes_v0.1.0.md
```

If the tag or release already exists, update the notes instead of recreating history.
