# PR Validation Matrix

Status values reflect local validation during the split, GitHub status after the
PR branches were pushed, and post-merge validation where a PR has already landed.

| Check | PR 1 core-statistics | PR 2 quality-security | PR 3 research-performance | PR 4 docs-governance |
| --- | --- | --- | --- | --- |
| pytest | passed after merge: 174 tests | passed after merge: 174 tests | passed in branch CI | not applicable locally; docs-only |
| coverage | not applicable | passed after merge: 81.29%, threshold 80% | passed through inherited CI check | not applicable |
| Ruff | passed | passed | passed | passed |
| format | workflow surface passed; broad check deferred to PR 2 | passed: `worldbench tests examples` | passed: `worldbench tests examples benchmarks` | not applicable locally; docs-only |
| mypy | not applicable | passed: 9 files checked | passed through inherited CI check | not applicable |
| Bandit | not applicable | configured scan passed | passed through inherited CI check | not applicable |
| pip-audit | not applicable | clean-environment audit passed | passed through inherited CI check | not applicable |
| build | passed | passed | not required | passed |
| twine | passed | passed | not required | passed |
| demo | passed on PR 1-compatible branch | inherited | inherited | passed |
| checkpoint regression example | passed through v0.4.1 fixture gate and numerical comparison | inherited | inherited | passed |
| v0.4.1 fixture loading | passed | passed through full pytest | passed through full pytest | not applicable |
| recursive numerical comparison | passed: 0 protected numerical differences | inherited | inherited | not applicable |
| fresh wheel install | passed on PR 1-compatible docs branch | inherited | inherited | passed |
| GitHub Actions | passed | passed | passed | passed |
| CodeQL | not applicable | passed | passed | not applicable |
| dependency review | not applicable | skipped: requires repository dependency graph support and `DEPENDENCY_REVIEW_ENABLED=true` | skipped: requires repository dependency graph support and `DEPENDENCY_REVIEW_ENABLED=true` | not applicable |

Known local caveats:

- The existing developer venv contains unrelated packages, so
  `.venv/bin/python -m pip_audit` can report issues in packages not installed
  by WorldBench's clean CI environment. The clean CI dependency vulnerability
  scan passed.
- The unconfigured `bandit -r worldbench` scans an ignored nested
  `worldbench/.venv`; the configured workflow command excludes local venvs and
  passed.
