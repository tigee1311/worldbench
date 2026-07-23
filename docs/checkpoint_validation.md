# Real Checkpoint Validation

Question:

```text
When I train a new world-model checkpoint, did it actually improve?
```

WorldBench answered this by comparing saved predictions from two real NanoWM checkpoints from the same model family on the same RT-1 / Fractal episodes.

## Comparison

| Field | Value |
| --- | --- |
| Model family | NanoWM-B/2 |
| Dataset | RT-1 / Fractal via LeRobot |
| Baseline checkpoint | `knightnemo/nanowm-b2-rt1-abl-pred-v-50k` |
| Candidate checkpoint | `knightnemo/nanowm-b2-rt1-300k` |
| Baseline revision | `82b169ab3c26d585efdeb88df782fa4a70db7486` |
| Candidate revision | `e073162d1ef2a34029cfe4f4662abbb7d18895e0` |
| Episodes | 0 through 9 |
| Episode selection | Fixed consecutive episode IDs chosen before inference |
| WorldBench version | `0.3.0.dev0` |
| WorldBench commit | `75f2f7b0549653c955671dc695fcdaec5e742377` |

The comparison is valid as a regression test because both checkpoints use the same NanoWM-B/2 family, the same fixed episodes, the same preprocessing, the same context, and a compatible RT-1 / Fractal setup. The intended experimental difference is checkpoint training stage.

## Controls

| Setting | Value |
| --- | ---: |
| Episodes | 10 |
| Context frames exported | 4 |
| Future frames evaluated | 8 |
| Rollout video length | 12 frames |
| Resolution | 256x256 RGB |
| FPS | 3 |
| Sampling steps | 50 |
| Batch size | 1 |
| Samples per episode | 1 |
| Precision | FP16 |
| Seeds | `2026070900` through `2026070909` |

NanoWM-B/2 uses a 4-frame model inference window with `n_context_frames=1` internally. The exported WorldBench videos still contain 4 context frames followed by 8 evaluated future frames.

## Compute

Inference ran on a Kaggle Tesla T4 GPU with PyTorch `2.7.1+cu126` and Python `3.12.13`.

Downloaded/cached data was limited to the required validation slice and model assets:

| Cache | Size | Files |
| --- | ---: | ---: |
| RT-1 / Fractal episode data | 10,801,527 bytes | 51 |
| Hugging Face cache, including VAE assets | 669,914,683 bytes | 31 |
| Baseline checkpoint weights | 634,407,072 bytes | 1 |
| Candidate checkpoint weights | 634,407,072 bytes | 1 |

Raw videos, dataset shards, model checkpoints, and frame data are not committed.

## Results

| Score | Baseline 50k | Candidate 300k | Change |
| --- | ---: | ---: | ---: |
| Composite Score mean | 85.67 | 87.28 | +1.61 |
| Visual Similarity mean | 77.57 | 79.76 | +2.19 |
| Temporal Stability mean | 95.79 | 96.69 | +0.89 |

Unavailable metrics stayed unavailable and were not averaged as zero:

| Metric | Status |
| --- | --- |
| Action Consistency | N/A: no actions aligned to predicted video frames |
| Object Permanence | N/A: reliable object tracking unavailable |
| Contact Realism | N/A: reliable robot/object tracking unavailable |

## Per-Horizon Results

| Horizon | Metric | Baseline | Candidate | Change |
| --- | --- | ---: | ---: | ---: |
| t+1 | Visual Similarity | 81.20 | 83.36 | +2.15 |
| t+2 | Visual Similarity | 80.66 | 82.61 | +1.94 |
| t+3 | Visual Similarity | 79.91 | 81.99 | +2.08 |
| t+4 | Visual Similarity | 79.34 | 81.40 | +2.07 |
| t+5 | Visual Similarity | 78.89 | 80.99 | +2.10 |
| t+6 | Visual Similarity | 78.40 | 80.53 | +2.13 |
| t+7 | Visual Similarity | 77.96 | 80.13 | +2.17 |
| t+8 | Visual Similarity | 77.57 | 79.76 | +2.19 |
| t+2 | Temporal Stability | 98.91 | 99.64 | +0.73 |
| t+3 | Temporal Stability | 97.50 | 98.66 | +1.16 |
| t+4 | Temporal Stability | 96.51 | 97.89 | +1.39 |
| t+5 | Temporal Stability | 96.68 | 97.91 | +1.22 |
| t+6 | Temporal Stability | 96.43 | 97.54 | +1.11 |
| t+7 | Temporal Stability | 95.87 | 96.88 | +1.01 |
| t+8 | Temporal Stability | 95.79 | 96.69 | +0.89 |

WorldBench did not detect a long-horizon aggregate regression in this 10-episode validation slice. Candidate scores improved at every supported aggregate horizon.

## Episode Comparison

| Episode outcome | Count |
| --- | ---: |
| Improved | 9 |
| Regressed | 1 |
| Unchanged | 0 |

Worst regressions:

| Episode | Baseline | Candidate | Change |
| --- | ---: | ---: | ---: |
| `episode_002.mp4` | 87.26 | 86.93 | -0.33 |

Best improvements:

| Episode | Baseline | Candidate | Change |
| --- | ---: | ---: | ---: |
| `episode_008.mp4` | 78.74 | 84.96 | +6.22 |
| `episode_007.mp4` | 85.90 | 87.99 | +2.09 |
| `episode_001.mp4` | 86.23 | 88.25 | +2.02 |

## Gate Results

| Gate | Thresholds | Result |
| --- | --- | --- |
| Strict | no overall, metric, or horizon drop beyond 0.01 tolerance | PASS |
| Engineering | `--max-overall-drop 2 --max-metric-drop 5 --max-horizon-drop 5` | PASS |

The episode-level regression in `episode_002.mp4` was small enough that it did not correspond to an aggregate metric or horizon regression under either configured gate.

## What WorldBench Discovered

On this fixed 10-episode RT-1 / Fractal validation slice, the NanoWM 300k checkpoint improved over the 50k checkpoint overall, improved both supported aggregate metrics, improved every supported aggregate horizon, and improved 9 of 10 episodes. WorldBench also surfaced the one episode-level regression instead of hiding it in the aggregate.

This is evidence that the candidate checkpoint improved on this controlled validation slice. It is not a claim that the candidate is universally better.

## Artifacts

Compact committed artifacts:

- [baseline_batch_result.json](../artifacts/checkpoint_validation/baseline_batch_result.json)
- [candidate_batch_result.json](../artifacts/checkpoint_validation/candidate_batch_result.json)
- [strict_gate_result.json](../artifacts/checkpoint_validation/strict_gate_result.json)
- [engineering_gate_result.json](../artifacts/checkpoint_validation/engineering_gate_result.json)
- [comparison_summary.json](../artifacts/checkpoint_validation/comparison_summary.json)
- [provenance.json](../artifacts/checkpoint_validation/provenance.json)

## Limitations

- Ten episodes are useful for an engineering proof, not a public cross-model ranking.
- Only one sample was generated per checkpoint per episode.
- The evaluation uses the supported video-pair metrics available today: Visual Similarity and Temporal Stability.
- Action Consistency, Object Permanence, and Contact Realism were N/A because the committed video-pair evaluation artifacts do not contain the required action alignment or reliable tracking semantics.
- Fixed seeds were used where supported, but CUDA and model internals may still have nondeterministic behavior.
- This comparison does not prove general superiority across all RT-1 tasks, datasets, seeds, or model families.
