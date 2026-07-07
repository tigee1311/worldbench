"""LeRobot import adapters.

This module keeps the original local LeRobot-style folder adapter and adds a
native Hugging Face LeRobotDataset importer for real robot datasets.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import inspect
import math
import shutil
from pathlib import Path
from typing import Any, Literal

import numpy as np
from PIL import Image, ImageDraw

from worldbench.dataset import validate_dataset
from worldbench.schemas import ValidationReport
from worldbench.utils import ensure_dir, list_image_files, write_json


REQUIRED_JSON_FILES = ("actions.json", "states.json", "metadata.json")
CAMERA_PREFIX = "observation.images."
ACTION_CANDIDATES = ("action",)
STATE_CANDIDATES = ("observation.state", "observation_state", "state")
TIMESTAMP_CANDIDATES = ("timestamp", "observation.timestamp")
EPISODE_INDEX_CANDIDATES = ("episode_index", "episode.index")
PREFERRED_VIDEO_BACKEND = "pyav"
TIMELINE_MODES = ("video", "control")
TimelineMode = Literal["video", "control"]
ACTION_ALIGNMENT_VIDEO = "latest_at_or_before_timestamp"
STATE_ALIGNMENT_VIDEO = "nearest_timestamp"
ACTION_ALIGNMENT_CONTROL = "source_control_row"
STATE_ALIGNMENT_CONTROL = "source_control_row"
TIMESTAMP_EPSILON = 1e-9


@dataclass(frozen=True)
class LeRobotFeatureInfo:
    """Resolved LeRobot keys needed to export a WorldBench dataset."""

    camera_keys: list[str]
    selected_camera: str
    action_key: str
    state_key: str | None
    timestamp_key: str | None
    episode_index_key: str | None
    fps: float | None


class LeRobotImportError(RuntimeError):
    """Raised when a native LeRobot dataset cannot be imported."""


@dataclass
class _EpisodeExport:
    episode_index: int
    episode_dir: Path
    frames_dir: Path
    actions: list[dict[str, Any]]
    states: list[dict[str, Any]]
    tasks: list[str]
    timeline: TimelineMode
    alignment_strategy: dict[str, str]
    source_control_steps: int = 0
    source_video_frame_ids: set[int] | None = None
    referenced_video_frame_ids: set[int] | None = None
    frame_count: int = 0


@dataclass(frozen=True)
class _SourceRow:
    row_index: int
    source_control_index: int
    episode_index: int
    timestamp: float | None
    video_frame_index: int | None
    video_timestamp: float | None
    row: dict[str, Any]


def import_lerobot_repo(
    repo_id: str,
    output_path: str | Path,
    episodes: list[int] | None = None,
    camera_key: str | None = None,
    timeline: TimelineMode = "video",
    overwrite: bool = True,
    dataset_cls: type | None = None,
) -> ValidationReport:
    """Load a LeRobotDataset repo and export selected episodes as WorldBench data.

    Args:
        repo_id: Hugging Face dataset repo id, such as ``username/dataset``.
        output_path: Destination directory for the WorldBench dataset.
        episodes: Optional absolute LeRobot episode indices to export.
        camera_key: Optional LeRobot image observation key to export.
        timeline: ``"video"`` exports one timestep per source camera frame;
            ``"control"`` exports one timestep per source control row.
        overwrite: Whether to replace an existing destination.
        dataset_cls: Test seam for injecting a small fake LeRobotDataset.
    """

    timeline = _validate_timeline(timeline)
    selected_episodes = _normalize_episodes(episodes)
    dataset_type = dataset_cls or _load_lerobot_dataset_class()
    dataset = _instantiate_lerobot_dataset(dataset_type, repo_id, selected_episodes)
    _validate_requested_episodes(dataset, selected_episodes)
    feature_info = inspect_lerobot_features(dataset, camera_key)
    _configure_lerobot_video_access(dataset, feature_info)

    destination = Path(output_path)
    if destination.exists() and overwrite:
        shutil.rmtree(destination)
    elif destination.exists():
        raise FileExistsError(f"Output path already exists: {destination}")
    ensure_dir(destination)

    exported = _export_lerobot_dataset(
        dataset, repo_id, destination, selected_episodes, feature_info, timeline
    )
    if not exported:
        raise LeRobotImportError("No frames were exported from the LeRobot dataset.")
    return validate_dataset(destination)


def parse_episode_selection(selection: str | None) -> list[int] | None:
    """Parse a LeRobot episode selection string.

    Supports comma-separated indices and half-open ranges, for example ``0``,
    ``0,2,4``, ``0:5``, or ``0:3,7``.
    """

    if selection is None or selection.strip() == "":
        return None

    episodes: list[int] = []
    seen: set[int] = set()
    for raw_part in selection.split(","):
        part = raw_part.strip()
        if not part:
            raise ValueError(f"Invalid empty episode selection in {selection!r}.")
        if ":" in part:
            pieces = part.split(":")
            if len(pieces) != 2 or not pieces[0] or not pieces[1]:
                raise ValueError(f"Invalid episode range {part!r}. Use START:STOP.")
            start, stop = (_parse_nonnegative_int(value, part) for value in pieces)
            if stop <= start:
                raise ValueError(
                    f"Invalid episode range {part!r}: STOP must be greater than START."
                )
            values = range(start, stop)
        else:
            values = [_parse_nonnegative_int(part, part)]

        for episode in values:
            if episode not in seen:
                episodes.append(episode)
                seen.add(episode)

    return episodes


def inspect_lerobot_features(
    dataset: Any, camera_key: str | None = None
) -> LeRobotFeatureInfo:
    """Inspect LeRobot feature keys and choose camera/action/state fields."""

    keys = _available_keys(dataset)
    camera_keys = sorted(key for key in keys if key.startswith(CAMERA_PREFIX))
    meta_video_keys = getattr(getattr(dataset, "meta", None), "video_keys", None)
    if meta_video_keys is not None:
        camera_keys = sorted(
            set(camera_keys).union(str(key) for key in meta_video_keys)
        )

    if not camera_keys:
        raise LeRobotImportError(
            "No camera observations found in the LeRobot dataset. "
            f"Expected keys beginning with {CAMERA_PREFIX!r}."
        )
    if camera_key is None:
        if len(camera_keys) > 1:
            available = ", ".join(camera_keys)
            raise LeRobotImportError(
                f"Multiple camera observations found. Specify --camera. Available cameras: {available}"
            )
        selected_camera = camera_keys[0]
    elif camera_key not in camera_keys:
        available = ", ".join(camera_keys)
        raise LeRobotImportError(
            f"Camera {camera_key!r} was not found. Available cameras: {available}"
        )
    else:
        selected_camera = camera_key

    action_key = _first_existing_key(keys, ACTION_CANDIDATES)
    if action_key is None:
        available = ", ".join(sorted(keys))
        raise LeRobotImportError(
            f"No action data found in LeRobot dataset. Available keys: {available}"
        )

    return LeRobotFeatureInfo(
        camera_keys=camera_keys,
        selected_camera=selected_camera,
        action_key=action_key,
        state_key=_first_existing_key(keys, STATE_CANDIDATES),
        timestamp_key=_first_existing_key(keys, TIMESTAMP_CANDIDATES),
        episode_index_key=_first_existing_key(keys, EPISODE_INDEX_CANDIDATES),
        fps=_dataset_fps(dataset),
    )


def import_lerobot_style(
    input_path: str | Path, output_path: str | Path, overwrite: bool = True
) -> ValidationReport:
    """Convert a local LeRobot-style folder into a WorldBench dataset."""

    source = Path(input_path)
    destination = Path(output_path)
    _validate_lerobot_source(source)

    if destination.exists() and overwrite:
        shutil.rmtree(destination)
    elif destination.exists():
        raise FileExistsError(f"Output path already exists: {destination}")

    episode_dir = destination / "episode_001"
    frames_dir = ensure_dir(episode_dir / "frames")
    for index, image_path in enumerate(list_image_files(source / "images")):
        shutil.copy2(image_path, frames_dir / f"{index:03d}{image_path.suffix.lower()}")

    for name in REQUIRED_JSON_FILES:
        shutil.copy2(source / name, episode_dir / name)

    return validate_dataset(destination)


def _load_lerobot_dataset_class() -> type:
    module = None
    try:
        module = importlib.import_module("lerobot.datasets")
    except ModuleNotFoundError as exc:
        raise LeRobotImportError(
            "Native LeRobot import requires the optional dependency. "
            'Install it with `python -m pip install "worldbench[lerobot]"`.'
        ) from exc

    if hasattr(module, "LeRobotDataset"):
        return module.LeRobotDataset

    try:
        submodule = importlib.import_module("lerobot.datasets.lerobot_dataset")
    except ModuleNotFoundError as exc:
        raise LeRobotImportError(
            "Installed lerobot package does not expose LeRobotDataset. "
            "Expected lerobot.datasets.LeRobotDataset or "
            "lerobot.datasets.lerobot_dataset.LeRobotDataset."
        ) from exc
    return submodule.LeRobotDataset


def _instantiate_lerobot_dataset(
    dataset_type: type, repo_id: str, episodes: list[int] | None
) -> Any:
    kwargs: dict[str, Any] = {"episodes": episodes}
    if _supports_keyword_argument(dataset_type, "return_uint8"):
        kwargs["return_uint8"] = True
    return dataset_type(repo_id, **kwargs)


def _supports_keyword_argument(callable_object: Any, name: str) -> bool:
    try:
        signature = inspect.signature(callable_object)
    except (TypeError, ValueError):
        return False
    return name in signature.parameters or any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )


def _validate_timeline(timeline: str) -> TimelineMode:
    if timeline == "video" or timeline == "control":
        return timeline
    available = ", ".join(TIMELINE_MODES)
    raise ValueError(f"Invalid LeRobot timeline {timeline!r}. Choose one of: {available}.")


def _normalize_episodes(episodes: list[int] | None) -> list[int] | None:
    if episodes is None:
        return None
    normalized: list[int] = []
    seen: set[int] = set()
    for episode in episodes:
        if episode < 0:
            raise ValueError(f"Episode index must be non-negative: {episode}")
        if episode not in seen:
            normalized.append(int(episode))
            seen.add(int(episode))
    return normalized


def _validate_requested_episodes(dataset: Any, episodes: list[int] | None) -> None:
    if episodes is None:
        return
    total = getattr(getattr(dataset, "meta", None), "total_episodes", None)
    if total is None:
        return
    invalid = [episode for episode in episodes if episode < 0 or episode >= int(total)]
    if invalid:
        raise ValueError(
            f"Invalid episode index/indices {invalid}; dataset has episodes 0 through {int(total) - 1}."
        )


def _available_keys(dataset: Any) -> set[str]:
    keys: set[str] = set()
    features = getattr(dataset, "features", None)
    if isinstance(features, dict):
        keys.update(str(key) for key in features)
    hf_dataset = getattr(dataset, "hf_dataset", None)
    hf_features = getattr(hf_dataset, "features", None)
    if isinstance(hf_features, dict):
        keys.update(str(key) for key in hf_features)
    if not keys and len(dataset) > 0:
        keys.update(str(key) for key in dataset[0].keys())
    return keys


def _first_existing_key(keys: set[str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in keys:
            return candidate
    return None


def _dataset_fps(dataset: Any) -> float | None:
    fps = getattr(dataset, "fps", None)
    if fps is None:
        fps = getattr(getattr(dataset, "meta", None), "fps", None)
    return None if fps is None else float(fps)


def _export_lerobot_dataset(
    dataset: Any,
    repo_id: str,
    destination: Path,
    requested_episodes: list[int] | None,
    feature_info: LeRobotFeatureInfo,
    timeline: TimelineMode,
) -> int:
    if timeline == "control":
        return _export_control_timeline(
            dataset, repo_id, destination, requested_episodes, feature_info
        )
    return _export_video_timeline(
        dataset, repo_id, destination, requested_episodes, feature_info
    )


def _export_control_timeline(
    dataset: Any,
    repo_id: str,
    destination: Path,
    requested_episodes: list[int] | None,
    feature_info: LeRobotFeatureInfo,
) -> int:
    exports: dict[int, _EpisodeExport] = {}
    fallback_episode = (
        requested_episodes[0]
        if requested_episodes and len(requested_episodes) == 1
        else None
    )

    for row_index in range(len(dataset)):
        source_row = _source_row_from_dataset(
            dataset,
            row_index,
            feature_info,
            fallback_episode=fallback_episode,
            include_image=True,
        )
        episode_index = source_row.episode_index
        if requested_episodes is not None and episode_index not in requested_episodes:
            continue
        episode_export = _episode_export_for(
            destination,
            episode_index,
            exports,
            timeline="control",
            alignment_strategy={
                "action": ACTION_ALIGNMENT_CONTROL,
                "state": STATE_ALIGNMENT_CONTROL,
            },
        )
        episode_export.source_control_steps += 1
        _record_video_frame_metadata(
            episode_export, dataset, episode_index, source_row, feature_info
        )
        _write_lerobot_timestep(
            episode_export,
            _row_with_control_provenance(source_row, source_row, source_row),
            feature_info,
        )

    _raise_missing_requested_episodes(requested_episodes, exports)
    return _finalize_lerobot_exports(exports, repo_id, feature_info)


def _record_video_frame_metadata(
    episode_export: _EpisodeExport,
    dataset: Any,
    episode_index: int,
    source_row: _SourceRow,
    feature_info: LeRobotFeatureInfo,
) -> None:
    _ensure_frame_id_sets(episode_export)
    max_frame_index = _episode_max_video_frame_index(
        dataset, episode_index, feature_info
    )
    if max_frame_index is not None:
        episode_export.source_video_frame_ids.update(range(max_frame_index + 1))
    elif source_row.video_frame_index is not None:
        episode_export.source_video_frame_ids.add(source_row.video_frame_index)

    if source_row.video_frame_index is not None:
        episode_export.referenced_video_frame_ids.add(source_row.video_frame_index)


def _export_video_timeline(
    dataset: Any,
    repo_id: str,
    destination: Path,
    requested_episodes: list[int] | None,
    feature_info: LeRobotFeatureInfo,
) -> int:
    exports: dict[int, _EpisodeExport] = {}
    source_rows_by_episode = _collect_source_rows_by_episode(
        dataset, requested_episodes, feature_info
    )

    for episode_index, source_rows in sorted(source_rows_by_episode.items()):
        episode_export = _episode_export_for(
            destination,
            episode_index,
            exports,
            timeline="video",
            alignment_strategy={
                "action": ACTION_ALIGNMENT_VIDEO,
                "state": STATE_ALIGNMENT_VIDEO,
            },
        )
        episode_export.source_control_steps = len(source_rows)
        frame_ids = _video_frame_ids_for_episode(dataset, episode_index, source_rows, feature_info)
        _ensure_frame_id_sets(episode_export)
        episode_export.source_video_frame_ids.update(frame_ids)
        episode_export.referenced_video_frame_ids.update(
            source_row.video_frame_index
            for source_row in source_rows
            if source_row.video_frame_index is not None
        )

        for frame_id in frame_ids:
            video_timestamp = _video_timestamp_from_frame_id(frame_id, feature_info)
            action_row = _latest_at_or_before(source_rows, video_timestamp)
            state_row = _nearest_by_timestamp(source_rows, video_timestamp)
            image_value = _image_for_video_frame(
                dataset, episode_index, frame_id, video_timestamp, source_rows, feature_info
            )
            aligned_row = _aligned_video_row(
                image_value,
                action_row,
                state_row,
                frame_id,
                video_timestamp,
                feature_info,
            )
            _write_lerobot_timestep(episode_export, aligned_row, feature_info)

    _raise_missing_requested_episodes(requested_episodes, exports)
    return _finalize_lerobot_exports(exports, repo_id, feature_info)


def _collect_source_rows_by_episode(
    dataset: Any,
    requested_episodes: list[int] | None,
    feature_info: LeRobotFeatureInfo,
) -> dict[int, list[_SourceRow]]:
    rows_by_episode: dict[int, list[_SourceRow]] = {}
    fallback_episode = (
        requested_episodes[0]
        if requested_episodes and len(requested_episodes) == 1
        else None
    )
    include_image = not _can_query_selected_video(dataset, feature_info)
    for row_index in range(len(dataset)):
        source_row = _source_row_from_dataset(
            dataset,
            row_index,
            feature_info,
            fallback_episode=fallback_episode,
            include_image=include_image,
        )
        if requested_episodes is not None and source_row.episode_index not in requested_episodes:
            continue
        rows_by_episode.setdefault(source_row.episode_index, []).append(source_row)
    return rows_by_episode


def _raise_missing_requested_episodes(
    requested_episodes: list[int] | None, exports: dict[int, _EpisodeExport]
) -> None:
    if requested_episodes is None:
        return
    missing = [episode for episode in requested_episodes if episode not in exports]
    if missing:
        raise ValueError(
            f"Requested episode(s) were not found in loaded LeRobot data: {missing}"
        )


def _finalize_lerobot_exports(
    exports: dict[int, _EpisodeExport],
    repo_id: str,
    feature_info: LeRobotFeatureInfo,
) -> int:
    frame_count = 0
    for episode_index in sorted(exports):
        episode_export = exports[episode_index]
        _write_lerobot_episode_records(episode_export, repo_id, feature_info)
        frame_count += episode_export.frame_count
    return frame_count


def _episode_export_for(
    destination: Path,
    episode_index: int,
    exports: dict[int, _EpisodeExport],
    timeline: TimelineMode,
    alignment_strategy: dict[str, str],
) -> _EpisodeExport:
    if episode_index not in exports:
        episode_dir = destination / f"episode_{episode_index:06d}"
        exports[episode_index] = _EpisodeExport(
            episode_index=episode_index,
            episode_dir=episode_dir,
            frames_dir=ensure_dir(episode_dir / "frames"),
            actions=[],
            states=[],
            tasks=[],
            timeline=timeline,
            alignment_strategy=alignment_strategy,
            source_video_frame_ids=set(),
            referenced_video_frame_ids=set(),
        )
    return exports[episode_index]


def _configure_lerobot_video_access(
    dataset: Any, feature_info: LeRobotFeatureInfo
) -> None:
    video_keys = _dataset_video_keys(dataset)
    if feature_info.selected_camera not in video_keys:
        return

    if hasattr(dataset, "video_backend") and _is_module_available("av"):
        dataset.video_backend = PREFERRED_VIDEO_BACKEND

    if feature_info.fps and hasattr(dataset, "tolerance_s"):
        existing = float(getattr(dataset, "tolerance_s", 0.0) or 0.0)
        dataset.tolerance_s = max(existing, 1.0 / feature_info.fps)


def _read_lerobot_row(
    dataset: Any, row_index: int, feature_info: LeRobotFeatureInfo
) -> dict[str, Any]:
    if not _can_read_selected_video(dataset, feature_info):
        return dataset[row_index]

    row = dict(dataset.hf_dataset[row_index])
    episode_index = _episode_index_from_row(
        row, feature_info.episode_index_key, fallback_episode=None
    )
    timestamp = _timestamp_from_row(row, feature_info.timestamp_key)
    if timestamp is None:
        return dataset[row_index]

    cached = _cached_selected_frame(dataset, episode_index, row, feature_info)
    if cached is not None:
        row[feature_info.selected_camera] = cached
    else:
        video_row = dataset._query_videos(
            {feature_info.selected_camera: [timestamp]}, episode_index
        )
        row.update(video_row)
        _cache_selected_frame(dataset, episode_index, row, feature_info)

    task = _task_from_row(dataset, row)
    if task is not None:
        row["task"] = task
    return row


def _source_row_from_dataset(
    dataset: Any,
    row_index: int,
    feature_info: LeRobotFeatureInfo,
    fallback_episode: int | None,
    include_image: bool,
) -> _SourceRow:
    row = _read_lerobot_source_row(dataset, row_index, feature_info, include_image)
    episode_index = _episode_index_from_row(
        row, feature_info.episode_index_key, fallback_episode
    )
    timestamp = _timestamp_from_row(row, feature_info.timestamp_key)
    video_frame_index = _source_video_frame_index(
        dataset, episode_index, timestamp, feature_info
    )
    video_timestamp = (
        _video_timestamp_from_frame_id(video_frame_index, feature_info)
        if video_frame_index is not None
        else None
    )
    return _SourceRow(
        row_index=row_index,
        source_control_index=_source_control_index(row, row_index),
        episode_index=episode_index,
        timestamp=timestamp,
        video_frame_index=video_frame_index,
        video_timestamp=video_timestamp,
        row=row,
    )


def _read_lerobot_source_row(
    dataset: Any,
    row_index: int,
    feature_info: LeRobotFeatureInfo,
    include_image: bool,
) -> dict[str, Any]:
    if include_image:
        return _read_lerobot_row(dataset, row_index, feature_info)
    if _can_query_selected_video(dataset, feature_info):
        row = dict(dataset.hf_dataset[row_index])
        task = _task_from_row(dataset, row)
        if task is not None:
            row["task"] = task
        return row
    return dataset[row_index]


def _source_control_index(row: dict[str, Any], row_index: int) -> int:
    if "index" in row:
        return int(_scalar_to_jsonable(row["index"]))
    return row_index


def _can_read_selected_video(
    dataset: Any, feature_info: LeRobotFeatureInfo
) -> bool:
    return (
        feature_info.selected_camera in _dataset_video_keys(dataset)
        and getattr(dataset, "hf_dataset", None) is not None
        and hasattr(dataset, "_query_videos")
        and feature_info.timestamp_key is not None
        and feature_info.episode_index_key is not None
    )


def _can_query_selected_video(dataset: Any, feature_info: LeRobotFeatureInfo) -> bool:
    return _can_read_selected_video(dataset, feature_info)


def _dataset_video_keys(dataset: Any) -> list[str]:
    video_keys = getattr(getattr(dataset, "meta", None), "video_keys", None)
    if video_keys is None:
        return []
    return [str(key) for key in video_keys]


def _is_module_available(name: str) -> bool:
    try:
        importlib.import_module(name)
    except ModuleNotFoundError:
        return False
    return True


def _task_from_row(dataset: Any, row: dict[str, Any]) -> str | None:
    if "task" in row:
        return str(_scalar_to_jsonable(row["task"]))
    task_index = row.get("task_index")
    tasks = getattr(getattr(dataset, "meta", None), "tasks", None)
    if task_index is None or tasks is None:
        return None
    try:
        return str(tasks.iloc[int(_scalar_to_jsonable(task_index))].name)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return None


def _source_video_frame_index(
    dataset: Any,
    episode_index: int,
    timestamp: float | None,
    feature_info: LeRobotFeatureInfo,
) -> int | None:
    if timestamp is None or not feature_info.fps:
        return None
    raw_frame_index = _nearest_video_frame_index(timestamp, feature_info.fps)
    max_frame_index = _episode_max_video_frame_index(
        dataset, episode_index, feature_info
    )
    if max_frame_index is not None:
        return max(0, min(raw_frame_index, max_frame_index))
    return max(0, raw_frame_index)


def _nearest_video_frame_index(timestamp: float, fps: float) -> int:
    return max(0, math.floor(timestamp * fps + 0.5 - TIMESTAMP_EPSILON))


def _episode_max_video_frame_index(
    dataset: Any, episode_index: int, feature_info: LeRobotFeatureInfo
) -> int | None:
    bounds = _episode_video_bounds(dataset, episode_index, feature_info.selected_camera)
    if bounds is None or not feature_info.fps:
        return None
    start, stop = bounds
    return max(0, math.floor((stop - start) * feature_info.fps + 1e-6))


def _episode_video_bounds(
    dataset: Any, episode_index: int, camera_key: str
) -> tuple[float, float] | None:
    episodes = getattr(getattr(dataset, "meta", None), "episodes", None)
    if episodes is None:
        return None
    try:
        episode = episodes[episode_index]
    except (IndexError, KeyError, TypeError):
        return None
    from_key = f"videos/{camera_key}/from_timestamp"
    to_key = f"videos/{camera_key}/to_timestamp"
    if from_key not in episode or to_key not in episode:
        return None
    return float(_scalar_to_jsonable(episode[from_key])), float(
        _scalar_to_jsonable(episode[to_key])
    )


def _video_frame_ids_for_episode(
    dataset: Any,
    episode_index: int,
    source_rows: list[_SourceRow],
    feature_info: LeRobotFeatureInfo,
) -> list[int]:
    max_frame_index = _episode_max_video_frame_index(
        dataset, episode_index, feature_info
    )
    if max_frame_index is not None:
        return list(range(max_frame_index + 1))

    frame_ids = sorted(
        {
            source_row.video_frame_index
            for source_row in source_rows
            if source_row.video_frame_index is not None
        }
    )
    if frame_ids:
        return frame_ids
    raise LeRobotImportError(
        "Video timeline requires timestamps and FPS to derive source camera frames."
    )


def _video_timestamp_from_frame_id(
    frame_id: int, feature_info: LeRobotFeatureInfo
) -> float:
    if not feature_info.fps:
        raise LeRobotImportError("Video timeline requires dataset FPS.")
    return frame_id / feature_info.fps


def _latest_at_or_before(
    source_rows: list[_SourceRow], target_timestamp: float
) -> _SourceRow:
    candidates = [
        source_row
        for source_row in source_rows
        if source_row.timestamp is not None
        and source_row.timestamp <= target_timestamp + TIMESTAMP_EPSILON
    ]
    if candidates:
        return max(candidates, key=lambda source_row: source_row.timestamp or 0.0)
    return _nearest_by_timestamp(source_rows, target_timestamp)


def _nearest_by_timestamp(
    source_rows: list[_SourceRow], target_timestamp: float
) -> _SourceRow:
    candidates = [source_row for source_row in source_rows if source_row.timestamp is not None]
    if not candidates:
        raise LeRobotImportError(
            "Video timeline alignment requires source control timestamps."
        )
    return min(
        candidates,
        key=lambda source_row: (
            abs((source_row.timestamp or 0.0) - target_timestamp),
            source_row.source_control_index,
        ),
    )


def _image_for_video_frame(
    dataset: Any,
    episode_index: int,
    frame_id: int,
    video_timestamp: float,
    source_rows: list[_SourceRow],
    feature_info: LeRobotFeatureInfo,
) -> Any:
    if _can_query_selected_video(dataset, feature_info):
        return dataset._query_videos(
            {feature_info.selected_camera: [video_timestamp]}, episode_index
        )[feature_info.selected_camera]

    matching_rows = [
        source_row
        for source_row in source_rows
        if source_row.video_frame_index == frame_id
        and feature_info.selected_camera in source_row.row
    ]
    if matching_rows:
        return matching_rows[0].row[feature_info.selected_camera]

    nearest = _nearest_by_timestamp(source_rows, video_timestamp)
    if feature_info.selected_camera not in nearest.row:
        raise LeRobotImportError(
            f"Selected camera {feature_info.selected_camera!r} is missing from source row."
        )
    return nearest.row[feature_info.selected_camera]


def _aligned_video_row(
    image_value: Any,
    action_row: _SourceRow,
    state_row: _SourceRow,
    frame_id: int,
    video_timestamp: float,
    feature_info: LeRobotFeatureInfo,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "_worldbench_timestamp": video_timestamp,
        "_source_video_frame_index": frame_id,
        "_source_video_timestamp": video_timestamp,
        "_source_action_control_index": action_row.source_control_index,
        "_source_action_control_timestamp": action_row.timestamp,
        "_source_state_control_index": state_row.source_control_index,
        "_source_state_control_timestamp": state_row.timestamp,
        feature_info.selected_camera: image_value,
        feature_info.action_key: action_row.row[feature_info.action_key],
    }
    if feature_info.state_key is not None and feature_info.state_key in state_row.row:
        row[feature_info.state_key] = state_row.row[feature_info.state_key]
    task = action_row.row.get("task") or state_row.row.get("task")
    if task is not None:
        row["task"] = task
    return row


def _row_with_control_provenance(
    source_row: _SourceRow, action_row: _SourceRow, state_row: _SourceRow
) -> dict[str, Any]:
    row = dict(source_row.row)
    row["_worldbench_timestamp"] = source_row.timestamp
    row["_source_video_frame_index"] = source_row.video_frame_index
    row["_source_video_timestamp"] = source_row.video_timestamp
    row["_source_action_control_index"] = action_row.source_control_index
    row["_source_action_control_timestamp"] = action_row.timestamp
    row["_source_state_control_index"] = state_row.source_control_index
    row["_source_state_control_timestamp"] = state_row.timestamp
    return row


def _ensure_frame_id_sets(episode_export: _EpisodeExport) -> None:
    if episode_export.source_video_frame_ids is None:
        episode_export.source_video_frame_ids = set()
    if episode_export.referenced_video_frame_ids is None:
        episode_export.referenced_video_frame_ids = set()


def _cached_selected_frame(
    dataset: Any,
    episode_index: int,
    row: dict[str, Any],
    feature_info: LeRobotFeatureInfo,
) -> Any | None:
    cache = getattr(dataset, "_worldbench_selected_frame_cache", None)
    if cache is None:
        return None
    cache_key = _selected_frame_cache_key(episode_index, row, feature_info)
    if cache_key is None or cache.get("key") != cache_key:
        return None
    return cache.get("frame")


def _cache_selected_frame(
    dataset: Any,
    episode_index: int,
    row: dict[str, Any],
    feature_info: LeRobotFeatureInfo,
) -> None:
    cache_key = _selected_frame_cache_key(episode_index, row, feature_info)
    if cache_key is None or feature_info.selected_camera not in row:
        return
    dataset._worldbench_selected_frame_cache = {
        "key": cache_key,
        "frame": row[feature_info.selected_camera],
    }


def _selected_frame_cache_key(
    episode_index: int,
    row: dict[str, Any],
    feature_info: LeRobotFeatureInfo,
) -> tuple[int, str, int] | None:
    timestamp = _timestamp_from_row(row, feature_info.timestamp_key)
    if timestamp is None or not feature_info.fps:
        return None
    return (
        episode_index,
        feature_info.selected_camera,
        _nearest_video_frame_index(timestamp, feature_info.fps),
    )


def _episode_index_from_row(
    row: dict[str, Any], episode_key: str | None, fallback_episode: int | None
) -> int:
    if episode_key is not None and episode_key in row:
        return int(_scalar_to_jsonable(row[episode_key]))
    if fallback_episode is not None:
        return fallback_episode
    raise LeRobotImportError(
        "LeRobot dataset does not expose an episode_index key. "
        "Specify a single episode with --episodes for this first importer version."
    )


def _write_lerobot_timestep(
    episode_export: _EpisodeExport,
    row: dict[str, Any],
    feature_info: LeRobotFeatureInfo,
) -> None:
    local_t = episode_export.frame_count
    timestamp = _timestamp_from_row(row, feature_info.timestamp_key)
    frame = _image_from_value(row[feature_info.selected_camera])
    frame.save(episode_export.frames_dir / f"{local_t:06d}.png")

    action_record = {
        "t": local_t,
        "timestamp": timestamp,
        "action": _to_jsonable(row[feature_info.action_key]),
    }
    _add_provenance_fields(action_record, row, source_kind="action")
    episode_export.actions.append(action_record)

    state_record: dict[str, Any] = {"t": local_t, "timestamp": timestamp}
    if feature_info.state_key is not None and feature_info.state_key in row:
        state_record["observation_state"] = _to_jsonable(row[feature_info.state_key])
    _add_provenance_fields(state_record, row, source_kind="state")
    episode_export.states.append(state_record)

    task = row.get("task")
    if task is not None:
        episode_export.tasks.append(str(_scalar_to_jsonable(task)))

    episode_export.frame_count += 1


def _add_provenance_fields(
    record: dict[str, Any], row: dict[str, Any], source_kind: Literal["action", "state"]
) -> None:
    control_index = row.get(f"_source_{source_kind}_control_index")
    control_timestamp = row.get(f"_source_{source_kind}_control_timestamp")
    if control_index is not None:
        record["source_control_index"] = int(_scalar_to_jsonable(control_index))
    if control_timestamp is not None:
        record["source_control_timestamp"] = float(_scalar_to_jsonable(control_timestamp))
    video_frame_index = row.get("_source_video_frame_index")
    video_timestamp = row.get("_source_video_timestamp")
    if video_frame_index is not None:
        record["source_video_frame_index"] = int(_scalar_to_jsonable(video_frame_index))
    if video_timestamp is not None:
        record["source_video_timestamp"] = float(_scalar_to_jsonable(video_timestamp))


def _write_lerobot_episode_records(
    episode_export: _EpisodeExport,
    repo_id: str,
    feature_info: LeRobotFeatureInfo,
) -> None:
    _ensure_frame_id_sets(episode_export)
    metadata = {
        "name": f"lerobot_episode_{episode_export.episode_index:06d}",
        "robot": "unknown",
        "task": episode_export.tasks[0] if episode_export.tasks else "unknown",
        "fps": feature_info.fps or 0.0,
        "description": "Episode exported from a native LeRobot dataset.",
        "source": "lerobot",
        "repo_id": repo_id,
        "episode_index": episode_export.episode_index,
        "camera_key": feature_info.selected_camera,
        "timeline": episode_export.timeline,
        "video_fps": feature_info.fps,
        "alignment_strategy": episode_export.alignment_strategy,
        "source_control_steps": episode_export.source_control_steps,
        "source_unique_video_frames": len(episode_export.source_video_frame_ids or set()),
        "source_referenced_video_frames": len(
            episode_export.referenced_video_frame_ids or set()
        ),
        "exported_timesteps": episode_export.frame_count,
    }

    write_json(episode_export.episode_dir / "actions.json", episode_export.actions)
    write_json(episode_export.episode_dir / "states.json", episode_export.states)
    write_json(episode_export.episode_dir / "metadata.json", metadata)


def _timestamp_from_row(row: dict[str, Any], timestamp_key: str | None) -> float | None:
    if "_worldbench_timestamp" in row:
        return float(_scalar_to_jsonable(row["_worldbench_timestamp"]))
    if timestamp_key is None or timestamp_key not in row:
        return None
    return float(_scalar_to_jsonable(row[timestamp_key]))


def _image_from_value(value: Any) -> Image.Image:
    if isinstance(value, Image.Image):
        return value.convert("RGB")
    if isinstance(value, (str, Path)):
        return Image.open(value).convert("RGB")

    array = _value_to_numpy(value)
    if (
        array.ndim == 3
        and array.shape[0] in {1, 3, 4}
        and array.shape[-1] not in {1, 3, 4}
    ):
        array = np.transpose(array, (1, 2, 0))
    if array.ndim == 2:
        mode = "L"
    elif array.ndim == 3 and array.shape[2] in {1, 3, 4}:
        mode = None
        if array.shape[2] == 1:
            array = array[:, :, 0]
            mode = "L"
    else:
        raise LeRobotImportError(f"Unsupported camera frame shape: {array.shape}")

    if np.issubdtype(array.dtype, np.floating):
        max_value = float(np.nanmax(array)) if array.size else 0.0
        if max_value <= 1.0:
            array = array * 255.0
        array = np.clip(array, 0, 255).astype(np.uint8)
    elif array.dtype != np.uint8:
        array = np.clip(array, 0, 255).astype(np.uint8)

    image = Image.fromarray(array, mode=mode)
    return image.convert("RGB")


def _value_to_numpy(value: Any) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        return np.asarray(value.numpy())
    return np.asarray(value)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return _to_jsonable(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if hasattr(value, "detach") or hasattr(value, "cpu") or hasattr(value, "numpy"):
        array = _value_to_numpy(value)
        if array.shape == ():
            return array.item()
        return _to_jsonable(array.tolist())
    return value


def _scalar_to_jsonable(value: Any) -> Any:
    converted = _to_jsonable(value)
    if isinstance(converted, list) and len(converted) == 1:
        return converted[0]
    return converted


def _parse_nonnegative_int(value: str, context: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid episode value {context!r}.") from exc
    if parsed < 0:
        raise ValueError(f"Episode value must be non-negative: {parsed}")
    return parsed


def create_lerobot_style_demo_source(
    output_path: str | Path, overwrite: bool = True
) -> Path:
    """Create a tiny synthetic LeRobot-style source folder for adapter demos."""

    root = Path(output_path)
    if root.exists() and overwrite:
        shutil.rmtree(root)
    elif root.exists():
        raise FileExistsError(f"Output path already exists: {root}")

    images_dir = ensure_dir(root / "images")
    states = []
    actions = []
    robot_x, robot_y = 24, 54
    object_x, object_y = 88, 54

    for t in range(8):
        if t > 0:
            robot_x += 8
            if robot_x >= object_x - 18:
                object_x += 5
        states.append(
            {
                "t": t,
                "robot_x": robot_x,
                "robot_y": robot_y,
                "object_x": object_x,
                "object_y": object_y,
            }
        )
        _render_lerobot_demo_frame(
            (robot_x, robot_y), (object_x, object_y), f"{t:03d}"
        ).save(images_dir / f"{t:03d}.png")

    for t in range(7):
        actions.append(
            {"t": t, "action": "move_right", "dx": 1.0, "dy": 0.0, "gripper": "open"}
        )

    write_json(root / "actions.json", actions)
    write_json(root / "states.json", states)
    write_json(
        root / "metadata.json",
        {
            "name": "lerobot_style_push_cube_demo",
            "robot": "synthetic_2d_arm",
            "task": "push cube",
            "fps": 5,
            "description": "Tiny synthetic source folder for the experimental LeRobot-style WorldBench adapter.",
        },
    )
    return root


def _validate_lerobot_source(source: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"LeRobot-style input path does not exist: {source}")
    if not source.is_dir():
        raise NotADirectoryError(
            f"LeRobot-style input path is not a directory: {source}"
        )
    images_dir = source / "images"
    if not images_dir.is_dir():
        raise FileNotFoundError(f"Missing images/ directory: {images_dir}")
    if not list_image_files(images_dir):
        raise ValueError(f"No image files found in {images_dir}")
    for name in REQUIRED_JSON_FILES:
        if not (source / name).is_file():
            raise FileNotFoundError(f"Missing {name}: {source / name}")


def _render_lerobot_demo_frame(
    robot: tuple[int, int], obj: tuple[int, int], label: str
) -> Image.Image:
    width, height = 128, 96
    image = Image.new("RGB", (width, height), (245, 248, 250))
    draw = ImageDraw.Draw(image)
    for x in range(0, width, 16):
        draw.line((x, 0, x, height), fill=(222, 229, 235), width=1)
    for y in range(0, height, 16):
        draw.line((0, y, width, y), fill=(222, 229, 235), width=1)
    draw.rectangle((5, 5, width - 6, height - 6), outline=(175, 188, 199), width=1)
    draw.text((8, 7), f"lerobot-style {label}", fill=(82, 96, 110))

    rx, ry = robot
    ox, oy = obj
    draw.line((rx, ry, ox, oy), fill=(140, 154, 165), width=2)
    draw.ellipse(
        (rx - 8, ry - 8, rx + 8, ry + 8),
        fill=(218, 65, 54),
        outline=(148, 43, 35),
        width=2,
    )
    draw.rectangle(
        (ox - 8, oy - 8, ox + 8, oy + 8),
        fill=(35, 170, 95),
        outline=(18, 102, 60),
        width=2,
    )
    return image
