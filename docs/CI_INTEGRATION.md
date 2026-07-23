# CI Integration

Commit an approved baseline batch artifact at `artifacts/worldbench/approved-baseline.json` or retrieve an immutable version from your artifact store. Do not regenerate the baseline during each candidate run. Update it only after a candidate passes, rollout changes are reviewed, and the team explicitly approves the new checkpoint.

The CI workflow is for saved video-based world-model predictions on a team's own fixed episode suite. It answers whether the candidate checkpoint regressed relative to the approved baseline; it is not a general robot-policy or task-success benchmark.

The complete example is [examples/github-actions/worldbench-gate.yml](../examples/github-actions/worldbench-gate.yml). It expects:

- `eval_suite/`: fixed ground-truth robot episode videos
- `candidate_predictions/`: candidate videos with identical relative paths
- `worldbench.yml`: reviewed metric and gate policy
- an approved baseline batch JSON

The model-specific inference step is intentionally a placeholder because WorldBench evaluates saved predictions and does not run arbitrary models.

The workflow installs WorldBench, obtains the approved baseline, runs your prediction generation, evaluates the candidate, gates it, and uploads batch JSON, Markdown, gate JSON, and gate Markdown even when the gate fails. The sample retains artifacts for 30 days; adjust this to your audit requirements.

Exit codes:

- `0`: evaluation completed or gate passed
- `1`: gate completed and failed policy
- `2`: invalid CLI input or incomparable episode suite

Before pushing, run the same commands locally:

```bash
worldbench eval-batch --ground-truth eval_suite --predictions candidate_predictions \
  --name candidate --output candidate.json --config worldbench.yml
worldbench gate --baseline artifacts/worldbench/approved-baseline.json \
  --candidate candidate.json --config worldbench.yml
```

When promoting a baseline, retain the candidate JSON exactly as evaluated, review the configuration hash and dataset identifier, copy it to the approved baseline location in a dedicated change, and require code review. Never compare runs created from different episodes or weaker metric coverage merely to obtain a pass.
