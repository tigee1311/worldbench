# Hardening Result

Date: 2026-07-27

Original branch: `hardening/worldbench-v0.5`

Split branches:

- `hardening/core-statistics`
- `hardening/quality-security`
- `hardening/research-performance`
- `hardening/docs-governance`

As of the PR #13 documentation review on 2026-07-28, `hardening/core-statistics`
and `hardening/quality-security` have been merged into `main`.
`hardening/research-performance` remains open and research-only. No release was
created, no tag was created or overwritten, and the original hardening branch
was preserved.

## Completed

- Modularized the CLI into `worldbench/commands/` while keeping `worldbench/cli.py` as a thin registration layer.
- Preserved existing command surfaces; help diff is limited to the new `verify-run` command and opt-in bootstrap flags on `gate`.
- Added explicit plugin protocols and deterministic registries for metrics, action adapters, dataset adapters, and prediction-format adapters.
- Added plugin version provenance and tests for duplicate names, deterministic ordering, unsupported results, and plugin failures.
- Added opt-in paired bootstrap intervals for checkpoint gates with deterministic seed, configurable samples, confidence level, small-sample warnings, and optional lower-bound gating.
- Added provenance helpers for input SHA-256 hashes, configuration hashes, package version, Git commit, Python/OS/architecture, decoder backend, OpenCV/imageio/imageio-ffmpeg/FFmpeg versions, codec metadata, alignment, trimming, resizing, FPS mismatch, plugin versions, and bootstrap config.
- Added `worldbench verify-run` for bounded JSON verification, local input hash checks, config hash checks, package-version warnings, and metric-version checks.
- Added metric coverage and available/unavailable metric display to terminal and Markdown report surfaces.
- Added `docs/METRIC_CARDS.md`.
- Added incremental mypy, pytest-cov branch coverage, Ruff `I/B/RUF100`, Bandit, pip-audit, CodeQL, Dependabot, dependency review, build, and twine checks.
- Set initial coverage threshold at 80% based on measured 81.15% total coverage
  on the split quality branch.
- Added governance files, issue templates, PR template, support/security policy, and roadmap/triage docs.
- Shortened the README into a focused landing page and moved deeper material to linked docs.
- Added compatibility matrix, brand assessment, external pilot protocol, human evaluation protocol, and second-model validation plan.
- Added performance benchmark harness and documentation.
- Added security tests for verifier JSON limits and parent-directory traversal in recorded paths.
- Updated release checklist for version `0.4.1`.

## Experimental Only

- Added `research_metrics/` corruption harness for candidate metric experiments.
- Generated small research artifacts in `artifacts/metric_research/`.
- Production metric formulas and weights were not changed.
- Streaming/chunked video decoding was documented but not implemented because it needs golden-result equivalence evidence.

## Requires External Evidence

- External users or repeated team usage.
- Human judgment calibration.
- Second unrelated model validation with real inference and evaluation.
- Real-robot task success correlation.
- Commercial willingness to pay.
- Testimonials or adoption claims.
- Legal/trademark clearance for the project name.

## Deferred

- Production replacement of temporal, learned-feature, optical-flow, object-track, or physical-consistency metrics: requires comparative evidence.
- Metric-weight changes: requires scientific review and explicit schema/version handling.
- Full streaming decoder: requires output-equivalence tests against current full-frame decode behavior.
- Repository rename: high collision risk documented, but no rename was authorized.
- Cloud sharing, public leaderboard, and generic ROS support: deferred until concrete validated user need.

## Validation Results

Detailed split validation is recorded in
[PR_VALIDATION_MATRIX.md](PR_VALIDATION_MATRIX.md).

Highlights:

- PR 1: `pytest -q` passed after merge with 174 tests; v0.4.1 fixture loading passed; recursive numerical comparison found 0 protected numerical differences.
- PR 2: post-merge coverage passed at 81.29% against an 80% threshold; mypy passed for 9 checked source files; configured Bandit passed; clean CI pip-audit passed.
- PR 3: research/performance checks passed in branch CI; documented research and benchmark commands ran during the split; production metrics remained unchanged.
- PR 4: documentation-only validation is limited to link/content review, `git diff --check`, and README accuracy checks.

## Compatibility Notes

- Existing saved legacy batch artifacts still load through `gate`.
- `eval-videos --reference` remains a backward-compatible alias.
- Existing `eval-video`, `eval-videos`, `eval-batch`, and `gate` help output is unchanged except for intentional opt-in gate flags.
- New result fields are additive.
- `gate` uncertainty output remains disabled by default.

## Rating After This Pass

These ratings describe repository maturity only. They do not credit adoption, users, revenue, testimonials, or independent validation that does not exist.

| Area | Rating |
| --- | ---: |
| Engineering | 8.0/10 |
| Scientific rigor | 6.5/10 |
| Developer experience | 7.5/10 |
| Extensibility | 7.5/10 |
| Reproducibility | 8.0/10 |
| Security | 6.5/10 |
| Community readiness | 7.0/10 |
| Commercial readiness | 4.0/10 |
