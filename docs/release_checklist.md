# Release Checklist

WorldBench 0.4.0 sharpens WorldBench around checkpoint regression testing with metric-coverage-safe gating and explicit configuration.

## 0.4.0 Scope

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
- Composite Score naming with metric coverage, configured-weight coverage, and effective normalized weights
- `worldbench.yml` configuration for enabled metrics, required metrics, weights, and gate policy
- Stricter gate checks for metric sets, weights, config hashes, episode identities, coverage, schema versions, and skip-context settings
- Deprecated synthetic demo commands hidden from the primary CLI surface

## Non-Goals

- New metrics
- New action adapters
- New model experiments
- Leaderboards
- Cloud sharing
- ROS support
- Hosted services
- Statistical hypothesis testing
- A standardized public robotics benchmark

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

- `pyproject.toml` and `worldbench.__version__` both report `0.4.0`.
- README links and images render on GitHub.
- Compact checkpoint-validation artifact links exist.
- No generated videos, PNG frame sequences, ZIP archives, virtual environments, model checkpoints, dataset shards, build output, or temporary run directories are staged.
- Historical tags and releases remain untouched.
- `docs/MIGRATION_V0_4.md` and `docs/release_notes_0.4.0.md` describe user-visible changes.
- The real NanoWM checkpoint artifacts still report 85.67 -> 87.28, +1.61, 9 improved, 1 regressed.

## Local Wheel Smoke Test

Install `dist/worldbench-0.4.0-py3-none-any.whl` in a fresh environment and verify:

```bash
worldbench --help
worldbench eval-video --help
worldbench eval-batch --help
worldbench gate --help
```

Also verify:

```python
import worldbench
assert worldbench.__version__ == "0.4.0"
```

Run one offline checkpoint-regression smoke test that exercises `eval-batch` and `gate` for both PASS and valid-regression FAIL.

## GitHub Release

Suggested release title:

```text
WorldBench v0.4.0 - Metric-coverage-safe checkpoint gates
```

Suggested release summary:

```text
WorldBench v0.4.0 makes checkpoint regression testing more transparent and harder to misuse.

Teams can evaluate identical episode suites for baseline and candidate checkpoints, inspect episode-level regressions, and fail CI when configured thresholds are exceeded. Results now report Composite Score coverage explicitly, store the effective WorldBench configuration, and make the gate fail or warn when runs were produced under incomparable conditions.

Real validation:
- NanoWM-B/2 50k vs 300k
- 10 fixed RT-1 episodes
- Composite Score: 85.67 -> 87.28
- Change: +1.61
- 9 episodes improved
- 1 small regression detected
- Gate: PASS
- Metrics available in this proof: Visual Similarity and Temporal Stability

This validation is a fixed 10-episode proof, not a standardized leaderboard result or universal model ranking.
```

Attach:

```text
worldbench-0.4.0.tar.gz
worldbench-0.4.0-py3-none-any.whl
```

## Publishing

Publishing uses GitHub Actions OIDC trusted publishing through `.github/workflows/publish.yml`.

Workflow inputs:

```text
target: testpypi or pypi
tag: v0.4.0
```

Publish to TestPyPI first, verify a fresh TestPyPI install, then publish to production PyPI and verify a fresh production install.
