# External Submission Example

Use this folder as a minimal checklist for an external pilot. Do not put private data, credentials, model weights, or large videos in a public issue or repository commit.

Expected local layout:

```text
submission/
  manifest.json
  ground_truth/
    episode_000.mp4
  baseline_predictions/
    episode_000.mp4
  candidate_predictions/
    episode_000.mp4
```

Run locally:

```bash
worldbench eval-batch --ground-truth ground_truth --predictions baseline_predictions --name baseline --output baseline.json
worldbench eval-batch --ground-truth ground_truth --predictions candidate_predictions --name candidate --output candidate.json
worldbench gate --baseline baseline.json --candidate candidate.json --strict-config-match
```
