# WorldBench Evaluation Report: bad_model

**Composite Score:** 42/100

**Main failure:** visually plausible but action-inconsistent.

The rollout looks like a believable robot scene at a glance, but the predicted future does not follow the logged action sequence or contact dynamics closely enough to be useful for planning.

## Metric Scores

| Metric | Score |
| --- | ---: |
| Visual similarity | 64/100 |
| Action consistency | 31/100 |
| Contact realism | 20/100 |
| Object permanence | 55/100 |
| Temporal stability | 48/100 |

## Evidence

- `move_right` actions did not produce rightward motion.
- The object moved before robot/object contact.
- The object disappeared briefly during the rollout.
- Temporal flicker was detected between adjacent predicted frames.

## Suggested Fixes

- Strengthen action conditioning during world-model training.
- Add contact-rich training data with pre-contact and post-contact phases.
- Add temporal consistency losses to reduce flicker.
- Evaluate held-out interaction rollouts before using generated futures for planning.

## Notes

This development-only sample report is based on a deterministic synthetic fixture.
