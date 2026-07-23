# WorldBench 0.4.1 Release Notes

## Highlights

WorldBench 0.4.1 adds a beginner-friendly saved-video evaluation workflow for users who have one ground-truth future video and one matching predicted future video.

```bash
worldbench eval-videos \
  --ground-truth ground_truth.mp4 \
  --prediction predicted_future.mp4 \
  --output results/
```

This command evaluates a saved predicted robot future against its matching ground-truth future. It does not perform checkpoint regression by itself. Checkpoint regression still requires evaluating baseline and candidate predictions against the same ground-truth suite with `eval-batch`, then comparing the batch artifacts with `gate`.

## Added

- `worldbench eval-videos` for one saved ground-truth/prediction video pair.
- Preferred `--ground-truth` input with backward-compatible `--reference` alias.
- `worldbench eval-videos --demo --output results/demo` for a tiny deterministic synthetic smoke test.
- JSON and Markdown reports for saved-video evaluations.
- Saved `artifacts/comparison.png` with `Ground truth` and `Prediction` labels.
- Frame-count alignment that records original frame counts, evaluated frame count, and frames trimmed from each input.
- Prediction resizing to the ground-truth resolution with explicit warnings and provenance.
- FPS mismatch warnings when evaluation uses frame-index alignment rather than time resampling.
- A fresh Colab notebook for uploaded MP4 files.

## Clarified

- The two-video command evaluates one prediction against matching ground truth.
- The two-video command is not a complete checkpoint-regression workflow.
- Video-only evaluation normally supports Visual Similarity and Temporal Stability.
- Action Consistency, Object Permanence, and Contact Realism return N/A unless the required action semantics or tracking signals are available.
- Demo results are synthetic demonstration data, not model-quality evidence and not benchmark evidence.

## Installation

After the trusted PyPI publishing workflow completes:

```bash
python -m pip install "worldbench[video]==0.4.1"
```

## Limitations

- WorldBench evaluates saved visual futures; it does not run model inference or closed-loop robot control.
- `eval-videos` does not measure robot task success.
- The command does not infer action semantics from video alone.
- Composite Scores summarize available metrics for a specific aligned pair; they are not accuracy.
- Cross-checkpoint regression should use the existing batch and gate workflow on the same ground-truth suite.
