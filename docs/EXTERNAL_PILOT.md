# External Pilot Protocol

This protocol is for teams that already produce saved robot-video predictions from baseline and candidate world-model checkpoints. It does not claim that WorldBench has external adoption.

## Qualified Pilot

A pilot qualifies when the external team can provide:

- A fixed set of robot episodes.
- Ground-truth future videos or frames for each episode.
- Baseline checkpoint predictions for the same episodes.
- Candidate checkpoint predictions for the same episodes.
- Stable episode identifiers and context-frame handling.
- Permission to evaluate the provided artifacts.

## Inputs Needed

- Episode list and pairing rule.
- Ground-truth files.
- Baseline prediction files.
- Candidate prediction files.
- Checkpoint identifiers.
- Frame rate, resolution, context length, and prediction horizon.
- Any available action schema documentation.
- Privacy and redistribution constraints.

Do not provide credentials or private download links in public issues.

## Privacy Handling

- Public data can be linked in an issue.
- Private data should be coordinated outside GitHub.
- Reports should use redacted paths by default.
- No private videos, model weights, or datasets should be committed to the repository.

## Output Delivered

- Baseline batch result JSON.
- Candidate batch result JSON.
- Gate result JSON and Markdown summary.
- Episode-level regressions and improvements.
- Metric coverage and unavailable-metric reasons.
- Provenance and `verify-run` result when local files remain available.

## Success Criteria

- The team can reproduce the run locally.
- The result answers whether the candidate regressed on fixed episodes.
- Regressed episodes and horizons are inspectable.
- The team can state whether the output would affect checkpoint acceptance.
- The team reports whether they would run WorldBench again.

## Follow-Up Questions

- Did the gate match your internal model-selection decision?
- Which unavailable metrics would have been useful?
- Were the worst-regression episodes useful for debugging?
- Were the JSON and Markdown artifacts sufficient?
- What blocked repeated use?
