# Release Checklist

This checklist is for the current release line. Historical release notes remain in `docs/release_notes_*.md`.

## Current Version

WorldBench `0.4.1` is the current repository version. Do not create a release unless CI passes and the release notes accurately describe implemented behavior only.

## Non-Goals For Release Copy

- Public cross-model rankings.
- Cloud sharing.
- Hosted services.
- Universal robotics evaluation.
- Closed-loop robot-task evaluation.
- Claims of task success from video similarity.
- Claims of external adoption or independent validation without evidence.

## Pre-Release Checks

```bash
python -m pytest
python -m pytest --cov=worldbench --cov-branch --cov-report=term-missing
python -m ruff check .
python -m ruff format --check worldbench tests examples research_metrics benchmarks
python -m mypy
python -m bandit -q -c pyproject.toml -r worldbench --exclude worldbench/.venv
python -m build
python -m twine check dist/*
git diff --check
```

Confirm:

- `pyproject.toml` and `worldbench.__version__` both report `0.4.1`.
- README and docs do not call Composite Score accuracy.
- Historical artifacts under `artifacts/checkpoint_validation/` have not changed unless separately reviewed.
- No videos, frame dumps, datasets, model checkpoints, archives, virtual environments, build output, or credentials are staged.
- `CHANGELOG.md` and release notes describe user-visible changes.
- The NanoWM checkpoint artifacts still report 85.67 -> 87.28, +1.61, 9 improved, 1 regressed.

## Help Snapshot

Verify the supported CLI surfaces:

```bash
worldbench --help
worldbench eval-video --help
worldbench eval-videos --help
worldbench eval-batch --help
worldbench gate --help
worldbench verify-run --help
```

## Local Wheel Smoke Test

Install the built wheel in a fresh environment and verify:

```bash
python -m venv /tmp/worldbench-wheel-test
source /tmp/worldbench-wheel-test/bin/activate
python -m pip install --upgrade pip
python -m pip install dist/worldbench-0.4.1-py3-none-any.whl
worldbench --help
worldbench eval-video --help
worldbench eval-videos --help
worldbench eval-batch --help
worldbench gate --help
worldbench verify-run --help
python - <<'PY'
import worldbench
assert worldbench.__version__ == "0.4.1"
PY
deactivate
```

## Publishing

Publishing uses GitHub Actions OIDC trusted publishing through `.github/workflows/publish.yml`.

Workflow inputs:

```text
target: testpypi or pypi
tag: v0.4.1
```

Publish to TestPyPI first, verify a fresh TestPyPI install, then publish to production PyPI and verify a fresh production install. Do not rebuild during publishing; publish the exact release assets.
