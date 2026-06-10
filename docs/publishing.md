# Publishing

WorldBench is prepared for PyPI-style packaging. Do not upload automatically; these commands are for maintainers during release.

## Build

```bash
python -m pip install --upgrade build twine
python -m build
twine check dist/*
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

Only publish to PyPI after GitHub CI passes and TestPyPI installation has been checked.

```bash
twine upload dist/*
```

## Package Name Note

If `worldbench` is unavailable on PyPI, use a package name such as `worldbench-ai` and update:

```text
pyproject.toml
README install commands
release notes
```

## Release Hygiene

- Keep `version` in `pyproject.toml` aligned with the Git tag.
- Keep release notes in `docs/release_notes_<version>.md`.
- Do not publish claims for planned adapters or cloud features until they exist.
- Rebuild demo assets only when the visual demo changes.
