#!/usr/bin/env python3
"""Prepare NanoWM RT-1 outputs for WorldBench checkpoint regression.

This adapter intentionally does not import NanoWM, Hugging Face, torch, or any
model code. It standardizes already-generated ground-truth and prediction clips
into the video-folder layout consumed by `worldbench eval-batch`.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import numpy as np
from PIL import Image

from worldbench.runners.video import VIDEO_EXTENSIONS
from worldbench.utils import IMAGE_EXTENSIONS, write_json
from worldbench.version import WORLD_BENCH_VERSION


ADAPTER_NAME = "nanowm_rt1_prepare_worldbench_inputs"
MANIFEST_SCHEMA_VERSION = "1"


class AdapterError(ValueError):
    """Raised when NanoWM outputs cannot be prepared without ambiguity."""


@dataclass(frozen=True)
class MediaInfo:
    source: Path
    kind: str
    frame_count: int
    width: int
    height: int
    fps: float | None
    extension: str | None
    files: tuple[Path, ...]

    @property
    def resolution(self) -> list[int]:
        return [self.width, self.height]


@dataclass(frozen=True)
class EpisodeInput:
    episode_id: str
    ground_truth: MediaInfo
    baseline: MediaInfo
    candidate: MediaInfo | None
    output_relative_path: Path


def prepare_worldbench_inputs(
    *,
    ground_truth: Path | None,
    baseline: Path | None,
    candidate: Path | None = None,
    episode_ids: list[str] | None = None,
    baseline_checkpoint: str | None,
    candidate_checkpoint: str | None = None,
    context_frames: int,
    prediction_frames: int,
    fps: float,
    dataset: str,
    dataset_source: str | None,
    output_dir: Path,
    camera: str | None = None,
    metadata_json: Path | None = None,
    known_limitations: list[str] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Validate and standardize NanoWM output clips for WorldBench."""

    metadata = _load_metadata(metadata_json)
    ground_truth = _metadata_path(metadata, "ground_truth", ground_truth)
    baseline = _metadata_path(metadata, "baseline", baseline)
    candidate = _metadata_path(metadata, "candidate", candidate)
    episode_ids = episode_ids or metadata.get("episode_ids")
    baseline_checkpoint = baseline_checkpoint or metadata.get("baseline_checkpoint")
    candidate_checkpoint = candidate_checkpoint or metadata.get("candidate_checkpoint")
    dataset = dataset or metadata.get("dataset")
    dataset_source = dataset_source or metadata.get("dataset_source")
    camera = camera or metadata.get("camera")
    context_frames = _metadata_int(metadata, "context_frames", context_frames)
    prediction_frames = _metadata_int(metadata, "prediction_frames", prediction_frames)
    fps = _metadata_float(metadata, "fps", fps)
    known_limitations = known_limitations or metadata.get("known_limitations") or []

    _require_path("ground truth", ground_truth)
    _require_path("baseline", baseline)
    if not baseline_checkpoint:
        raise AdapterError("--baseline-checkpoint is required.")
    if candidate is not None and not candidate_checkpoint:
        raise AdapterError("--candidate-checkpoint is required when --candidate is set.")
    if context_frames < 0:
        raise AdapterError("--context-frames must be non-negative.")
    if prediction_frames <= 0:
        raise AdapterError("--prediction-frames must be positive.")
    if fps <= 0:
        raise AdapterError("--fps must be positive.")
    if not dataset:
        raise AdapterError("--dataset is required.")

    total_frames = context_frames + prediction_frames
    episodes = _resolve_episodes(
        ground_truth=ground_truth,
        baseline=baseline,
        candidate=candidate,
        episode_ids=episode_ids or [],
        expected_frames=total_frames,
        expected_fps=fps,
    )
    if not episodes:
        raise AdapterError("No episodes were selected.")
    _validate_output_is_separate(
        output_dir,
        [path for path in (ground_truth, baseline, candidate) if path is not None],
    )

    if output_dir.exists():
        if not overwrite:
            raise AdapterError(
                f"Output directory already exists: {output_dir}. Use --overwrite to replace it."
            )
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for episode in episodes:
        _materialize_media(
            episode.ground_truth,
            output_dir / "ground_truth" / episode.output_relative_path,
            fps=fps,
        )
        _materialize_media(
            episode.baseline,
            output_dir / "baseline" / episode.output_relative_path,
            fps=fps,
        )
        if episode.candidate is not None:
            _materialize_media(
                episode.candidate,
                output_dir / "candidate" / episode.output_relative_path,
                fps=fps,
            )

    resolutions = {tuple(ep.ground_truth.resolution) for ep in episodes}
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "adapter": ADAPTER_NAME,
        "dataset": dataset,
        "dataset_source": dataset_source,
        "episodes": [
            {
                "episode_id": episode.episode_id,
                "output_relative_path": episode.output_relative_path.as_posix(),
                "frame_count": episode.ground_truth.frame_count,
                "context_frames": context_frames,
                "prediction_frames": prediction_frames,
                "resolution": episode.ground_truth.resolution,
                "source_kind": episode.ground_truth.kind,
            }
            for episode in episodes
        ],
        "camera": camera,
        "baseline_checkpoint": baseline_checkpoint,
        "candidate_checkpoint": candidate_checkpoint,
        "context_frames": context_frames,
        "prediction_frames": prediction_frames,
        "fps": fps,
        "resolution": list(next(iter(resolutions))) if len(resolutions) == 1 else None,
        "ground_truth_directory": "ground_truth",
        "baseline_directory": "baseline",
        "candidate_directory": "candidate" if candidate is not None else None,
        "source_files": [
            {
                "episode_id": episode.episode_id,
                "ground_truth": _source_payload(episode.ground_truth),
                "baseline": _source_payload(episode.baseline),
                "candidate": _source_payload(episode.candidate)
                if episode.candidate is not None
                else None,
            }
            for episode in episodes
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "worldbench_version": WORLD_BENCH_VERSION,
        "worldbench_commit": _worldbench_commit(),
        "known_limitations": known_limitations,
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def _resolve_episodes(
    *,
    ground_truth: Path,
    baseline: Path,
    candidate: Path | None,
    episode_ids: list[str],
    expected_frames: int,
    expected_fps: float,
) -> list[EpisodeInput]:
    if len(set(episode_ids)) != len(episode_ids):
        raise AdapterError("Duplicate episode identifiers are not allowed.")

    gt_entries = _collect_media(ground_truth, single_episode_ids=episode_ids)
    baseline_entries = _collect_media(baseline, single_episode_ids=episode_ids)
    candidate_entries = (
        _collect_media(candidate, single_episode_ids=episode_ids)
        if candidate is not None
        else {}
    )

    selected_ids = episode_ids or sorted(gt_entries)
    missing_gt = [episode_id for episode_id in selected_ids if episode_id not in gt_entries]
    if missing_gt:
        raise AdapterError(f"Missing ground truth for episode(s): {', '.join(missing_gt)}")

    _validate_matching_ids("baseline", selected_ids, baseline_entries)
    if candidate is not None:
        _validate_matching_ids("candidate", selected_ids, candidate_entries)

    output_names = [_output_relative_path(episode_id, gt_entries[episode_id]) for episode_id in selected_ids]
    if len({path.as_posix() for path in output_names}) != len(output_names):
        raise AdapterError("Episode identifiers map to duplicate output filenames.")

    episodes = []
    for episode_id, output_name in zip(selected_ids, output_names, strict=True):
        gt = _inspect_media(
            gt_entries[episode_id],
            label=f"ground truth {episode_id}",
            expected_frames=expected_frames,
            expected_fps=expected_fps,
        )
        base = _inspect_media(
            baseline_entries[episode_id],
            label=f"baseline {episode_id}",
            expected_frames=expected_frames,
            expected_fps=expected_fps,
        )
        cand = (
            _inspect_media(
                candidate_entries[episode_id],
                label=f"candidate {episode_id}",
                expected_frames=expected_frames,
                expected_fps=expected_fps,
            )
            if candidate is not None
            else None
        )
        _validate_compatible(episode_id, gt, base)
        if cand is not None:
            _validate_compatible(episode_id, gt, cand)
        episodes.append(
            EpisodeInput(
                episode_id=episode_id,
                ground_truth=gt,
                baseline=base,
                candidate=cand,
                output_relative_path=output_name,
            )
        )
    return episodes


def _collect_media(root: Path, *, single_episode_ids: list[str]) -> dict[str, Path]:
    if not root.exists():
        raise AdapterError(f"Input path does not exist: {root}")
    if root.is_file():
        if root.suffix.lower() not in VIDEO_EXTENSIONS:
            raise AdapterError(
                f"Unsupported file extension for {root}. Supported videos: "
                f"{', '.join(sorted(VIDEO_EXTENSIONS))}."
            )
        if len(single_episode_ids) != 1:
            raise AdapterError(
                "A single input video requires exactly one --episode-id."
            )
        return {single_episode_ids[0]: root}
    if not root.is_dir():
        raise AdapterError(f"Input path is neither a file nor a directory: {root}")

    root_images = _image_files(root)
    if root_images:
        if len(single_episode_ids) != 1:
            raise AdapterError(
                "A single frame directory requires exactly one --episode-id."
            )
        return {single_episode_ids[0]: root}

    video_files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )
    frame_dirs = sorted(
        path
        for path in root.rglob("*")
        if path.is_dir() and _image_files(path)
    )
    if video_files and frame_dirs:
        raise AdapterError(
            f"Mixed video files and frame directories are not supported under {root}."
        )
    if video_files:
        entries = {
            path.relative_to(root).as_posix(): path
            for path in video_files
        }
    elif frame_dirs:
        entries = {
            path.relative_to(root).as_posix(): path
            for path in frame_dirs
        }
    else:
        raise AdapterError(
            f"No supported videos or frame directories found under {root}."
        )

    if single_episode_ids:
        missing = [episode_id for episode_id in single_episode_ids if episode_id not in entries]
        if missing:
            raise AdapterError(
                f"Requested episode id(s) not found under {root}: {', '.join(missing)}"
            )
        return {episode_id: entries[episode_id] for episode_id in single_episode_ids}
    return entries


