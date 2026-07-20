# Changelog

## Unreleased

### Changed

- Refreshed README and focused docs to distinguish the single-rollout NanoWM integration artifact, checkpoint-regression workflow, LeRobot timelines, metric availability, and roadmap status using verified code, tests, and artifacts.
- Aligned CI lint and package validation with the documented release-readiness checks.

## 0.4.0 (unreleased)

### Added

- `worldbench.yml` metric profiles and gate policy
- Schema-v2 composite-score coverage, configuration, version, and dataset identity metadata
- Required-metric, minimum-count, minimum-coverage, weight-coverage, episode-regression, and strict-configuration gate checks
- Complete GitHub Actions checkpoint-gate example and focused operator documentation

### Changed

- Renamed user-facing Overall Score to Composite Score; legacy JSON fields remain readable
- Made the real NanoWM 50k-vs-300k checkpoint comparison the primary public proof
- Tightened gate behavior so weaker or materially different evaluations cannot silently pass
- Reduced public CLI help to production evaluation, gate, reporting, import, and validation workflows

### Deprecated

- Synthetic `demo` and `benchmark` commands and maintainer asset commands are hidden in 0.4 and planned for removal in 0.5

### Validation

- The committed NanoWM proof values remain unchanged: 85.67 to 87.28 (`+1.61`), 9 episodes improved, 1 regressed, gate PASS, with Visual Similarity and Temporal Stability only

## 0.3.0

### Added

- Direct video-pair evaluation with `worldbench eval-video`
- Multi-episode checkpoint evaluation with `worldbench eval-batch`
- Per-horizon evaluation curves
- Baseline-vs-candidate regression gates with `worldbench gate`
- Episode-level improvement and regression analysis
- CI-compatible PASS / FAIL exit codes
- Batch and gate artifacts for checkpoint regression workflows
- Real NanoWM 50k vs 300k checkpoint validation

### Changed

- WorldBench can now evaluate checkpoints across identical episode suites
- Results include additive horizon and provenance data
- Development test dependencies now include the optional video stack used by offline video workflow tests

### Validation

- Real checkpoint proof compared NanoWM-B/2 50k vs 300k on 10 fixed RT-1 / Fractal episodes
- Candidate overall mean improved from 85.67 to 87.28 (+1.61)
- Visual Similarity improved by +2.19 and Temporal Stability improved by +0.89
- 9 episodes improved and 1 episode had a small regression (`episode_002.mp4`, -0.33)
- Strict gate PASS and engineering-threshold gate PASS
- This validation is a fixed 10-episode proof, not a standardized leaderboard result or universal model ranking

## v0.2.0

### Added

- Native LeRobot import
- Video/control timelines
- Real robot rollout support
- Frame-freeze benchmark
- Temporal-scramble benchmark
- Real NanoWM evaluation

### Changed

- Unsupported metrics return N/A
- Overall scores renormalize across available metrics

### Fixed

- Arbitrary numeric action vectors are no longer interpreted as zero-motion commands
- Synthetic-only object/contact heuristics no longer create misleading real-world scores

## v0.1.0

Initial public MVP:

- Synthetic robotics world-model demo
- Good vs bad model comparison
- `worldbench compare` model comparison command
- Synthetic benchmark scenarios
- CLI evaluation
- Local dashboard
- Markdown reports
- Action consistency metric
- Temporal stability metric
- Object permanence metric
- Contact realism metric
- Demo GIF/video generator
- Experimental LeRobot-style import
- Dashboard/report screenshot generator
- Example reports and SDK examples
- GitHub Actions test workflow
