from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
import importlib

import numpy as np
import pytest

from worldbench.backends import lerobot
from worldbench.backends.lerobot import (
    LeRobotImportError,
    import_lerobot_repo,
    inspect_lerobot_features,
    parse_episode_selection,
)
from worldbench.dataset import validate_dataset
from worldbench.utils import read_json


class FakeTensor:
    def __init__(self, value: Any) -> None:
        self.value = np.asarray(value)

    def detach(self) -> "FakeTensor":
        return self

    def cpu(self) -> "FakeTensor":
        return self

    def numpy(self) -> np.ndarray:
        return self.value


def fake_lerobot_dataset(
    rows: list[dict[str, Any]],
    features: dict[str, dict[str, Any]],
    total_episodes: int = 2,
    fps: int = 30,
    video_keys: list[str] | None = None,
    episode_metadata: list[dict[str, Any]] | None = None,
) -> type:
    class FakeLeRobotDataset:
        init_kwargs: dict[str, Any] = {}

        def __init__(self, repo_id: str, **kwargs: Any) -> None:
            self.repo_id = repo_id
            self.features = features
            self.fps = fps
            self.meta = SimpleNamespace(
                total_episodes=total_episodes,
                fps=fps,
                video_keys=video_keys or [],
                episodes=episode_metadata,
            )
            self.__class__.init_kwargs = kwargs
            requested = kwargs.get("episodes")
            if requested is None:
                self.rows = rows
            else:
                self.rows = [
                    row for row in rows if int(row["episode_index"]) in requested
                ]

        def __len__(self) -> int:
            return len(self.rows)

        def __getitem__(self, idx: int) -> dict[str, Any]:
            return self.rows[idx]

    return FakeLeRobotDataset


def sample_rows(camera_key: str = "observation.images.front") -> list[dict[str, Any]]:
    return [
        {
            "episode_index": 0,
            "timestamp": np.float64(0.0),
            "action": FakeTensor([0.12, -0.04, 0.31, 0.0, 1.0]),
            "observation.state": np.asarray([0.5, 0.2, -0.3], dtype=np.float32),
            camera_key: np.zeros((3, 6, 8), dtype=np.uint8),
            "task": "pick cube",
        },
        {
            "episode_index": 0,
            "timestamp": np.float64(1.0 / 30.0),
            "action": np.asarray([0.2, -0.01, 0.32, 0.0, 1.0], dtype=np.float64),
            "observation.state": FakeTensor([0.6, 0.2, -0.2]),
            camera_key: np.full((6, 8, 3), 255, dtype=np.uint8),
            "task": "pick cube",
        },
        {
            "episode_index": 1,
            "timestamp": np.float64(0.0),
            "action": np.asarray([0.9, 0.1], dtype=np.float32),
            "observation.state": np.asarray([1.0, 2.0], dtype=np.float32),
            camera_key: np.full((6, 8, 3), 120, dtype=np.uint8),
            "task": "place cube",
        },
    ]


def duplicate_frame_rows(
    camera_key: str = "observation.images.front",
) -> list[dict[str, Any]]:
    rows = []
    timestamps = [0.00, 0.01, 0.02, 0.03, 0.04, 0.05]
    for index, timestamp in enumerate(timestamps):
        frame_value = 40 if index < 3 else 180
        rows.append(
            {
                "index": index,
                "episode_index": 0,
                "timestamp": np.float64(timestamp),
                "action": np.asarray([index, index + 0.5], dtype=np.float32),
                "observation.state": np.asarray([index, -index], dtype=np.float32),
                camera_key: np.full((4, 6, 3), frame_value, dtype=np.uint8),
                "task": "dedupe frames",
            }
        )
    return rows


def skipped_video_frame_rows(
    camera_key: str = "observation.images.front",
) -> list[dict[str, Any]]:
    return [
        {
            "index": 0,
            "episode_index": 0,
            "timestamp": np.float64(0.0),
            "action": np.asarray([0.0], dtype=np.float32),
            "observation.state": np.asarray([0.0], dtype=np.float32),
            camera_key: np.full((4, 6, 3), 40, dtype=np.uint8),
        },
        {
            "index": 1,
            "episode_index": 0,
            "timestamp": np.float64(0.1),
            "action": np.asarray([1.0], dtype=np.float32),
            "observation.state": np.asarray([1.0], dtype=np.float32),
            camera_key: np.full((4, 6, 3), 180, dtype=np.uint8),
        },
    ]


def features(*camera_keys: str) -> dict[str, dict[str, Any]]:
    payload = {
        "episode_index": {},
        "timestamp": {},
        "action": {},
        "observation.state": {},
        "task": {},
    }
    for camera_key in camera_keys:
        payload[camera_key] = {}
    return payload