def _inspect_media(
    source: Path,
    *,
    label: str,
    expected_frames: int,
    expected_fps: float,
) -> MediaInfo:
    if source.is_file():
        return _inspect_video(
            source,
            label=label,
            expected_frames=expected_frames,
            expected_fps=expected_fps,
        )
    return _inspect_frame_dir(source, label=label, expected_frames=expected_frames)


def _inspect_video(
    source: Path,
    *,
    label: str,
    expected_frames: int,
    expected_fps: float,
) -> MediaInfo:
    try:
        import imageio.v2 as imageio
    except ImportError as exc:  # pragma: no cover
        raise AdapterError(
            "Video inputs require imageio. Install WorldBench with the video extra."
        ) from exc

    try:
        reader = imageio.get_reader(source)
        metadata = reader.get_meta_data()
        fps = _read_fps(metadata)
        frame_count = 0
        width = height = None
        for frame in reader:
            array = _as_rgb_uint8(frame, label=label)
            current_height, current_width = array.shape[:2]
            if width is None or height is None:
                width = current_width
                height = current_height
            elif (width, height) != (current_width, current_height):
                raise AdapterError(
                    f"{label} has mixed frame resolutions; frame {frame_count} is "
                    f"{current_width}x{current_height}, expected {width}x{height}."
                )
            frame_count += 1
        reader.close()
    except AdapterError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise AdapterError(f"{label} video is unreadable: {source} ({exc})") from exc

    if width is None or height is None or frame_count == 0:
        raise AdapterError(f"{label} video is empty: {source}")
    _validate_frame_count(label, frame_count, expected_frames)
    if fps is not None:
        _validate_fps(label, fps, expected_fps)

    return MediaInfo(
        source=source,
        kind="video",
        frame_count=frame_count,
        width=width,
        height=height,
        fps=fps,
        extension=source.suffix.lower(),
        files=(source,),
    )


