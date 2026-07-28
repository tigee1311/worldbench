# Human Evaluation Protocol

This protocol defines a blinded comparison between ground truth, baseline predictions, candidate predictions, WorldBench metric deltas, and human judgments. No human-evaluation data was collected during this hardening pass.

## Study Unit

One item is a single fixed episode with:

- Ground-truth future video.
- Baseline predicted future video.
- Candidate predicted future video.
- WorldBench episode delta and horizon deltas hidden from the rater during initial scoring.

## Blinding

- Randomize baseline/candidate side assignment.
- Hide checkpoint names and training steps.
- Show ground truth as reference.
- Ask raters to judge the two predictions before revealing WorldBench deltas.

## Rater Questions

Use a 1-5 ordinal scale plus free text:

- Visual quality relative to ground truth.
- Temporal correctness and absence of flicker.
- Action fidelity when actions are visible or documented.
- Object persistence and contact plausibility when visible.
- Task plausibility, with an explicit warning that this is not task-success measurement.

## Analysis

- Compare human preference with WorldBench composite delta.
- Compare human temporal judgments with Temporal Stability deltas.
- Compare object/contact judgments only when tracking-supporting evidence exists.
- Record disagreements and inspect whether WorldBench penalized plausible alternative futures unfairly.

## Limitations

- Human video preference is not real-robot task success.
- Small episode counts provide weak evidence.
- Raters may overweight visual similarity when multiple futures are plausible.
- Action fidelity cannot be judged without documented action semantics.