def test_parse_episode_selection_indices_and_ranges() -> None:
    assert parse_episode_selection(None) is None
    assert parse_episode_selection("0") == [0]
    assert parse_episode_selection("0:3,7,2") == [0, 1, 2, 7]


def test_parse_episode_selection_rejects_invalid_ranges() -> None:
    with pytest.raises(ValueError, match="STOP must be greater"):
        parse_episode_selection("3:1")
    with pytest.raises(ValueError, match="non-negative"):
        parse_episode_selection("-1")


def test_single_camera_auto_detection() -> None:
    dataset_cls = fake_lerobot_dataset(
        sample_rows(), features("observation.images.front")
    )
    dataset = dataset_cls("user/dataset")

    info = inspect_lerobot_features(dataset)

    assert info.selected_camera == "observation.images.front"
    assert info.action_key == "action"
    assert info.state_key == "observation.state"
    assert info.timestamp_key == "timestamp"
    assert info.episode_index_key == "episode_index"


def test_multiple_camera_requires_explicit_camera() -> None:
    dataset_cls = fake_lerobot_dataset(
        sample_rows(),
        features("observation.images.front", "observation.images.wrist"),
    )
    dataset = dataset_cls("user/dataset")

    with pytest.raises(LeRobotImportError, match="Multiple camera observations"):
        inspect_lerobot_features(dataset)


def test_invalid_camera_error_lists_available_cameras() -> None:
    dataset_cls = fake_lerobot_dataset(
        sample_rows(),
        features("observation.images.front", "observation.images.wrist"),
    )
    dataset = dataset_cls("user/dataset")

    with pytest.raises(LeRobotImportError, match="observation.images.front"):
        inspect_lerobot_features(dataset, camera_key="observation.images.side")


def test_import_lerobot_repo_exports_selected_episode_and_preserves_vectors(
    tmp_path: Path,
) -> None:
    dataset_cls = fake_lerobot_dataset(
        sample_rows(), features("observation.images.front")
    )
    output_path = tmp_path / "worldbench_lerobot"

    report = import_lerobot_repo(
        "user/dataset",
        output_path,
        episodes=[0],
        camera_key=None,
        dataset_cls=dataset_cls,
    )

    assert report.is_valid
    assert dataset_cls.init_kwargs["episodes"] == [0]
    assert dataset_cls.init_kwargs["return_uint8"] is True
    episode_dir = output_path / "episode_000000"
    assert (episode_dir / "frames" / "000000.png").exists()
    assert (episode_dir / "frames" / "000001.png").exists()
    assert validate_dataset(output_path).is_valid

    actions = read_json(episode_dir / "actions.json")
    states = read_json(episode_dir / "states.json")
    metadata = read_json(episode_dir / "metadata.json")

    assert actions[0]["t"] == 0
    assert actions[0]["timestamp"] == 0.0
    assert actions[0]["action"] == [0.12, -0.04, 0.31, 0.0, 1.0]
    assert actions[1]["action"] == [0.2, -0.01, 0.32, 0.0, 1.0]
    assert states[0]["observation_state"] == pytest.approx([0.5, 0.2, -0.3])
    assert states[1]["observation_state"] == [0.6, 0.2, -0.2]
    assert metadata["source"] == "lerobot"
    assert metadata["repo_id"] == "user/dataset"
    assert metadata["episode_index"] == 0
    assert metadata["camera_key"] == "observation.images.front"
    assert metadata["timeline"] == "video"
    assert metadata["fps"] == 30
    assert metadata["task"] == "pick cube"


def test_video_timeline_is_default_and_exports_unique_video_steps(
    tmp_path: Path,
) -> None:
    dataset_cls = fake_lerobot_dataset(
        duplicate_frame_rows(), features("observation.images.front"), fps=20
    )
    output_path = tmp_path / "video_timeline"

    report = import_lerobot_repo(
        "user/dataset",
        output_path,
        episodes=[0],
        camera_key="observation.images.front",
        dataset_cls=dataset_cls,
    )

    assert report.is_valid
    episode_dir = output_path / "episode_000000"
    frames = sorted((episode_dir / "frames").glob("*.png"))
    actions = read_json(episode_dir / "actions.json")
    states = read_json(episode_dir / "states.json")
    metadata = read_json(episode_dir / "metadata.json")

    assert [frame.name for frame in frames] == ["000000.png", "000001.png"]
    assert len(actions) == len(states) == 2
    assert [action["timestamp"] for action in actions] == [0.0, 0.05]
    assert [action["source_video_frame_index"] for action in actions] == [0, 1]
    assert actions[0]["source_control_index"] == 0
    assert actions[0]["action"] == pytest.approx([0.0, 0.5])
    assert actions[1]["source_control_index"] == 5
    assert actions[1]["action"] == pytest.approx([5.0, 5.5])
    assert states[0]["source_control_index"] == 0
    assert states[1]["source_control_index"] == 5
    assert states[1]["observation_state"] == pytest.approx([5.0, -5.0])
    assert metadata["timeline"] == "video"
    assert metadata["alignment_strategy"] == {
        "action": "latest_at_or_before_timestamp",
        "state": "nearest_timestamp",
    }
    assert metadata["source_control_steps"] == 6
    assert metadata["source_unique_video_frames"] == 2
    assert metadata["source_referenced_video_frames"] == 2
    assert metadata["exported_timesteps"] == 2


