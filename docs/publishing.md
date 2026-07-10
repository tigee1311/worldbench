# Publishing

WorldBench releases are published from GitHub release assets through GitHub Actions OIDC trusted publishing. Do not store PyPI API tokens in the repository and do not upload from a local machine unless trusted publishing is unavailable and the maintainer explicitly chooses that path.

## Build

```bash
rm -rf dist build
find . -maxdepth 2 -type d -name "*.egg-info" -prune -exec rm -rf {} +
python -m build
twine check dist/*
```

For v0.4.0 the clean build should produce exactly:

```text
dist/worldbench-0.4.0.tar.gz
dist/worldbench-0.4.0-py3-none-any.whl
```

## Local Wheel Smoke Test

```bash
python -m venv /tmp/worldbench-wheel-test
source /tmp/worldbench-wheel-test/bin/activate
python -m pip install --upgrade pip
python -m pip install dist/worldbench-0.4.0-py3-none-any.whl
worldbench --help
worldbench eval-video --help
worldbench eval-batch --help
worldbench gate --help
python - <<'PY'
import worldbench
assert worldbench.__version__ == "0.4.0"
PY
deactivate
```

## GitHub Release Assets

Create the GitHub release after CI passes and attach both files:

```text
worldbench-0.4.0.tar.gz
worldbench-0.4.0-py3-none-any.whl
```

The `publish.yml` workflow downloads those release assets and publishes the exact attached distributions. Do not rebuild during publishing.

## TestPyPI

Use the `publish` workflow with:

```text
target: testpypi
tag: v0.4.0
```

Then verify installation in a fresh environment using TestPyPI for WorldBench and PyPI for dependencies:

```bash
python -m venv /tmp/worldbench-testpypi
source /tmp/worldbench-testpypi/bin/activate
python -m pip install --upgrade pip
python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple \
  "worldbench[video]==0.4.0"
worldbench --help
worldbench eval-video --help
worldbench eval-batch --help
worldbench gate --help
deactivate
```

## PyPI

Only publish to PyPI after GitHub CI passes, the GitHub release assets are correct, and TestPyPI installation has been checked.

Use the `publish` workflow with:

```text
target: pypi
tag: v0.4.0
```

After publishing:

```bash
python -m venv /tmp/worldbench-pypi-test
source /tmp/worldbench-pypi-test/bin/activate
python -m pip install --upgrade pip
python -m pip install "worldbench[video]==0.4.0"
worldbench --help
worldbench eval-video --help
worldbench eval-batch --help
worldbench gate --help
deactivate
```

## Release Hygiene

- Keep `version` in `pyproject.toml`, `worldbench.__version__`, and the Git tag aligned.
- Keep release notes accurate about implemented features only.
- Do not publish claims for unfinished adapters, cloud features, hosted services, or standardized leaderboard status.
- Do not commit generated videos, PNG frame dumps, model checkpoints, dataset shards, build output, or credentials.
