# Contributing to WorldBench

WorldBench is scoped to regression testing for saved video predictions from robotics world models. Contributions should preserve the core workflow:

```text
same episodes -> baseline predictions vs candidate predictions -> episode and horizon deltas -> reproducible PASS or FAIL gate
```

## Good Fits

- CLI and Python API improvements for saved-video evaluation.
- Metric transparency, provenance, verification, and reproducibility work.
- Explicit adapters for datasets, action schemas, and prediction formats.
- Tests, docs, examples, packaging, and CI hardening.
- Research-only metric experiments that are clearly separated from production metrics.

## Out of Scope

- Real-robot execution.
- Closed-loop policy evaluation.
- Universal robotics leaderboards.
- Claims of task success from video similarity alone.
- Metric-weight or formula changes without comparative evidence.

## Development Setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,video]"
```

## Checks

Run these before opening a pull request:

```bash
python -m pytest
python -m pytest --cov=worldbench --cov-branch --cov-report=term-missing
python -m ruff check .
python -m ruff format --check worldbench tests examples
python -m mypy
python -m bandit -q -c pyproject.toml -r worldbench --exclude worldbench/.venv
python -m build
python -m twine check dist/*
```

## Metrics And Scientific Changes

Do not silently change released metric formulas, weights, or output schemas. Metric changes that affect scientific meaning should be introduced under a research namespace first, documented with corruption tests or model comparisons, and promoted only after review.

## Data And Models

Do not commit datasets, model weights, private videos, credentials, or large generated artifacts. Small JSON, Markdown, and static chart artifacts are acceptable when they make a reproducible result easier to inspect.