def test_control_timeline_preserves_control_rows_and_repeated_frames(
    tmp_path: Path,
) -> None:
    dataset_cls = fake_lerobot_dataset(
        duplicate_frame_rows(), features("observation.images.front"), fps=20
    )
    output_path = tmp_path / "control_timeline"

    report = import_lerobot_repo(
        "user/dataset",
        output_path,
        episodes=[0],
        camera_key="observation.images.front",
        timeline="control",
        dataset_cls=dataset_cls,
    )

    assert report.is_valid
    episode_dir = output_path / "episode_000000"
    frames = sorted((episode_dir / "frames").glob("*.png"))
    actions = read_json(episode_dir / "actions.json")
    states = read_json(episode_dir / "states.json")
    metadata = read_json(episode_dir / "metadata.json")

    assert len(frames) == len(actions) == len(states) == 6
    assert [action["source_video_frame_index"] for action in actions] == [
        0,
        0,
        0,
        1,
        1,
        1,
    ]
    assert actions[-1]["source_control_index"] == 5
    assert actions[-1]["action"] == pytest.approx([5.0, 5.5])
    assert states[-1]["observation_state"] == pytest.approx([5.0, -5.0])
    assert metadata["timeline"] == "control"
    assert metadata["alignment_strategy"] == {
        "action": "source_control_row",
        "state": "source_control_row",
    }
    assert metadata["source_control_steps"] == 6
    assert metadata["source_unique_video_frames"] == 2
    assert metadata["exported_timesteps"] == 6


def test_video_timeline_exports_metadata_frames_without_control_rows(
    tmp_path: Path,
) -> None:
    camera_key = "observation.images.front"
    dataset_cls = fake_lerobot_dataset(
        skipped_video_frame_rows(camera_key),
        features(camera_key),
        fps=20,
        video_keys=[camera_key],
        episode_metadata=[
            {
                f"videos/{camera_key}/from_timestamp": 0.0,
                f"videos/{camera_key}/to_timestamp": 0.1,
            }
        ],
    )
    output_path = tmp_path / "video_with_skipped_control_mapping"

    report = import_lerobot_repo(
        "user/dataset",
        output_path,
        episodes=[0],
        camera_key=camera_key,
        dataset_cls=dataset_cls,
    )

    assert report.is_valid
    episode_dir = output_path / "episode_000000"
    actions = read_json(episode_dir / "actions.json")
    metadata = read_json(episode_dir / "metadata.json")

    assert len(sorted((episode_dir / "frames").glob("*.png"))) == 3
    assert [action["source_video_frame_index"] for action in actions] == [0, 1, 2]
    assert metadata["source_unique_video_frames"] == 3
    assert metadata["source_referenced_video_frames"] == 2
    assert metadata["exported_timesteps"] == 3


def test_invalid_timeline_rejected(tmp_path: Path) -> None:
    dataset_cls = fake_lerobot_dataset(
        sample_rows(), features("observation.images.front")
    )

    with pytest.raises(ValueError, match="Invalid LeRobot timeline"):
        import_lerobot_repo(
            "user/dataset",
            tmp_path / "out",
            episodes=[0],
            timeline="invalid",  # type: ignore[arg-type]
            dataset_cls=dataset_cls,
        )


def test_import_lerobot_repo_validates_invalid_episode(tmp_path: Path) -> None:
    dataset_cls = fake_lerobot_dataset(
        sample_rows(), features("observation.images.front"), total_episodes=2
    )

    with pytest.raises(ValueError, match="Invalid episode"):
        import_lerobot_repo(
            "user/dataset", tmp_path / "out", episodes=[3], dataset_cls=dataset_cls
        )


def test_missing_optional_dependency_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def missing_lerobot(name: str) -> Any:
        if name == "lerobot.datasets":
            raise ModuleNotFoundError("No module named 'lerobot'")
        return importlib.import_module(name)

    monkeypatch.setattr(lerobot.importlib, "import_module", missing_lerobot)

    with pytest.raises(LeRobotImportError, match="worldbench\\[lerobot\\]"):
        import_lerobot_repo("user/dataset", tmp_path / "out")
