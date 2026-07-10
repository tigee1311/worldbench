"""Video-pair evaluation adapters for WorldBench."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from typing import Any

import numpy as np
from PIL import Image

from worldbench.config import WorldBenchConfig
from worldbench.runners.evaluator import EvaluationRunner
from worldbench.schemas import EvaluationResult
from worldbench.utils import write_json


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


class VideoEvaluationError(ValueError):
    """Raised when a video pair cannot be evaluated honestly."""


@dataclass(frozen=True)
class DecodedVideo:
    path: Path
    frames: list[np.ndarray]
    fps: float | None
    width: int
    height: int

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height} RGB"


def evaluate_video_pair(
    ground_truth: str | Path,
    prediction: str | Path,
    *,
    skip_context: int = 0,
    name: str | None = None,
    config: WorldBenchConfig | None = None,
) -> EvaluationResult:
    """Evaluate a ground-truth video against a predicted video."""

    gt_path = Path(ground_truth)
    pred_path = Path(prediction)
    if skip_context < 0:
        raise VideoEvaluationError("--skip-context must be non-negative.")

    gt_video = decode_video(gt_path, label="Ground truth")
    pred_video = decode_video(pred_path, label="Prediction")
    validate_video_pair(gt_video, pred_video, skip_context=skip_context)

    future_gt = gt_video.frames[skip_context:]
    future_pred = pred_video.frames[skip_context:]
    episode_name = "episode_001"

    with tempfile.TemporaryDirectory(prefix="worldbench-video-") as tmpdir:
        root = Path(tmpdir)
        dataset_dir = root / "dataset"
        episode_dir = dataset_dir / episode_name
        frames_dir = episode_dir / "frames"
        predictions_dir = root / "predictions"
        _write_frames(future_gt, frames_dir)
        _write_frames(future_pred, predictions_dir)
        write_json(episode_dir / "actions.json", [])
        write_json(episode_dir / "states.json", [])
        write_json(
            episode_dir / "metadata.json",
            {
                "name": name or "video_pair",
                "robot": "unknown",
                "task": "video_pair_evaluation",
                "fps": gt_video.fps or 0.0,
                "description": "Temporary video-pair adapter dataset for WorldBench evaluation.",
                "source": "video_pair",
            },
        )
        result = EvaluationRunner(dataset_dir, predictions=predictions_dir).run(
            config=config
        )

    result.dataset_path = str(gt_path)
    result.predictions_path = str(pred_path)
    result.provenance = {
        "source": "video_pair",
        "name": name,
        "ground_truth_path": str(gt_path),
        "prediction_path": str(pred_path),
        "skip_context": skip_context,
        "ground_truth_frame_count": gt_video.frame_count,
        "prediction_frame_count": pred_video.frame_count,
        "evaluated_frame_count": len(future_gt),
        "evaluated_ground_truth_frames": len(future_gt),
        "evaluated_prediction_frames": len(future_pred),
        "fps": gt_video.fps,
        "prediction_fps": pred_video.fps,
        "resolution": gt_video.resolution,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return result


def decode_video(path: Path, *, label: str) -> DecodedVideo:
    """Decode a video into RGB uint8 frames and basic metadata."""

    if not path.exists():
        raise VideoEvaluationError(f"{label} video does not exist: {path}")
    if not path.is_file():
        raise VideoEvaluationError(f"{label} path is not a file: {path}")

    try:
        import imageio.v2 as imageio
    except ImportError as exc:  # pragma: no cover - exercised only without extras
        raise VideoEvaluationError(
            "Video evaluation requires the optional video dependencies. "
            "Install WorldBench with the video extra."
        ) from exc

    try:
        reader = imageio.get_reader(path)
        metadata = reader.get_meta_data()
        frames = [_as_rgb_uint8(frame) for frame in reader]
        reader.close()
    except Exception as exc:  # noqa: BLE001
        raise VideoEvaluationError(
            f"{label} video is unreadable: {path} ({exc})"
        ) from exc

    if not frames:
        raise VideoEvaluationError(f"{label} video is empty: {path}")

    height, width = frames[0].shape[:2]
    for index, frame in enumerate(frames):
        if frame.shape[:2] != (height, width):
            raise VideoEvaluationError(
                f"{label} frame {index} has resolution "
                f"{frame.shape[1]}x{frame.shape[0]}, expected {width}x{height}."
            )

    return DecodedVideo(
        path=path,
        frames=frames,
        fps=_read_fps(metadata),
        width=width,
        height=height,
    )


def validate_video_pair(
    ground_truth: DecodedVideo,
    prediction: DecodedVideo,
    *,
    skip_context: int,
) -> None:
    """Validate that a video pair can be aligned without hidden truncation."""

    if skip_context >= ground_truth.frame_count:
        raise VideoEvaluationError(
            f"--skip-context {skip_context} leaves no ground-truth future frames; "
            f"ground truth has {ground_truth.frame_count} frame(s)."
        )
    if skip_context >= prediction.frame_count:
        raise VideoEvaluationError(
            f"--skip-context {skip_context} leaves no predicted future frames; "
            f"prediction has {prediction.frame_count} frame(s)."
        )

    gt_future = ground_truth.frame_count - skip_context
    pred_future = prediction.frame_count - skip_context
    if gt_future != pred_future:
        raise VideoEvaluationError(
            f"Prediction has {pred_future} future frame(s) after context removal. "
            f"Ground truth has {gt_future} future frame(s) after context removal. "
            "WorldBench requires matching future lengths."
        )

    if (ground_truth.width, ground_truth.height) != (
        prediction.width,
        prediction.height,
    ):
        raise VideoEvaluationError(
            "Prediction resolution differs from ground truth. "
            f"Prediction: {prediction.width}x{prediction.height}; "
            f"ground truth: {ground_truth.width}x{ground_truth.height}."
        )

    if ground_truth.fps is None and prediction.fps is not None:
        raise VideoEvaluationError(
            "Ground-truth FPS is unavailable but prediction FPS is present."
        )
    if ground_truth.fps is not None and prediction.fps is None:
        raise VideoEvaluationError(
            "Prediction FPS is unavailable but ground-truth FPS is present."
        )
    if ground_truth.fps is not None and prediction.fps is not None:
        tolerance = max(0.05, max(ground_truth.fps, prediction.fps) * 0.01)
        if abs(ground_truth.fps - prediction.fps) > tolerance:
            raise VideoEvaluationError(
                "Prediction FPS differs meaningfully from ground truth. "
                f"Prediction: {prediction.fps:.3f}; ground truth: {ground_truth.fps:.3f}."
            )


def collect_video_files(root: str | Path) -> dict[str, Path]:
    """Collect supported videos under a root keyed by relative POSIX path."""

    base = Path(root)
    return {
        path.relative_to(base).as_posix(): path
        for path in sorted(base.rglob("*"))
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    }


def _write_frames(frames: list[np.ndarray], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(frames):
        Image.fromarray(frame, mode="RGB").save(output_dir / f"{index:06d}.png")


def _as_rgb_uint8(frame: Any) -> np.ndarray:
    arr = np.asarray(frame)
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=2)
    if arr.ndim != 3 or arr.shape[2] not in {3, 4}:
        raise VideoEvaluationError(f"Unsupported frame shape: {arr.shape}")
    arr = arr[:, :, :3]
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    return arr


def _read_fps(metadata: dict[str, Any]) -> float | None:
    fps = metadata.get("fps") or metadata.get("framerate")
    if isinstance(fps, (int, float)) and float(fps) > 0:
        return float(fps)
    return None
