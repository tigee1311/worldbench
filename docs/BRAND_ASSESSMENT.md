# Brand Assessment

Research date: 2026-07-27.

No repository, package, CLI, import path, tag, or documentation brand was renamed during this task.

## Summary

`WorldBench` has high collision risk. The name is already used by multiple active AI benchmark projects, including an adjacent video/world-model physics benchmark and a multimodal visual-reasoning benchmark. The current project can continue using the name for now, but a rename should be considered before broader outreach, external pilots, or a larger release.

## Observed Collisions

| Source | Collision | Relevance | Severity |
| --- | --- | --- | --- |
| [world-bench.github.io](https://world-bench.github.io/) | `WorldBench: How Close are World Models to the Physical World?` | Adjacent video-based world-model benchmark with physics scenarios, dataset, paper, and leaderboard language. | High |
| [worldbench-vl.github.io](https://worldbench-vl.github.io/) | `WorldBench: A Challenging and Visually Diverse Multimodal Reasoning Benchmark` | Active multimodal reasoning benchmark with paper/code/dataset links. | High |
| [Hugging Face `worldbench`](https://huggingface.co/worldbench) | Organization/user namespace named `worldbench` with models, datasets, and Spaces. | Namespace collision on a major ML distribution platform. | High |
| [GitHub `worldbench`](https://github.com/worldbench) | GitHub organization named `worldbench`, including WorldLens and related benchmark repositories. | Repository-owner and social/search collision. | High |
| [PyPI `worldbench`](https://pypi.org/project/worldbench/) | Package name currently associated with this project. | No PyPI name conflict, but package page is not enough to disambiguate web search. | Low for package ownership, medium for discoverability |
| [PCWorld WorldBench](https://www.pcworld.com/article/535824/worldbench-2.html) | Historical PC benchmarking product. | Older non-robotics collision; still affects search history. | Low |
| [iWorld-Bench](https://iworld-bench.com/) | Similar name in interactive world-model benchmarking. | Not exact, but close enough to add search ambiguity. | Medium |

## Risks

### Searchability

High. Exact-name searches surface multiple unrelated `WorldBench` projects. The adjacent physics benchmark is especially likely to confuse researchers looking for world-model evaluation.

### Legal Or Trademark Uncertainty

Unknown. This assessment is not a trademark search or legal opinion. The presence of historical and current uses means a formal trademark review would be needed before investing heavily in the name.

### Package Migration Cost

Medium. The PyPI package and Python import are already `worldbench`. A rename would require:

- new package reservation
- transitional package or deprecation period
- CLI alias strategy
- import compatibility wrapper
- documentation migration
- release notes and user-facing warnings

### Repository Migration Cost

Medium. GitHub links, badges, PyPI project URLs, docs, artifacts, and issue references would need redirects or updates. Because external adoption is not yet established, migration cost is lower now than after wider pilots.

### User Disruption

Currently low to medium. There is a public release and tag history, but no claimed large user base. Disruption grows if more artifacts, external pilots, or integrations reference the current name.

## Naming Criteria

A better name should:

- preserve the same-episode checkpoint-regression focus
- avoid claiming a universal benchmark
- be searchable
- work as a Python package and CLI
- avoid direct collision with active papers, datasets, and organizations
- tolerate backward-compatible aliases during migration

## Possible Alternative Names

1. `RolloutDelta`
2. `HorizonGate`
3. `FutureDelta`
4. `CheckpointFutures`
5. `VideoRolloutCheck`

These names were not exhaustively cleared. Each would need package, repository, domain, social, and trademark review.

## Recommendation

Do not rename automatically in this hardening pass.

Before a v0.5 or v1.0 positioning push, run a formal naming decision. If the project stays `WorldBench`, consistently qualify it as "WorldBench checkpoint regression" or "WorldBench for saved robot-video checkpoint regression" to reduce confusion with broader benchmark projects. If a rename is chosen, do it with a compatibility plan before external pilots create more references to the current name.
