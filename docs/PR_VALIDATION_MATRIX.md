# PR Validation Matrix

Status values reflect local validation during the split plus GitHub status at
the time each PR was opened. GitHub checks should be treated as authoritative
once they finish.

| Check | PR 1 core-statistics | PR 2 quality-security | PR 3 research-performance | PR 4 docs-governance |
| --- | --- | --- | --- | --- |
| pytest | passed: 157 tests | passed: 157 tests | passed: 159 tests | not applicable locally; docs-only |
| coverage | not applicable | passed: 81.15%, threshold 80% | inherited CI check pending GitHub | not applicable |
| Ruff | passed | passed | passed | passed |
| format | workflow surface passed; broad check deferred to PR 2 | passed broad check | passed broad check | not applicable locally; docs-only |
| mypy | not applicable | passed: 9 files checked | inherited CI check pending GitHub | not applicable |
| Bandit | not applicable | configured scan passed | inherited CI check pending GitHub | not applicable |
| pip-audit | not applicable | clean-environment audit passed | inherited CI check pending GitHub | not applicable |
| build | passed | passed | not required | passed |
| twine | passed | passed | not required | passed |
| demo | passed on PR 1-compatible branch | inherited | inherited | passed |
| checkpoint regression example | passed through v0.4.1 fixture gate and numerical comparison | inherited | inherited | passed |
| v0.4.1 fixture loading | passed | passed through full pytest | passed through full pytest | not applicable |
| recursive numerical comparison | passed: 0 protected numerical differences | inherited | inherited | not applicable |
| fresh wheel install | passed on PR 1-compatible docs branch | inherited | inherited | passed |
| GitHub Actions | pending GitHub | pending GitHub | pending GitHub | pending GitHub |
| CodeQL | not applicable | pending GitHub | pending GitHub | not applicable |
| dependency review | not applicable | pending GitHub | pending GitHub | not applicable |

Known local caveats:

- The existing developer venv contains unrelated packages, so
  `.venv/bin/python -m pip_audit --local --progress-spinner off` reports issues
  in packages not installed by WorldBench's clean CI environment. A clean
  project audit environment passed.
- The unconfigured `bandit -r worldbench` scans an ignored nested
  `worldbench/.venv`; the configured workflow command excludes local venvs and
  passed.
