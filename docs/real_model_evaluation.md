# Real Model Evaluation

This document records the first compact WorldBench real-model artifact.

## Scope

This is a single-rollout integration proof. It is not a standardized leaderboard result and it is not a claim that NanoWM is 92.4% accurate.

Compact result artifact:

- [../artifacts/real_model_eval/nanowm_rt1_episode0.json](../artifacts/real_model_eval/nanowm_rt1_episode0.json)

## Model And Data

| Field | Value |
| --- | --- |
| Model | NanoWM-B/2 on RT-1 |
| Checkpoint | `knightnemo/nanowm-b2-rt1-300k` |
| Model card | https://huggingface.co/knightnemo/nanowm-b2-rt1-300k |
| NanoWM collection | https://huggingface.co/collections/knightnemo/nano-world-model |
| Dataset | RT-1 / Fractal |
| Dataset reference on model card | `lerobot/fractal20220817_data` |
| RT-1 paper | https://arxiv.org/abs/2212.06817 |
| Rollout count | 1 |
| Episode | 0 |
| Context frames | 4, inferred from temporary evaluation dataset metadata: "Future-only evaluation of NanoWM frames 4 through 11." |
| Generated future frames | 8 |
| FPS | 3 |
| Resolution | 256x256 RGB |
| Evaluation timestamp | 2026-07-09T01:01:02.726668+00:00 |
| WorldBench version used for artifact | 0.1.0 |

The artifact was generated before the repository metadata was bumped to 0.2.0.

## Evaluation Command

The compact artifact was produced from temporary scoring inputs:

```bash
worldbench eval <temporary-rt1-episode0-worldbench-dataset> \
  --predictions <temporary-nanowm-prediction-frames>
```

The local temporary dataset and prediction folders are not committed. The repository keeps only the compact JSON result artifact.

## Score Breakdown

| Metric | Status | Score | Reason |
| --- | --- | ---: | --- |
| Visual Similarity | available | 89.2 | 8 aligned frame pairs were scored. |
| Temporal Stability | available | 96.3 | Generated frames had stable frame-to-frame deltas. |
| Action Consistency | N/A | N/A | Unsupported raw numeric action vectors require an action adapter. |
| Object Permanence | N/A | N/A | Reliable object tracking is unavailable for this rollout. |
| Contact Realism | N/A | N/A | Reliable robot and object tracking are unavailable for this rollout. |

Overall:

```text
Visual Similarity: 89.24097498284189, weight 0.25
Temporal Stability: 96.32682361785054, weight 0.20
Available weight: 0.45
Overall: 92.39024104284573
```

Rounded display:

```text
Overall: 92.4
Visual Similarity: 89.2
Temporal Stability: 96.3
Action Consistency: N/A
Object Permanence: N/A
Contact Realism: N/A
```

## Metric Availability

WorldBench excluded unsupported metrics from the overall denominator. It did not assign a fake zero or a synthetic proxy score to action consistency, object permanence, or contact realism.

This behavior matters for real robot data:

- 7D numeric action vectors do not define screen-space motion without an action adapter.
- Object permanence cannot be scored reliably without object tracking.
- Contact realism cannot be scored reliably without robot and object tracking.

## Limitations

- One rollout only.
- Eight generated future frames only.
- The context length is inferred from local metadata, not from a committed model inference script.
- The temporary image dataset and prediction frames are intentionally not committed.
- The result should be treated as an integration proof, not a benchmark.

## External Credit

NanoWM, the Nano-World-Model collection, the RT-1 data, and the RT-1 paper are external projects. WorldBench only evaluates the saved generated frames and does not claim ownership of those models or datasets.
