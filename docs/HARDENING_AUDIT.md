# WorldBench Hardening Audit

Audit date: 2026-07-27

Scope: source, tests, docs, examples, artifacts, packaging, CI, governance, reproducibility, security, branding readiness, and external-validation readiness. This audit preserves WorldBench's narrow scope: regression testing for saved video-based robot world-model predictions on the same episodes.

## Classification

| Class | Meaning |
| --- | --- |
| A. Fix now | Low-risk repository improvement that can be independently verified. |
| B. Research experiment required | Change could affect scientific meaning and needs comparative evidence before production. |
| C. External validation required | Repository edits can create protocol, but cannot honestly claim completion. |

## Findings

| ID | Severity | Category | Class | Exact file and line | Observed behavior | Risk | Recommended change | Can be fixed now | Evidence required | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WB-HARD-001 | High | CLI maintainability | A | `worldbench/cli.py:51`, `worldbench/cli.py:303`, `worldbench/cli.py:558`, `worldbench/cli.py:635`, `worldbench/cli.py:1292` | The CLI is a single 1,292-line module containing command registration, command bodies, formatting helpers, hidden maintainer commands, and saved-video report generation. | Larger CLI changes are harder to review, command compatibility is harder to test, and new commands increase circular-import risk. | Move command implementations into `worldbench/commands/` modules and keep `worldbench/cli.py` as registration/dispatch. Snapshot and compare help output. | yes | Help-output diff, CLI tests, full pytest. | Fixed |
| WB-HARD-002 | High | Extension API | A | `worldbench/config.py:14`, `worldbench/config.py:67`, `worldbench/runners/evaluator.py:27`, `worldbench/metrics/action_consistency.py:39` | Metric names are fixed in config, built-in metrics are constructed directly, and Action Consistency reports that raw numeric actions require an adapter while no public adapter registry exists. | Third-party metrics/adapters require private patterns or forks; duplicate names and unsupported capabilities have no shared contract. | Add explicit plugin protocols and deterministic registries for metrics, action adapters, dataset adapters, and prediction adapters. Record plugin versions in provenance. | yes | Registry tests for duplicates, ordering, failures, unsupported results, and provenance. | Fixed |
| WB-HARD-003 | High | Statistical validity | B | `worldbench/runners/regression.py:217`, `worldbench/runners/regression.py:256`, `docs/checkpoint_regression.md:180`, `docs/checkpoint_regression.md:229` | Gates compare point estimates and episode counts, but do not provide paired uncertainty intervals over baseline-vs-candidate episode deltas. Documentation explicitly says no statistical model is included yet. | Users may overinterpret a small mean delta, especially on the 10-episode public proof. | Add opt-in paired bootstrap confidence intervals and optional confidence-lower-bound gate. Keep existing gate defaults unchanged. | yes, if opt-in and documented | Synthetic deterministic bootstrap tests and documentation of limitations. | Fixed as opt-in; production scientific policy still requires evidence |
| WB-HARD-004 | High | Provenance and reproducibility | A | `worldbench/runners/video.py:113`, `worldbench/runners/video.py:116`, `worldbench/runners/video.py:143`, `worldbench/runners/regression.py:98`, `worldbench/runners/regression.py:120` | Results record some alignment/config metadata, but not SHA-256 hashes for every input video, decoder versions, OS/architecture, Git commit, FFmpeg/OpenCV versions, metric/plugin versions, or path-redacted input manifests. Some path fields can contain full absolute paths. | Results are harder to verify later and may leak private local paths. | Add safe provenance capture, input hashes, environment metadata, plugin versions, and `worldbench verify-run`. Redact private absolute paths by default. | yes | Provenance and hash-mismatch tests, verify-run CLI tests. | Fixed |
| WB-HARD-005 | Medium | Performance and memory | B | `worldbench/runners/video.py:29`, `worldbench/runners/video.py:181`, `worldbench/runners/video.py:474` | Video decoding loads every frame into a list before alignment/scoring. Comparison artifact generation decodes both videos again. | Long or high-resolution videos can consume unbounded memory and do duplicate decode work. | Add performance benchmarks and document streaming/chunking design. Only implement streaming after proving no metric semantic changes. | partially | Benchmark runtime/memory data and equality tests before any streaming implementation. | Benchmark added; streaming deferred |
| WB-HARD-006 | Medium | Package security | A | `worldbench/utils.py:26`, `worldbench/config.py:132`, `worldbench/runners/regression.py:188` | JSON/YAML reads use normal parsers without a WorldBench-level file-size guard or clearer malformed-result diagnostics. | Accidentally huge or malformed untrusted result/config files can consume memory or produce unclear errors. | Add bounded JSON reads for result verification and tests for oversized/malformed JSON. Keep compatibility for normal artifacts. | yes | Security tests for oversized/malformed JSON and corrupted reports. | Fixed for result verification |
| WB-HARD-007 | Medium | CI consistency | A | `.github/workflows/tests.yml:18`, `.github/workflows/tests.yml:20`, `.github/workflows/tests.yml:22`, `.github/workflows/tests.yml:31` | CI runs tests/lint/build, but no coverage, type checking, dependency vulnerability scan, or static-security workflow. Format check covers only selected files. | Regressions in unformatted files, untyped public APIs, and security-sensitive code can land unnoticed. | Add incremental type checking, pytest-cov, full format check for intended surfaces, CodeQL/security scan, dependency review, and Dependabot. | yes | Local runs and workflow files. | Fixed |
| WB-HARD-008 | Medium | Typing | A | `pyproject.toml:46`, `pyproject.toml:48`, `pyproject.toml:73` | No type checker dependency or configuration exists. Public schemas and runner APIs rely on partial annotations but are not checked. | Public API changes can silently break callers and plugin authors. | Add incremental mypy or Pyright configuration focused on public API, schemas, evaluator, comparator/gate, plugin interfaces, provenance, and statistics. | yes | Type-checker run in CI and locally. | Fixed |
| WB-HARD-009 | Medium | Test coverage | A | `pyproject.toml:48`, `pyproject.toml:66`, `.github/workflows/tests.yml:18` | `pytest-cov` is absent and CI does not measure line or branch coverage. | Test gaps are hard to see, and future changes can reduce coverage silently. | Add coverage config, XML output, branch coverage, and an initial threshold based on measured reality. | yes | Coverage report and threshold justification. | Fixed |
| WB-HARD-010 | Medium | Ruff/code quality | A | `pyproject.toml:73` | Ruff currently enables only `E4`, `E7`, `E9`, and `F`. Import sorting, bugbear checks, and stale noqa detection are not enabled. | Common maintainability and bug patterns are not checked. | Add targeted rule groups such as `I`, `B`, and `RUF100` after fixing violations. Avoid broad unrelated churn. | yes | Ruff check and format check. | Fixed |
| WB-HARD-011 | Medium | Security governance | A | `.github/workflows/tests.yml:1`, `.github/workflows/publish.yml:1`, `.github/ISSUE_TEMPLATE/test-worldbench.yml:8` | There is no `SECURITY.md`, CodeQL workflow, Dependabot config, or vulnerability scanning workflow. The external tester template warns about credentials, but disclosure handling is not documented. | Vulnerability reports and dependency updates have no standard route. | Add security policy, CodeQL/dependency scan, Dependabot, and responsible-disclosure guidance. | yes | Workflow lint/local scan where possible. | Fixed |
| WB-HARD-012 | Medium | Metric transparency | A | `worldbench/metrics/visual.py:39`, `worldbench/metrics/temporal.py:40`, `worldbench/metrics/action_consistency.py:157`, `worldbench/runners/reporter.py:43`, `worldbench/dashboard.py:427` | Metric formulas live in code and partial docs; result surfaces show coverage but not a full metric-card explanation or warnings when only a small subset contributes. | Users can overinterpret a Composite Score without knowing assumptions, unsupported situations, or what the metrics do not establish. | Add `docs/METRIC_CARDS.md`; show available/unavailable metrics and configured-weight coverage consistently in terminal, Markdown, and dashboard. | yes | Docs and rendering tests. | Fixed |
| WB-HARD-013 | Medium | Documentation clarity | A | `README.md:1`, `README.md:219`, `README.md:251`, `README.md:304`, `README.md:430` | The README is 430 lines and mixes landing-page positioning, deep metric methodology, LeRobot/NanoWM details, corruption artifacts, roadmap, and contributor setup. | New users must read too much before reaching the core workflow. | Shorten README and move deep material to dedicated docs without deleting historical documentation. | yes | README review and docs link checks. | Fixed |
| WB-HARD-014 | Medium | External-validation readiness | C | `docs/ROADMAP.md:24`, `docs/ROADMAP.md:27`, `.github/ISSUE_TEMPLATE/test-worldbench.yml:1` | Roadmap says to evaluate a second real model and get an external user, and a tester request template exists, but there is no pilot protocol, human-evaluation protocol, or second-model validation plan. | Repository could imply validation that has not happened, or pilots could be inconsistent. | Add external pilot kit, human evaluation protocol, and second-model validation plan. Do not claim completion. | no | Independent user/pilot results, blinded human study, and second-model execution evidence. | Protocols created; evidence still required |
| WB-HARD-015 | Medium | Branding conflicts | C | `README.md:1`, `pyproject.toml:6`, `.github/workflows/publish.yml:28` | The project, package, and publication target use the name `WorldBench`; no collision assessment is committed. | Name collision or package/searchability issues could become expensive after adoption. | Research active collisions and create `docs/BRAND_ASSESSMENT.md`. Do not rename automatically. | no | Primary-source search evidence and explicit rename decision. | Assessment created; rename decision required |
| WB-HARD-016 | Low | Public Python API | A | `docs/PYTHON_API.md:1`, `docs/PYTHON_API.md:26`, `worldbench/core.py:62`, `worldbench/core.py:92` | The public API docs are short and do not describe extension registration, provenance verification, or batch/gate APIs. | Plugin authors and API consumers may depend on internals. | Expand API docs and export stable extension/provenance/statistics interfaces. | yes | Docs and import tests. | Fixed |
| WB-HARD-017 | Low | Package reproducibility | A | `pyproject.toml:48`, `.github/workflows/tests.yml:38`, baseline command output | The source version is `0.4.1`, but the local editable install metadata reported `worldbench 0.3.0.dev0` during the initial state check. No CI check compares installed metadata with `worldbench.__version__`. | Local release checks can miss stale editable metadata or packaging drift. | Add package metadata/version smoke tests and fresh wheel install validation. | yes | Wheel install test and metadata/version assertion. | Fixed in local install and CI smoke |
| WB-HARD-018 | Low | Contributor experience | A | `.github/ISSUE_TEMPLATE/bug_report.md:1`, `.github/ISSUE_TEMPLATE/feature_request.md:1`, missing `CONTRIBUTING.md`, missing `SUPPORT.md` | Issue templates exist, but requested YAML templates, PR template, contributor guide, support policy, and code of conduct are missing. | External contributors have incomplete guidance and maintainers receive lower-quality issues. | Add governance files and issue/PR templates aligned with WorldBench's narrow scope. | yes | File review and template completeness. | Fixed |
| WB-HARD-019 | Low | Research harness | B | `docs/METRIC_VALIDATION.md:3`, `artifacts/frame_freeze_benchmark.json:1`, `artifacts/temporal_scramble_benchmark.json:1` | Corruption artifacts exist for frame freeze and temporal scramble, but there is no reusable research-only harness comparing candidate metrics against corruptions. | Metric experiments can be ad hoc and accidentally promoted without evidence. | Add a non-production `research_metrics/` harness and `docs/METRIC_RESEARCH_PLAN.md`; commit only small JSON/Markdown artifacts. | no for production metric changes | Harness output, monotonicity/runtime data, and written review before production adoption. | Research harness added; production metric changes deferred |
| WB-HARD-020 | Low | Release engineering | A | `docs/release_checklist.md:50`, `docs/release_checklist.md:73`, `docs/publishing.md:34` | Release docs include useful checks, but some historical checklist text still references `0.4.0` assertions while the current public release is `0.4.1`. | Maintainers could copy stale release commands. | Update release engineering docs to separate historical release notes from current release checklist. | yes | Docs review. | Fixed |

