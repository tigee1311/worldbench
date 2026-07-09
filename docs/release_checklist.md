# Release Checklist

WorldBench 0.3.0 turns robotics world-model evaluation into checkpoint regression testing.

## 0.3.0 Scope

- Direct video-pair evaluation with `worldbench eval-video`
- Multi-episode checkpoint evaluation with `worldbench eval-batch`
- Per-horizon evaluation curves
- Baseline-vs-candidate regression gates with `worldbench gate`
- Episode-level improvement and regression analysis
- CI-compatible PASS / FAIL exit codes
- Strict video validation for future-frame alignment, resolution, FPS, and frame count
- Batch aggregation across identical episode suites
- Checkpoint compatibility validation before gating
- Real NanoWM-B/2 50k vs 300k checkpoint validation on 10 fixed RT-1 / Fractal episodes

## Non-Goals

- New metrics
- New action adapters
- New model experiments
- Leaderboards
- Cloud sharing
- ROS support
- Hosted services
- Statistical hypothesis testing

## Pre-Release Checks

```bash
ruff check .
pytest
worldbench --help
worldbench eval-video --help
worldbench eval-batch --help
worldbench gate --help
python -m build
twine check dist/*
```

Confirm:

- `pyproject.toml` and `worldbench.__version__` both report `0.3.0`.
- README links and images render on GitHub.
- Compact checkpoint-validation artifact links exist.
- No generated videos, PNG frame sequences, ZIP archives, virtual environments, model checkpoints, dataset shards, build output, or temporary run directories are staged.
- `v0.2.0` tag and release remain untouched.

## Local Wheel Smoke Test

Install `dist/worldbench-0.3.0-py3-none-any.whl` in a fresh environment and verify:

```bash
worldbench --help
worldbench eval-video --help
worldbench eval-batch --help
worldbench gate --help
```

Also verify:

```python
import worldbench
assert worldbench.__version__ == "0.3.0"
```

Run one offline checkpoint-regression smoke test that exercises `eval-batch` and `gate` for both PASS and valid-regression FAIL.

## GitHub Release

Suggested release title:

```text
WorldBench v0.3.0 - Checkpoint regression testing
```

Suggested release summary:

```text
WorldBench v0.3.0 turns robotics world-model evaluation into checkpoint regression testing.

Teams can now evaluate identical episode suites for baseline and candidate checkpoints, compare aggregate and per-horizon behavior, inspect episode-level regressions, and fail CI when configured thresholds are exceeded.

Real validation:
- NanoWM-B/2 50k vs 300k
- 10 fixed RT-1 episodes
- Overall: 85.67 -> 87.28
- Change: +1.61
- 9 episodes improved
- 1 small regression detected
- Strict gate: PASS
- Engineering gate: PASS

This validation is a fixed 10-episode proof, not a standardized leaderboard result or universal model ranking.
```

Attach:

```text
worldbench-0.3.0.tar.gz
worldbench-0.3.0-py3-none-any.whl
```

## Publishing

Publishing uses GitHub Actions OIDC trusted publishing through `.github/workflows/publish.yml`.

Workflow inputs:

```text
target: testpypi or pypi
tag: v0.3.0
```

Publish to TestPyPI first, verify a fresh TestPyPI install, then publish to production PyPI and verify a fresh production install.
