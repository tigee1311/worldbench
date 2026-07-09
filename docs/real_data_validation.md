# Real Data Validation

WorldBench has been validated against a public LeRobot Yaskawa cable-untangling dataset.

Dataset:

- Hugging Face: https://huggingface.co/datasets/chocolat-nya/yaskawa-untangle-dataset
- Repo id: `chocolat-nya/yaskawa-untangle-dataset`
- Camera used in validation: `observation.images.fixed_cam1`
- Episode used in validation: `0`

The dataset card describes a Yaskawa 7-axis manipulator, 7-DOF state, 7D target-joint actions, 30 FPS video, and 640x480 images.

## Commands

Video timeline:

```bash
worldbench import-lerobot \
  --repo-id chocolat-nya/yaskawa-untangle-dataset \
  --episodes 0:1 \
  --camera observation.images.fixed_cam1 \
  --timeline video \
  --out examples/yaskawa_video
```

Control timeline:

```bash
worldbench import-lerobot \
  --repo-id chocolat-nya/yaskawa-untangle-dataset \
  --episodes 0:1 \
  --camera observation.images.fixed_cam1 \
  --timeline control \
  --out examples/yaskawa_control
```

## Validated Results

| Check | Video timeline | Control timeline |
| --- | ---: | ---: |
| Exported frames | 900 | 4,952 |
| Action rows | 900 | 4,952 |
| State rows | 900 | 4,952 |
| Action dimensionality | 7D | 7D |
| State dimensionality | 7D | 7D |
| Source video | 640x480 RGB | 640x480 RGB |
| Source control rows | 4,952 | 4,952 |

## Timeline Semantics

### Video Timeline

`--timeline video` exports one WorldBench timestep per unique source camera frame.

For each video frame:

- the output frame is the selected camera image at that video timestamp
- the action is aligned with the latest source control row at or before the video timestamp
- the state is aligned with the nearest source control timestamp
- provenance records the source control index/timestamp and source video frame index/timestamp

In the validated Yaskawa import:

- 900 unique video frames were exported
- 4,952 source control rows were used for alignment
- each exported WorldBench timestep references one source video frame

### Control Timeline

`--timeline control` exports one WorldBench timestep per source control row.

For each control row:

- the action and state come from the same source control row
- the selected camera image is the source camera frame nearest to that control timestamp
- camera frames can repeat because control runs faster than video
- provenance records the source control index/timestamp and source video frame index/timestamp

In the validated Yaskawa import:

- 4,952 WorldBench timesteps were exported
- multiple control rows referenced the same source video frame

## Metadata

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

Actions and states include source provenance fields when available:

- `source_control_index`
- `source_control_timestamp`
- `source_video_frame_index`
- `source_video_timestamp`

## Test Policy

The public Yaskawa tests are marked `integration`. Normal CI runs offline tests only:

```bash
pytest
```

Integration tests can be run explicitly in an environment that has the optional LeRobot dependencies and network/data access:

```bash
pytest -m integration
```