def _inspect_frame_dir(source: Path, *, label: str, expected_frames: int) -> MediaInfo:
    files = tuple(_image_files(source))
    if not files:
        raise AdapterError(f"{label} frame directory is empty: {source}")
    width = height = None
    for index, path in enumerate(files):
        with Image.open(path) as image:
            current_width, current_height = image.convert("RGB").size
        if width is None or height is None:
            width = current_width
            height = current_height
        elif (width, height) != (current_width, current_height):
            raise AdapterError(
                f"{label} has mixed frame resolutions; frame {index} is "
                f"{current_width}x{current_height}, expected {width}x{height}."
            )
    assert width is not None and height is not None
    _validate_frame_count(label, len(files), expected_frames)
    return MediaInfo(
        source=source,
        kind="frames",
        frame_count=len(files),
        width=width,
        height=height,
        fps=None,
        extension=None,
        files=files,
    )


def _materialize_media(source: MediaInfo, destination: Path, *, fps: float) -> None:
    _ensure_relative_to(destination, destination.parents[1])
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.kind == "video":
        shutil.copy2(source.source, destination)
        return

    try:
        import imageio.v2 as imageio
    except ImportError as exc:  # pragma: no cover
        raise AdapterError(
            "Frame-directory inputs require imageio to encode MP4 outputs."
        ) from exc

    writer = imageio.get_writer(destination, fps=fps, macro_block_size=1)
    try:
        for frame_path in source.files:
            with Image.open(frame_path) as image:
                writer.append_data(np.asarray(image.convert("RGB"), dtype=np.uint8))
    finally:
        writer.close()


