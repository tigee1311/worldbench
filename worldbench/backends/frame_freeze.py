"""Deterministic frame-freeze corruption helpers."""

from __future__ import annotations

from dataclasses import dataclass
import random
import shutil
from pathlib import Path

from worldbench.utils import ensure_dir, list_image_files


@dataclass(frozen=True)
class FrameFreezeResult:
    """Summary of a frozen prediction sequence."""

    source_frames: int
    frozen_frames: int
    output_paths: list[Path]


def freeze_frames(
    source_frames: str | Path,
    output_frames: str | Path,
    severity: float = 0.0,
    seed: int = 42,
    overwrite: bool = True,
) -> FrameFreezeResult:
    """Copy a frame sequence while freezing a deterministic subset of timesteps.

    A frozen frame is copied from the most recent previous output frame, so the
    visible timeline can repeat short spans without modifying the source data.
    """

    if not 0.0 <= severity <= 1.0:
        raise ValueError(f"Severity must be between 0 and 1: {severity}")

    source = Path(source_frames)
    if not source.is_dir():
        raise FileNotFoundError(f"Source frame directory does not exist: {source}")

    frames = list_image_files(source)
    if not frames:
        raise ValueError(f"No image frames found in {source}")

    destination = Path(output_frames)
    if destination.exists() and overwrite:
        shutil.rmtree(destination)
    elif destination.exists():
        raise FileExistsError(f"Output frame directory already exists: {destination}")
    ensure_dir(destination)

    frozen_positions = _frozen_positions(len(frames), severity, seed)
    frozen_frames = 0
    output_paths: list[Path] = []
    previous_output: Path | None = None

    for idx, source_path in enumerate(frames):
        destination_path = destination / source_path.name
        if idx == 0 or idx not in frozen_positions or previous_output is None:
            shutil.copy2(source_path, destination_path)
        else:
            shutil.copy2(previous_output, destination_path)
            frozen_frames += 1
        previous_output = destination_path
        output_paths.append(destination_path)

    return FrameFreezeResult(
        source_frames=len(frames),
        frozen_frames=frozen_frames,
        output_paths=output_paths,
    )


def freeze_rollout_predictions(
    source_dataset: str | Path,
    output_root: str | Path,
    severity: float = 0.0,
    seed: int = 42,
    overwrite: bool = True,
) -> list[FrameFreezeResult]:
    """Create a WorldBench-style prediction tree from a rollout dataset root."""

    source_root = Path(source_dataset)
    if not source_root.is_dir():
        raise FileNotFoundError(f"Source dataset directory does not exist: {source_root}")

    destination_root = Path(output_root)
    if destination_root.exists() and overwrite:
        shutil.rmtree(destination_root)
    elif destination_root.exists():
        raise FileExistsError(f"Output root already exists: {destination_root}")
    ensure_dir(destination_root)

    results: list[FrameFreezeResult] = []
    for episode_dir in sorted(
        path for path in source_root.iterdir() if path.is_dir() and path.name.startswith("episode_")
    ):
        frames_dir = episode_dir / "frames"
        predictions_dir = destination_root / episode_dir.name / "predictions"
        result = freeze_frames(frames_dir, predictions_dir, severity=severity, seed=seed, overwrite=overwrite)
        results.append(result)
    return results


def _frozen_positions(frame_count: int, severity: float, seed: int) -> set[int]:
    if frame_count <= 1 or severity <= 0.0:
        return set()

    freeze_count = round((frame_count - 1) * severity)
    freeze_count = max(0, min(frame_count - 1, freeze_count))
    if freeze_count == 0:
        return set()

    positions = list(range(1, frame_count))
    random.Random(seed).shuffle(positions)
    return set(sorted(positions[:freeze_count]))
