# WorldBench v0.4.1 Compatibility Fixtures

These fixtures were generated from the published `worldbench[video]==0.4.1`
package in a clean Python 3.11 virtual environment under
`/Users/ayush/worldbench-review/v041-fixture-env-py311`.

Commands used:

```bash
/opt/homebrew/bin/python3.11 -m venv /Users/ayush/worldbench-review/v041-fixture-env-py311
/Users/ayush/worldbench-review/v041-fixture-env-py311/bin/python -m pip install --upgrade pip
/Users/ayush/worldbench-review/v041-fixture-env-py311/bin/pip install "worldbench[video]==0.4.1"
/Users/ayush/worldbench-review/v041-fixture-env-py311/bin/worldbench eval-videos --demo --output tests/fixtures/v0_4_1/saved_video --no-save-comparison
/Users/ayush/worldbench-review/v041-fixture-env-py311/bin/worldbench eval-batch --ground-truth tests/fixtures/v0_4_1/batch/ground_truth --predictions tests/fixtures/v0_4_1/batch/baseline_predictions --name baseline_v041 --output tests/fixtures/v0_4_1/batch/baseline_batch_result.json --output-root /Users/ayush/worldbench-review/v041-batch-artifacts
/Users/ayush/worldbench-review/v041-fixture-env-py311/bin/worldbench eval-batch --ground-truth tests/fixtures/v0_4_1/batch/ground_truth --predictions tests/fixtures/v0_4_1/batch/candidate_predictions --name candidate_v041 --output tests/fixtures/v0_4_1/batch/candidate_batch_result.json --output-root /Users/ayush/worldbench-review/v041-batch-artifacts
/Users/ayush/worldbench-review/v041-fixture-env-py311/bin/worldbench gate --baseline tests/fixtures/v0_4_1/batch/baseline_batch_result.json --candidate tests/fixtures/v0_4_1/batch/candidate_batch_result.json --output-root tests/fixtures/v0_4_1/gate
```

Fixture purpose:

- `saved_video/result.json` and `saved_video/summary.md`: single saved-video
  evaluation report.
- `batch/baseline_batch_result.json` and `batch/candidate_batch_result.json`:
  one-episode checkpoint batch results.
- `gate/latest/gate.json`: v0.4.1 default gate result for the batch pair.
- `worldbench.yml` and `gate_config.yml`: release-compatible configuration
  files used to assert config and gate schema compatibility.
- `nanowm_rt1_episode0.json`: small existing NanoWM result sample copied from
  repository artifacts.

Expected compatibility behavior:

- v0.4.1 JSON reports must load without requiring newer provenance or
  bootstrap fields.
- Missing new fields must be treated as absent evidence, not invented values.
- Existing gate semantics must remain unchanged unless confidence-aware gates
  are explicitly enabled.
- Old CLI aliases such as `--reference` must continue to work.
