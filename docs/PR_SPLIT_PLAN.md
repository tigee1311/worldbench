# PR Split Plan

Source branch: `hardening/worldbench-v0.5`

Base branch: `main`

Goal: split the original 103-file hardening branch into focused, independently
reviewable PRs without merging the large branch directly.

## Dependency Graph

```text
PR 1: hardening/core-statistics
  base: main
  reason: introduces production core changes used by later checks and docs
  includes: CLI modularization, plugins, paired bootstrap, provenance, verify-run

    ↓

PR 2: hardening/quality-security
  base: hardening/core-statistics
  reason: quality checks cover files and APIs introduced by PR 1
  includes: coverage, mypy, Ruff, Bandit, pip-audit, CodeQL, Dependabot, CI

    ↓

PR 3: hardening/research-performance
  base: hardening/quality-security
  reason: research/performance tests use PR 2 dev tooling and format paths
  includes: research-only metrics, corruption harness, performance benchmarks

PR 4: hardening/docs-governance
  base: hardening/core-statistics
  reason: docs can reference PR 1 features without depending on PR 2/3 tooling
  includes: README rewrite, governance, validation protocols, brand/compat docs
```

## Shared-File Strategy

| File | Hunk owner | Strategy |
| --- | --- | --- |
| `pyproject.toml` | PR 2 | Dev dependencies, coverage, Ruff, mypy, and Bandit configuration only. |
| `.github/workflows/tests.yml` | PR 2 | CI quality/security workflow changes only. |
| `worldbench/__init__.py` | PR 1 | Public API exports for plugins, statistics, and verification. |
| `README.md` | PR 4 | Public landing-page rewrite only. |
| `docs/EXTENDING_WORLDBENCH.md` | PR 1 | Required to use the new extension API. |
| `docs/PYTHON_API.md` | PR 1 | Minimal API docs for PR 1 exports. |
| `docs/checkpoint_regression.md` | PR 1 | Paired bootstrap and confidence-gate usage. |
| `docs/ROADMAP.md` | PR 4 | Governance roadmap alignment only. |
| `docs/release_checklist.md` | PR 4 | Release-process documentation only. |

No logical change is duplicated across PRs. Files that contain unrelated
formatting-only changes are assigned to PR 2.

## File Inventory