def _validate_matching_ids(
    label: str, selected_ids: list[str], entries: dict[str, Path]
) -> None:
    selected = set(selected_ids)
    available = set(entries)
    missing = sorted(selected - available)
    extra = sorted(available - selected)
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"missing {label}: {', '.join(missing)}")
        if extra:
            parts.append(f"{label}-only episodes: {', '.join(extra)}")
        raise AdapterError("; ".join(parts))


def _validate_compatible(episode_id: str, ground_truth: MediaInfo, prediction: MediaInfo) -> None:
    if ground_truth.frame_count != prediction.frame_count:
        raise AdapterError(
            f"{episode_id} frame count mismatch: ground truth has "
            f"{ground_truth.frame_count}, prediction has {prediction.frame_count}."
        )
    if (ground_truth.width, ground_truth.height) != (prediction.width, prediction.height):
        raise AdapterError(
            f"{episode_id} resolution mismatch: ground truth is "
            f"{ground_truth.width}x{ground_truth.height}, prediction is "
            f"{prediction.width}x{prediction.height}."
        )


def _validate_frame_count(label: str, actual: int, expected: int) -> None:
    if actual != expected:
        raise AdapterError(
            f"{label} has {actual} frame(s), expected {expected} "
            "(context_frames + prediction_frames)."
        )


def _validate_fps(label: str, actual: float, expected: float) -> None:
    tolerance = max(0.05, max(actual, expected) * 0.01)
    if abs(actual - expected) > tolerance:
        raise AdapterError(
            f"{label} FPS {actual:.3f} does not match expected FPS {expected:.3f}."
        )


def _output_relative_path(episode_id: str, source: Path) -> Path:
    safe = Path(episode_id)
    if safe.is_absolute() or ".." in safe.parts:
        raise AdapterError(f"Episode id must be relative and stay inside output: {episode_id}")
    if source.is_file() and safe.suffix.lower() in VIDEO_EXTENSIONS:
        output = safe
    elif safe.suffix.lower() in VIDEO_EXTENSIONS:
        output = safe
    else:
        output = safe.with_suffix(".mp4")
    _ensure_relative_to(output, Path("."))
    return output


