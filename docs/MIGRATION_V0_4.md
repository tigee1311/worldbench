# Migrating From 0.3 To 0.4

## Score naming and schema

Evaluation and batch artifacts use schema version `2`. `Composite Score` replaces user-facing `Overall Score` because unavailable metrics are excluded and available weights are renormalized. The JSON field `composite_score` is canonical; legacy `score`, `weights`, and batch `aggregate.overall` remain for compatibility.

New artifacts include metric coverage, configured-weight coverage, effective normalized weights, effective configuration, configuration hash, dataset identity, schema version, and WorldBench version. Schema-v1 evaluation and batch JSON remains loadable. Coverage and default weights are inferred when possible, and the gate warns when old artifacts lack content or configuration hashes.

## Configuration

Add `worldbench.yml` to define enabled, disabled, and required metrics; weights; gate thresholds; and strict matching. The CLI auto-detects this file in the current directory or accepts `--config PATH`.

Configuration precedence is:

1. Command-line gate flags
2. An explicit `--config PATH`
3. `worldbench.yml` in the current working directory
4. Built-in defaults

## Gate behavior

The gate now fails when a baseline metric disappears, a required metric is unavailable, coverage falls below configured thresholds, or strict evaluation settings differ. Identical episode IDs are still mandatory. Use `--no-strict-config-match` only for an intentional exploratory comparison; warnings remain visible in the gate artifact.

## Deprecated commands

`demo`, `benchmark`, `make-demo-video`, and `make-screenshots` are hidden and deprecated. They remain callable during 0.4 to avoid an abrupt break and are planned for removal in 0.5. Contributor equivalents live under `scripts/dev/`.
