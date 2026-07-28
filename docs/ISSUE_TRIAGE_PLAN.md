# Issue Triage Plan

Read-only review date: 2026-07-27.

No GitHub issues were opened, closed, edited, or commented on during this hardening pass.

| Issue | Current title | Recommendation | Reason | Proposed next action |
| --- | --- | --- | --- | --- |
| [#1](https://github.com/tigee1311/worldbench/issues/1) | Roadmap: ManiSkill and RLBench adapters | rewrite | Adapters may fit WorldBench only if they export saved visual futures aligned to fixed episodes. The current title sounds like broad simulator support. | Rewrite as "Adapters for saved visual-future exports from ManiSkill/RLBench-style datasets" and require example inputs before implementation. |
| [#3](https://github.com/tigee1311/worldbench/issues/3) | Roadmap: ROS bag import | defer | Generic ROS support broadens WorldBench toward robotics data infrastructure. It may be useful only if a concrete user needs bag-to-RGB-future extraction. | Defer until an external user provides a saved-video regression workflow blocked by ROS bag conversion. |
| [#4](https://github.com/tigee1311/worldbench/issues/4) | Roadmap: Benchmark leaderboard | close or rewrite | A leaderboard conflicts with the current positioning unless restricted to a single documented protocol. WorldBench is not validated as a public cross-model ranking. | Prefer close. If kept, rewrite as "Documented comparison bundle format for one fixed protocol" and require external validation first. |
| [#6](https://github.com/tigee1311/worldbench/issues/6) | Roadmap: Cloud run sharing | defer | Cloud sharing is not required for the core regression workflow and introduces privacy/security responsibilities. | Defer until repeated external pilots show teams need hosted sharing rather than local artifacts. |

## Triage Rules Going Forward

- Keep issues tied to saved visual-future regression testing.
- Require evidence before metric formula, metric weight, or scientific-claim changes.
- Label research-only work separately from production features.
- Close or rewrite issues that imply real-robot execution, universal benchmarking, or task-success claims.
- Do not ask users to post private videos, credentials, or model artifacts in public issues.
