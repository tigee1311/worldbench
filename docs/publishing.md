# Publishing

WorldBench is prepared for PyPI-style packaging. These notes are for maintainers; do not upload release artifacts until CI passes and the release checklist is complete.

## Build

```bash
rm -rf dist build *.egg-info
python -m pip install --upgrade build twine
python -m build
twine check dist/*
```

The build should produce:

```text
dist/worldbench-0.1.0.tar.gz
dist/worldbench-0.1.0-py3-none-any.whl
```

## Local Wheel Smoke Test

```bash
python -m venv /tmp/worldbench-wheel-test
source /tmp/worldbench-wheel-test/bin/activate
python -m pip install dist/worldbench-0.1.0-py3-none-any.whl
worldbench --help
```

## TestPyPI

```bash
twine upload --repository testpypi dist/*
```

Then verify installation in a fresh environment:

```bash
python -m venv /tmp/worldbench-testpypi
source /tmp/worldbench-testpypi/bin/activate
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple worldbench
worldbench --help
```

## PyPI

Only publish to PyPI after GitHub CI passes, TestPyPI installation has been checked, and the GitHub release notes are ready.

```bash
twine upload dist/*
```

After publishing:

```bash
python -m venv /tmp/worldbench-pypi-test
source /tmp/worldbench-pypi-test/bin/activate
python -m pip install worldbench
worldbench --help
```

## Package Name Note

If `worldbench` is unavailable on PyPI, use a package name such as `worldbench-ai` and update:

```text
pyproject.toml
README install commands
release notes
```

Then rebuild the package from a clean `dist/` directory before uploading.

## Release Hygiene

- Keep `version` in `pyproject.toml` aligned with the Git tag.
- Keep release notes in `docs/release_notes_<version>.md`.
- Do not publish claims for planned adapters or cloud features until they exist.
- Rebuild demo assets only when the visual demo changes.
