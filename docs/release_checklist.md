# Release Checklist

WorldBench 0.2.0 surfaces the completed real-data and real-model validation work.

## 0.2.0 Scope

- Native LeRobot import through the optional `lerobot` extra
- Video and control timeline import modes
- Real robot rollout evaluation
- Source provenance fields on imported actions and states
- Unsupported metric handling with N/A status and reasons
- Weighted overall score renormalization across available metrics
- Frame-freeze corruption benchmark artifact
- Temporal-scramble corruption benchmark artifact
- Compact NanoWM RT-1 single-rollout evaluation artifact
- Updated README and documentation for current behavior
- Python 3.10, 3.11, and 3.12 CI matrix

## Pre-Release Checks

```bash
python3.11 --version
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,video]"
ruff check .
pytest
worldbench --help
worldbench import-lerobot --help
worldbench demo
worldbench validate examples/demo_dataset
worldbench eval examples/demo_dataset --predictions examples/demo_dataset/good_model
worldbench compare examples/demo_dataset --models good_model bad_model
worldbench benchmark --demo
worldbench report .worldbench/runs/latest/result.json
worldbench dashboard .worldbench/runs/latest/result.json --no-open
worldbench import-lerobot --demo --out examples/lerobot_push_cube
worldbench validate examples/lerobot_push_cube
python -m build
twine check dist/*
```

Confirm README links and images render on GitHub.
Confirm compact artifact links exist.
Confirm no generated videos, PNG frame sequences, ZIP archives, virtual environments, or temporary datasets are staged.
Use `docs/demo_video_guide.md` if recording a short Loom or release demo.

## GitHub Release

1. Confirm `pyproject.toml` and `worldbench.__version__` have `0.2.0`.
2. Confirm README badges, links, and quickstart point to `https://github.com/tigee1311/worldbench`.
3. Confirm demo media exists under `assets/demo/`.
4. Confirm package build artifacts pass `twine check`.
5. Confirm GitHub Actions pass for Python 3.10, 3.11, and 3.12.
6. Create a normal Git tag and release only after the synchronized documentation commit is pushed.

Suggested release title:

```text
WorldBench v0.2.0 - Real robot rollout and real-model validation
```

Suggested release summary:

```text
WorldBench 0.2.0 adds native LeRobot import, video/control timelines, real robot rollout support, unavailable-metric handling, corruption validation artifacts, and a compact NanoWM RT-1 single-rollout evaluation proof. The result is not a standardized leaderboard and not a model-accuracy claim.
```

Tag and publish:

```bash
git tag v0.2.0
git push origin v0.2.0
gh release create v0.2.0 --title "WorldBench v0.2.0 - Real robot rollout and real-model validation"
```

If the tag or release already exists, update notes instead of recreating history.
