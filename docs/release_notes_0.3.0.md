# WorldBench v0.3.0 - Checkpoint regression testing

WorldBench v0.3.0 turns video-based robotics world-model evaluation into checkpoint regression testing.

Teams can now evaluate identical episode suites for baseline and candidate checkpoints, compare aggregate and per-horizon behavior, inspect episode-level regressions, and fail CI when configured thresholds are exceeded.

## Highlights

- Direct video-pair evaluation with `worldbench eval-video`
- Multi-episode checkpoint evaluation with `worldbench eval-batch`
- Per-horizon evaluation curves
- Baseline-vs-candidate regression gates with `worldbench gate`
- Episode-level improvement and regression analysis
- CI-compatible PASS / FAIL exit codes
- Compact checkpoint-regression artifacts and provenance

## Real Validation

- Model family: NanoWM-B/2
- Baseline: `knightnemo/nanowm-b2-rt1-abl-pred-v-50k`
- Candidate: `knightnemo/nanowm-b2-rt1-300k`
- Dataset: RT-1 / Fractal
- Episodes: 10 fixed episodes, IDs 0 through 9
- Overall: 85.67 -> 87.28
- Change: +1.61
- Visual Similarity: +2.19
- Temporal Stability: +0.89
- Episodes: 9 improved, 1 small regression, 0 unchanged
- Strict gate: PASS
- Engineering gate: PASS

Visual similarity improved at every evaluated horizon from t+1 through t+8. Temporal stability improved at every measurable horizon from t+2 through t+8. WorldBench still detected one small episode-level regression.

This validation is a fixed 10-episode proof, not a public cross-model ranking or a claim of universal model quality.
