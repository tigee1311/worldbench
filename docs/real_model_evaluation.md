# Real Model Evaluation

This document records the committed single-rollout NanoWM integration artifact.

Artifact: [../artifacts/real_model_eval/nanowm_rt1_episode0.json](../artifacts/real_model_eval/nanowm_rt1_episode0.json)

## Scope

This is a single-rollout integration proof, not a standardized leaderboard result and not a claim that NanoWM is 92.4% accurate.

| Field | Verified value |
| --- | --- |
| Model/checkpoint | `knightnemo/nanowm-b2-rt1-300k` |
| README label | NanoWM B2 RT-1 300K |
| Dataset | RT-1 / Fractal |
| Episode | 0 |
| Rollout count | 1 |
| Context frames | 4 |
| Evaluated generated frames | 8 |
| Resolution | 256x256 RGB |
| FPS | 3 |
| Artifact timestamp | 2026-07-09T01:01:02.726668+00:00 |
| WorldBench version recorded in artifact | 0.1.0 |

The artifact records `dataset_path` as `temporary RT-1 episode 0 evaluation dataset; not committed` and `predictions_path` as `temporary NanoWM prediction frames; not committed`. The exact command cannot be rerun from committed inputs because the temporary dataset and prediction frames are not in the repository.

## Results

| Metric | Status | Exact value | Rounded display | Reason |
| --- | --- | ---: | ---: | --- |
| Overall | available | 92.39024104284573 | 92.4 | weighted over available metrics |
| Visual Similarity | available | 89.24097498284189 | 89.2 | 8 aligned frame pairs |
| Temporal Stability | available | 96.32682361785054 | 96.3 | no jump indices recorded |
| Action Consistency | unsupported | N/A | N/A | unsupported raw numeric action vectors require an action adapter. |
| Object Permanence | unsupported | N/A | N/A | Reliable object tracking is unavailable for this rollout. |
| Contact Realism | unsupported | N/A | N/A | Reliable robot and object tracking are unavailable for this rollout. |

The available metric weights were Visual Similarity `0.25` and Temporal Stability `0.20`, for an available denominator of `0.45`:

```text
(89.24097498284189 * 0.25 + 96.32682361785054 * 0.20) / 0.45 = 92.39024104284573
```

## N/A Explanations

Action Consistency was not scored because the rollout contained raw numeric action vectors and no action adapter that maps those values to expected image-space motion.

Object Permanence was not scored because reliable object tracking is unavailable for this rollout.

Contact Realism was not scored because reliable robot and object tracking are unavailable for this rollout.

## Limitations

- One rollout only.
- Eight evaluated generated future frames only.
- The temporary image dataset and prediction frames are not committed.
- The command used to create the artifact cannot be reconstructed as a runnable repository command from committed files.
- The result should be treated as an integration proof, not a benchmark, leaderboard entry, or accuracy claim.
