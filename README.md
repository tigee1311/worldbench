# WorldBench

**WorldBench catches regressions in robot world-model checkpoints before deployment.**

It evaluates baseline and candidate rollout videos on the same episodes, reports hidden metric and episode regressions, and returns a CI-ready `PASS` or `FAIL`.

[![Tests](https://github.com/tigee1311/worldbench/actions/workflows/tests.yml/badge.svg)](https://github.com/tigee1311/worldbench/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![Version](https://img.shields.io/badge/version-0.4.0-blue)
![License](https://img.shields.io/github/license/tigee1311/worldbench)

## Real Checkpoint Proof

WorldBench compared a real NanoWM-B/2 50k baseline with the 300k candidate on the same 10 RT-1 / Fractal episodes.

| Result | Verified value |
| --- | ---: |
| Composite Score | 85.67 -> 87.28 |
| Change | +1.61 |
| Episodes improved | 9 |
| Episodes regressed | 1 |
| Gate | PASS |

The aggregate improved, but WorldBench still surfaced `episode_002.mp4`, which regressed by 0.33 points. Only **Visual Similarity** and **Temporal Stability** were supported by these RGB video pairs. Action Consistency, Object Permanence, and Contact Realism remained `N/A` and were excluded from the composite denominator.

This is a fixed checkpoint-regression proof, not a standardized benchmark, leaderboard, universal model ranking, or accuracy claim. See the [case study](docs/CASE_STUDIES.md), [methodology](docs/checkpoint_validation.md), and [committed artifacts](artifacts/checkpoint_validation/).

## Quickstart

Install video support:

```bash
pip install "worldbench[video]"
```

Use identical ground-truth episode filenames for both checkpoint prediction folders:

```bash
worldbench eval-batch --ground-truth eval_suite/ --predictions checkpoint_50k/ --name checkpoint_50k --config worldbench.yml

worldbench eval-batch --ground-truth eval_suite/ --predictions checkpoint_300k/ --name checkpoint_300k --config worldbench.yml

worldbench gate --baseline checkpoint_50k.json --candidate checkpoint_300k.json --config worldbench.yml
```

`eval-batch` writes JSON plus Markdown reports. `gate` exits `0` on `PASS`, `1` on a valid regression failure, and `2` for invalid input or incomparable episode suites. See [CLI reference](docs/CLI.md) and [data format](docs/DATA_FORMAT.md).

## What WorldBench Evaluates

| Metric | General availability | `N/A` behavior |
| --- | --- | --- |
| Visual Similarity | Aligned ground-truth and predicted RGB frames | No alignable frame pairs |
| Temporal Stability | At least two predicted future frames | Too few future frames |
| Action Consistency | String or `dx`/`dy` actions, or a compatible adapter | Raw action vectors without an adapter |
| Object Permanence | Current deterministic fixture tracker or a tracking adapter | Real scenes without reliable tracking |
| Contact Realism | Current deterministic fixture tracker or robot/object tracking adapters | Real scenes without reliable tracking |

WorldBench never invents an unavailable score. The **Composite Score** renormalizes configured weights across available metrics and always reports:

- available and unsupported metrics
- metric coverage count
- configured-weight coverage
- effective normalized weights
- the effective configuration and its hash

The NanoWM comparison had 2 of 5 configured metrics and 45% configured-weight coverage. See [metric support](docs/metric_support.md) and [metric validation](docs/METRIC_VALIDATION.md).

## CI Regression Gate

```yaml
- name: Gate candidate checkpoint
  run: |
    worldbench gate \
      --baseline artifacts/worldbench/approved-baseline.json \
      --candidate .worldbench/candidate.json \
      --config worldbench.yml
```

The gate rejects disappearing required metrics and can enforce metric count, weight coverage, exact metric profiles and weights, dataset identity, episode identity, skip context, horizon coverage, and schema compatibility. A complete copy-paste workflow is in [examples/github-actions/worldbench-gate.yml](examples/github-actions/worldbench-gate.yml); operational guidance is in [CI integration](docs/CI_INTEGRATION.md).

## Limitations

- The public checkpoint proof covers two NanoWM checkpoints and 10 fixed RT-1 episodes.
- Its composite uses only Visual Similarity and Temporal Stability.
- Raw robot action vectors need a robot-specific adapter before Action Consistency is meaningful.
- Real-world Object Permanence and Contact Realism need reliable tracking adapters.
- Temporal corruption sensitivity remains weaker for some scramble patterns than for frame freezing.
- WorldBench evaluates saved predictions; it does not run arbitrary model inference or provide a hosted leaderboard.

## Looking For Early Testers

Training a robot world model?

Send baseline and candidate prediction videos from the same episodes. I will help run your first WorldBench evaluation and send you the results.

**Looking for 3 early testing partners.**

- [Request an evaluation](https://github.com/tigee1311/worldbench/issues/new?template=test-worldbench.yml)
- [Email writetoayushadi@gmail.com](mailto:writetoayushadi@gmail.com?subject=WorldBench%20Early%20Tester)
- [Website](https://worldbench.xyz)
- [Repository](https://github.com/tigee1311/worldbench)

Issue availability must be verified after merge; see the [launch checklist](docs/LAUNCH_CHECKLIST.md).

## Documentation

- [CLI](docs/CLI.md)
- [Data format](docs/DATA_FORMAT.md)
- [Python API](docs/PYTHON_API.md)
- [LeRobot import](docs/LEROBOT.md)
- [CI integration](docs/CI_INTEGRATION.md)
- [Metric validation](docs/METRIC_VALIDATION.md)
- [Case studies](docs/CASE_STUDIES.md)
- [Roadmap](docs/ROADMAP.md)
- [Migration from 0.3](docs/MIGRATION_V0_4.md)
- [Changelog](CHANGELOG.md)

WorldBench is Apache-2.0 licensed.