## Dimension Coverage

| Dimension | Relevant findings |
| --- | --- |
| Architecture | WB-HARD-001, WB-HARD-002, WB-HARD-016 |
| CLI maintainability | WB-HARD-001 |
| Public Python API | WB-HARD-016 |
| Metric implementations | WB-HARD-003, WB-HARD-012, WB-HARD-019 |
| Regression gate behavior | WB-HARD-003, WB-HARD-004 |
| Statistical validity | WB-HARD-003, WB-HARD-014 |
| Provenance | WB-HARD-004, WB-HARD-017 |
| Performance | WB-HARD-005 |
| Memory usage | WB-HARD-005 |
| Plugin and adapter extensibility | WB-HARD-002, WB-HARD-016 |
| Error handling | WB-HARD-006, WB-HARD-011 |
| Package security | WB-HARD-006, WB-HARD-011 |
| Typing | WB-HARD-008 |
| Test coverage | WB-HARD-009 |
| CI consistency | WB-HARD-007, WB-HARD-010 |
| Documentation clarity | WB-HARD-012, WB-HARD-013, WB-HARD-020 |
| Contributor experience | WB-HARD-018 |
| Release engineering | WB-HARD-017, WB-HARD-020 |
| Branding conflicts | WB-HARD-015 |
| External-validation readiness | WB-HARD-014 |

## Work Categories

### A. Fix Now

WB-HARD-001, WB-HARD-002, WB-HARD-004, WB-HARD-006, WB-HARD-007, WB-HARD-008, WB-HARD-009, WB-HARD-010, WB-HARD-011, WB-HARD-012, WB-HARD-013, WB-HARD-016, WB-HARD-017, WB-HARD-018, WB-HARD-020.

### B. Research Experiment Required

WB-HARD-003 is safe to add as opt-in uncertainty reporting, but any gate policy that treats intervals as formal significance requires more evidence. WB-HARD-005 streaming changes and WB-HARD-019 metric replacements require comparative experiments before production adoption.

### C. External Validation Required

WB-HARD-014 and WB-HARD-015 cannot be completed honestly through repository edits alone. This pass can create protocols and assessments, but external pilots, human calibration, independent model validation, legal review, and adoption evidence remain unproven.
