from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image, ImageStat

from worldbench.backends.lerobot import import_lerobot_repo
from worldbench.dataset import validate_dataset


@pytest.mark.integration
def test_public_yaskawa_video_timeline_imports_episode_zero(tmp_path: Path) -> None:
    output_path = tmp_path / "yaskawa_video"

    report = import_lerobot_repo(
        "chocolat-nya/yaskawa-untangle-dataset",
        output_path,
        episodes=[0],
        camera_key="observation.images.fixed_cam1",
        timeline="video",
    )

    assert report.is_valid
    assert validate_dataset(output_path).is_valid

    episode_dir = output_path / "episode_000000"
    frames = sorted((episode_dir / "frames").glob("*.png"))
    assert len(frames) == 900
    assert frames[0].name == "000000.png"
    assert frames[-1].name == f"{len(frames) - 1:06d}.png"

    for frame_path in [frames[0], frames[len(frames) // 2], frames[-1]]:
        with Image.open(frame_path) as image:
            assert image.size == (640, 480)
            assert sum(ImageStat.Stat(image.convert("L")).var) > 0

    actions = json.loads((episode_dir / "actions.json").read_text())
    states = json.loads((episode_dir / "states.json").read_text())
    metadata = json.loads((episode_dir / "metadata.json").read_text())

    assert len(actions) == len(frames)
    assert len(states) == len(frames)
    assert metadata["timeline"] == "video"
    assert metadata["source_control_steps"] == 4952
    assert metadata["source_unique_video_frames"] == 900
    assert metadata["exported_timesteps"] == 900
    assert len({action["source_video_frame_index"] for action in actions}) == len(actions)
    assert isinstance(actions[0]["action"], list)
    assert len(actions[0]["action"]) == 7
    assert "observation_state" in states[0]
    assert len(states[0]["observation_state"]) == 7
    assert metadata["source"] == "lerobot"
    assert metadata["repo_id"] == "chocolat-nya/yaskawa-untangle-dataset"
    assert metadata["episode_index"] == 0
    assert metadata["camera_key"] == "observation.images.fixed_cam1"
    assert metadata["fps"] == 30


@pytest.mark.integration
def test_public_yaskawa_control_timeline_preserves_control_rows(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "yaskawa_control"

    report = import_lerobot_repo(
        "chocolat-nya/yaskawa-untangle-dataset",
        output_path,
        episodes=[0],
        camera_key="observation.images.fixed_cam1",
        timeline="control",
    )

    assert report.is_valid
    assert validate_dataset(output_path).is_valid

    episode_dir = output_path / "episode_000000"
    frames = sorted((episode_dir / "frames").glob("*.png"))
    actions = json.loads((episode_dir / "actions.json").read_text())
    states = json.loads((episode_dir / "states.json").read_text())
    metadata = json.loads((episode_dir / "metadata.json").read_text())

    assert len(frames) == len(actions) == len(states) == 4952
    assert metadata["timeline"] == "control"
    assert metadata["source_control_steps"] == 4952
    assert metadata["exported_timesteps"] == 4952
    frame_ids = [action["source_video_frame_index"] for action in actions]
    assert len(set(frame_ids)) < len(frame_ids)
    assert len(actions[0]["action"]) == 7
    assert len(states[0]["observation_state"]) == 7
