# PyPI and TestPyPI Publishing

WorldBench is release-ready as a local Python package. These steps document how maintainers can publish package artifacts when ready.

## Build Locally

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

## Publish to TestPyPI

```bash
python -m twine upload --repository testpypi dist/*
```

Then verify installation in a fresh environment:

```bash
python -m venv /tmp/worldbench-testpypi
source /tmp/worldbench-testpypi/bin/activate
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple worldbench
worldbench --help
```

## Publish to PyPI

Only publish to PyPI after GitHub CI passes and TestPyPI installation has been checked.

```bash
python -m twine upload dist/*
```

## Release Hygiene

- Keep `version` in `pyproject.toml` aligned with the Git tag.
- Keep release notes in `docs/release_notes_<version>.md`.
- Do not publish claims for planned adapters or cloud features until they exist.
- Rebuild demo assets only when the visual demo changes.
