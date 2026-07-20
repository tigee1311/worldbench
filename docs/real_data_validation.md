# Real Data Validation

This document records the LeRobot importer behavior verified by repository code and tests.

## Dataset Used

The network integration tests use:

- Repo id: `chocolat-nya/yaskawa-untangle-dataset`
- Episode: `0`
- Camera: `observation.images.fixed_cam1`
- Timeline modes tested: `video` and `control`

The tests are marked `integration` and are excluded from the default `pytest` command. They were not rerun during this documentation update.

Evidence: [../tests/test_lerobot_integration.py](../tests/test_lerobot_integration.py)

## Importer Behavior

Native import is implemented by `import_lerobot_repo` in [../worldbench/backends/lerobot.py](../worldbench/backends/lerobot.py). The public CLI is:

```bash
worldbench import-lerobot --repo-id chocolat-nya/yaskawa-untangle-dataset --episodes 0:1 --camera observation.images.fixed_cam1 --timeline video --out examples/yaskawa_video
worldbench import-lerobot --repo-id chocolat-nya/yaskawa-untangle-dataset --episodes 0:1 --camera observation.images.fixed_cam1 --timeline control --out examples/yaskawa_control
```

`--timeline` accepts `video` or `control`.

## Timeline Semantics

### Video Timeline

`--timeline video` exports one WorldBench timestep per unique source camera frame.

Verified behavior:

- action alignment strategy: `latest_at_or_before_timestamp`
- state alignment strategy: `nearest_timestamp`
- output frames are selected camera frames at the video timestamp
- action and state records preserve source control and source video provenance when available

Recorded Yaskawa integration-test values:

| Check | Value |
| --- | ---: |
| Exported frames | 900 |
| Action rows | 900 |
| State rows | 900 |
| Source control rows | 4,952 |
| Unique source video frames | 900 |
| Action dimensionality | 7D |
| State dimensionality | 7D |
| Source video | 640x480 RGB |
| FPS | 30 |

### Control Timeline

`--timeline control` exports one WorldBench timestep per source control row.

Verified behavior:

- action alignment strategy: `source_control_row`
- state alignment strategy: `source_control_row`
- camera frames can repeat because the control timeline can be denser than the video timeline
- provenance records the source control row and nearest/referenced video frame when available

Recorded Yaskawa integration-test values:

| Check | Value |
| --- | ---: |
| Exported frames | 4,952 |
| Action rows | 4,952 |
| State rows | 4,952 |
| Source control rows | 4,952 |
| Action dimensionality | 7D |
| State dimensionality | 7D |

## Provenance Fields

LeRobot imports write metadata fields including:

- `source`
- `repo_id`
- `episode_index`
- `camera_key`
- `timeline`
- `video_fps`
- `alignment_strategy`
- `source_control_steps`
- `source_unique_video_frames`
- `source_referenced_video_frames`
- `exported_timesteps`

Actions and states can include:

- `source_control_index`
- `source_control_timestamp`
- `source_video_frame_index`
- `source_video_timestamp`

## Verification Boundaries

Verified from repository code and offline tests:

- native LeRobot import path and CLI options
- video and control timeline modes
- action and state alignment strategy names
- source provenance fields
- fake-dataset unit tests for vector preservation, frame deduplication, and repeated-frame control timelines

Recorded from network integration tests:

- 900-frame Yaskawa video timeline
- 4,952-row Yaskawa control timeline
- 7D action vectors and 7D observation states
- 640x480 RGB video frames

Not verified during this task:

- a fresh download of the Yaskawa dataset
- current upstream Hugging Face dataset availability
- new LeRobot package behavior beyond the committed tests