| Status | File | Assignment |
| --- | --- | --- |
| A | `.github/ISSUE_TEMPLATE/bug_report.yml` | PR 4: docs-governance |
| A | `.github/ISSUE_TEMPLATE/feature_request.yml` | PR 4: docs-governance |
| A | `.github/ISSUE_TEMPLATE/integration_request.yml` | PR 4: docs-governance |
| A | `.github/dependabot.yml` | PR 2: quality-security |
| A | `.github/pull_request_template.md` | PR 4: docs-governance |
| A | `.github/workflows/codeql.yml` | PR 2: quality-security |
| M | `.github/workflows/tests.yml` | PR 2: quality-security |
| A | `CODE_OF_CONDUCT.md` | PR 4: docs-governance |
| A | `CONTRIBUTING.md` | PR 4: docs-governance |
| M | `README.md` | PR 4: docs-governance |
| A | `SECURITY.md` | PR 4: docs-governance |
| A | `SUPPORT.md` | PR 4: docs-governance |
| A | `artifacts/metric_research/README.md` | PR 3: research-performance |
| A | `artifacts/metric_research/corruption_harness.json` | PR 3: research-performance |
| A | `artifacts/metric_research/corruption_harness.md` | PR 3: research-performance |
| A | `artifacts/performance/README.md` | PR 3: research-performance |
| A | `artifacts/performance/latest.json` | PR 3: research-performance |
| A | `benchmarks/performance.py` | PR 3: research-performance |
| A | `docs/BRAND_ASSESSMENT.md` | PR 4: docs-governance |
| A | `docs/COMPATIBILITY_MATRIX.md` | PR 4: docs-governance |
| A | `docs/EXTENDING_WORLDBENCH.md` | PR 1: core-statistics |
| A | `docs/EXTERNAL_PILOT.md` | PR 4: docs-governance |
| A | `docs/HARDENING_AUDIT.md` | PR 4: docs-governance |
| A | `docs/HARDENING_RESULT.md` | PR 4: docs-governance |
| A | `docs/HUMAN_EVALUATION_PROTOCOL.md` | PR 4: docs-governance |
| A | `docs/ISSUE_TRIAGE_PLAN.md` | PR 4: docs-governance |
| A | `docs/METRIC_CARDS.md` | PR 4: docs-governance |
| A | `docs/METRIC_RESEARCH_PLAN.md` | PR 3: research-performance |
| A | `docs/PERFORMANCE.md` | PR 3: research-performance |
| M | `docs/PYTHON_API.md` | PR 1: core-statistics |
| M | `docs/ROADMAP.md` | PR 4: docs-governance |
| A | `docs/SECOND_MODEL_VALIDATION.md` | PR 4: docs-governance |
| M | `docs/checkpoint_regression.md` | PR 1: core-statistics |
| M | `docs/release_checklist.md` | PR 4: docs-governance |
| M | `examples/basic_usage.py` | PR 2: quality-security |
| M | `examples/colab/worldbench_saved_video_demo.ipynb` | PR 2: quality-security |
| M | `examples/compare_models.py` | PR 2: quality-security |
| A | `examples/custom_action_adapter/README.md` | PR 1: core-statistics |
| A | `examples/custom_action_adapter/example_adapter.py` | PR 1: core-statistics |
| A | `examples/custom_metric/README.md` | PR 1: core-statistics |
| A | `examples/custom_metric/run_custom_metric.py` | PR 1: core-statistics |
| A | `examples/external_submission/README.md` | PR 4: docs-governance |
| A | `examples/external_submission/manifest.example.json` | PR 4: docs-governance |
| M | `examples/import_lerobot_style.py` | PR 2: quality-security |
| M | `examples/nanowm_rt1/prepare_worldbench_inputs.py` | PR 2: quality-security |
| M | `examples/quickstart.py` | PR 2: quality-security |
| M | `examples/run_benchmark.py` | PR 2: quality-security |
| M | `pyproject.toml` | PR 2: quality-security |
| A | `research_metrics/__init__.py` | PR 3: research-performance |
| A | `research_metrics/corruption_harness.py` | PR 3: research-performance |
| M | `scripts/dev/make_demo_video.py` | PR 2: quality-security |
| M | `scripts/dev/make_screenshots.py` | PR 2: quality-security |
| M | `scripts/nanowm_checkpoint_validation_kaggle.py` | PR 2: quality-security |
| M | `tests/test_action_consistency_unavailable.py` | PR 1: core-statistics |
| M | `tests/test_checkpoint_regression.py` | PR 1: core-statistics |
| M | `tests/test_config_gate.py` | PR 1: core-statistics |
| M | `tests/test_frame_freeze.py` | PR 1: core-statistics |
| M | `tests/test_lerobot.py` | PR 1: core-statistics |
| M | `tests/test_nanowm_rt1_adapter.py` | PR 1: core-statistics |
| M | `tests/test_object_contact_unavailable.py` | PR 1: core-statistics |
| A | `tests/test_plugins.py` | PR 1: core-statistics |
| A | `tests/test_provenance_verification.py` | PR 1: core-statistics |
| A | `tests/test_research_and_performance_harnesses.py` | PR 3: research-performance |
| M | `tests/test_saved_video_cli.py` | PR 1: core-statistics |
| A | `tests/test_security_hardening.py` | PR 1: core-statistics |
| A | `tests/test_statistics.py` | PR 1: core-statistics |
| M | `tests/test_temporal_scramble.py` | PR 1: core-statistics |
| M | `worldbench/__init__.py` | PR 1: core-statistics |
| M | `worldbench/backends/benchmark.py` | PR 1: core-statistics |
| M | `worldbench/backends/frame_freeze.py` | PR 1: core-statistics |
| M | `worldbench/backends/frame_scramble.py` | PR 1: core-statistics |
| M | `worldbench/backends/lerobot.py` | PR 1: core-statistics |
| M | `worldbench/cli.py` | PR 1: core-statistics |
| A | `worldbench/commands/__init__.py` | PR 1: core-statistics |
| A | `worldbench/commands/common.py` | PR 1: core-statistics |
| A | `worldbench/commands/dashboard.py` | PR 1: core-statistics |
| A | `worldbench/commands/eval_batch.py` | PR 1: core-statistics |
| A | `worldbench/commands/eval_video.py` | PR 1: core-statistics |
| A | `worldbench/commands/gate.py` | PR 1: core-statistics |
| A | `worldbench/commands/import_lerobot.py` | PR 1: core-statistics |
| A | `worldbench/commands/legacy.py` | PR 1: core-statistics |
| A | `worldbench/commands/verify.py` | PR 1: core-statistics |
| M | `worldbench/config.py` | PR 1: core-statistics |
| M | `worldbench/dashboard.py` | PR 1: core-statistics |
| M | `worldbench/dataset.py` | PR 1: core-statistics |
| M | `worldbench/metrics/action_consistency.py` | PR 1: core-statistics |
| M | `worldbench/metrics/contact.py` | PR 1: core-statistics |
| M | `worldbench/metrics/object_permanence.py` | PR 1: core-statistics |
| M | `worldbench/metrics/temporal.py` | PR 1: core-statistics |
| M | `worldbench/metrics/visual.py` | PR 1: core-statistics |
| A | `worldbench/plugins.py` | PR 1: core-statistics |
| A | `worldbench/provenance.py` | PR 1: core-statistics |
| M | `worldbench/runners/__init__.py` | PR 1: core-statistics |
| M | `worldbench/runners/benchmark.py` | PR 1: core-statistics |
| M | `worldbench/runners/comparator.py` | PR 1: core-statistics |
| M | `worldbench/runners/evaluator.py` | PR 1: core-statistics |
| M | `worldbench/runners/regression.py` | PR 1: core-statistics |
| M | `worldbench/runners/reporter.py` | PR 1: core-statistics |
| M | `worldbench/runners/video.py` | PR 1: core-statistics |
| M | `worldbench/schemas.py` | PR 1: core-statistics |
| A | `worldbench/statistics.py` | PR 1: core-statistics |
| M | `worldbench/utils.py` | PR 1: core-statistics |
| A | `worldbench/verification.py` | PR 1: core-statistics |

Supplemental files created during the split:

| File | Assignment |
| --- | --- |
| `docs/V041_COMPATIBILITY_REPORT.md` | PR 1: core-statistics |
| `tests/fixtures/v0_4_1/**` | PR 1: core-statistics |
| `tests/test_v041_compatibility.py` | PR 1: core-statistics, with import-order cleanup in PR 2 |
| `docs/PR_SPLIT_PLAN.md` | PR 4: docs-governance |
| `docs/PR_VALIDATION_MATRIX.md` | PR 4: docs-governance |

## Explicitly Excluded

- No file from the original large hardening branch is deferred.
- No historical result artifact is altered.
- No tag, release, package version, or PyPI publish action is part of any PR.
- Research metrics remain non-production and isolated in PR 3.
