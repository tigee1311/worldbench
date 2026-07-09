# Changelog

## Unreleased

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
