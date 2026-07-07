"""Deterministic temporal scrambling helpers."""

from __future__ import annotations

from dataclasses import dataclass
import random
import shutil
from pathlib import Path

from worldbench.utils import ensure_dir, list_image_files


@dataclass(frozen=True)
class TemporalScrambleResult:
    """Summary of a temporally scrambled prediction sequence."""

    source_frames: int
    moved_frames: int
    output_paths: list[Path]
    moved_positions: list[int]

    @property
    def moved_frame_percentage(self) -> float:
        if self.source_frames <= 0:
            return 0.0
        return self.moved_frames / self.source_frames


def scramble_frames(
    source_frames: str | Path,
    output_frames: str | Path,
    severity: float = 0.0,
    seed: int = 42,
    overwrite: bool = True,
) -> TemporalScrambleResult:
    """Copy a frame sequence while deterministically scrambling local temporal order.

    The implementation rotates selected non-overlapping windows of three adjacent
    frames by one step. This keeps the corruption local and explainable while
    progressively increasing the number of out-of-order frames as severity rises.
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

    source_order = _scrambled_source_order(len(frames), severity, seed)
    output_paths: list[Path] = []
    moved_positions: list[int] = []

    for idx, source_index in enumerate(source_order):
        source_path = frames[source_index]
        destination_path = destination / f"{idx:06d}{source_path.suffix.lower()}"
        shutil.copy2(source_path, destination_path)
        output_paths.append(destination_path)
        if source_index != idx:
            moved_positions.append(idx)

    return TemporalScrambleResult(
        source_frames=len(frames),
        moved_frames=len(moved_positions),
        output_paths=output_paths,
        moved_positions=moved_positions,
    )


def scramble_rollout_predictions(
    source_dataset: str | Path,
    output_root: str | Path,
    severity: float = 0.0,
    seed: int = 42,
    overwrite: bool = True,
) -> list[TemporalScrambleResult]:
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

    results: list[TemporalScrambleResult] = []
    for episode_dir in sorted(
        path for path in source_root.iterdir() if path.is_dir() and path.name.startswith("episode_")
    ):
        frames_dir = episode_dir / "frames"
        predictions_dir = destination_root / episode_dir.name / "predictions"
        result = scramble_frames(
            frames_dir,
            predictions_dir,
            severity=severity,
            seed=seed,
            overwrite=overwrite,
        )
        results.append(result)
    return results


def _scrambled_source_order(frame_count: int, severity: float, seed: int) -> list[int]:
    source_order = list(range(frame_count))
    if frame_count <= 1 or severity <= 0.0:
        return source_order

    candidate_windows = list(range(1, max(1, frame_count - 2) + 1, 3))
    candidate_windows = [start for start in candidate_windows if start + 2 < frame_count]
    target_windows = round((frame_count - 1) * severity / 3.0)
    target_windows = max(0, min(len(candidate_windows), target_windows))
    if target_windows == 0:
        return source_order

    shuffled = candidate_windows[:]
    random.Random(seed).shuffle(shuffled)
    selected = sorted(shuffled[:target_windows])
    for start in selected:
        source_order[start : start + 3] = [
            source_order[start + 1],
            source_order[start + 2],
            source_order[start],
        ]
    return source_order