def _image_files(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    return sorted(
        item
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )


def _as_rgb_uint8(frame: Any, *, label: str) -> np.ndarray:
    array = np.asarray(frame)
    if array.ndim == 2:
        array = np.stack([array, array, array], axis=2)
    if array.ndim != 3 or array.shape[2] not in {3, 4}:
        raise AdapterError(f"{label} has unsupported frame shape: {array.shape}")
    array = array[:, :, :3]
    if array.dtype != np.uint8:
        array = np.clip(array, 0, 255).astype(np.uint8)
    return array


def _read_fps(metadata: dict[str, Any]) -> float | None:
    fps = metadata.get("fps") or metadata.get("framerate")
    if isinstance(fps, (int, float)) and float(fps) > 0:
        return float(fps)
    return None


def _source_payload(source: MediaInfo) -> dict[str, Any]:
    return {
        "path": str(source.source),
        "kind": source.kind,
        "frame_count": source.frame_count,
        "resolution": source.resolution,
        "fps": source.fps,
        "files": [str(path) for path in source.files],
    }


def _load_metadata(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:  # noqa: BLE001
        raise AdapterError(f"Could not parse metadata JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise AdapterError(f"Metadata JSON must be an object: {path}")
    return data


def _metadata_path(metadata: dict[str, Any], key: str, fallback: Path | None) -> Path | None:
    value = metadata.get(key)
    if fallback is not None or value is None:
        return fallback
    return Path(str(value))


def _metadata_int(metadata: dict[str, Any], key: str, fallback: int) -> int:
    value = metadata.get(key, fallback)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise AdapterError(f"{key} must be an integer.") from exc


def _metadata_float(metadata: dict[str, Any], key: str, fallback: float) -> float:
    value = metadata.get(key, fallback)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise AdapterError(f"{key} must be a number.") from exc


def _require_path(label: str, path: Path | None) -> None:
    if path is None:
        raise AdapterError(f"--{label.replace(' ', '-')} is required.")
    if not path.exists():
        raise AdapterError(f"{label.capitalize()} path does not exist: {path}")


def _ensure_relative_to(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise AdapterError(f"Output path escapes expected root: {path}") from exc


def _validate_output_is_separate(output_dir: Path, source_paths: list[Path]) -> None:
    resolved_output = output_dir.resolve()
    for source in source_paths:
        resolved_source = source.resolve()
        if resolved_output == resolved_source:
            raise AdapterError(
                f"Output directory must be separate from input sources: {output_dir}"
            )
        try:
            resolved_output.relative_to(resolved_source)
        except ValueError:
            pass
        else:
            raise AdapterError(
                f"Output directory must not be inside input source: {output_dir}"
            )
        try:
            resolved_source.relative_to(resolved_output)
        except ValueError:
            pass
        else:
            raise AdapterError(
                f"Input source must not be inside output directory: {source}"
            )


def _worldbench_commit() -> str | None:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:  # noqa: BLE001
        return None
    return result.stdout.strip() or None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare already-generated NanoWM RT-1 clips for WorldBench."
    )
    parser.add_argument("--ground-truth", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--episode-id", action="append", default=[])
    parser.add_argument("--baseline-checkpoint")
    parser.add_argument("--candidate-checkpoint")
    parser.add_argument("--context-frames", type=int, required=True)
    parser.add_argument("--prediction-frames", type=int, required=True)
    parser.add_argument("--fps", type=float, required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--dataset-source")
    parser.add_argument("--camera")
    parser.add_argument("--metadata-json", type=Path)
    parser.add_argument("--known-limitation", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        manifest = prepare_worldbench_inputs(
            ground_truth=args.ground_truth,
            baseline=args.baseline,
            candidate=args.candidate,
            episode_ids=args.episode_id,
            baseline_checkpoint=args.baseline_checkpoint,
            candidate_checkpoint=args.candidate_checkpoint,
            context_frames=args.context_frames,
            prediction_frames=args.prediction_frames,
            fps=args.fps,
            dataset=args.dataset,
            dataset_source=args.dataset_source,
            camera=args.camera,
            metadata_json=args.metadata_json,
            output_dir=args.output_dir,
            known_limitations=args.known_limitation,
            overwrite=args.overwrite,
        )
    except AdapterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"Prepared {len(manifest['episodes'])} episode(s) at {args.output_dir}")
    print(f"Manifest: {args.output_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
