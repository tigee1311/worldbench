"""Video-pair evaluation adapters for WorldBench."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from pathlib import Path
import tempfile
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

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


@dataclass(frozen=True)
class AlignedVideoPair:
    ground_truth_frames: list[np.ndarray]
    prediction_frames: list[np.ndarray]
    warnings: list[str]
    details: dict[str, Any]


def evaluate_video_pair(
    ground_truth: str | Path,
    prediction: str | Path,
    *,
    skip_context: int = 0,
    name: str | None = None,
    config: WorldBenchConfig | None = None,
    alignment: str = "strict",
    max_frame_mismatch_ratio: float = 0.25,
    max_frame_mismatch_frames: int = 8,
) -> EvaluationResult:
    """Evaluate a ground-truth video against a predicted video."""

    gt_path = Path(ground_truth)
    pred_path = Path(prediction)
    if skip_context < 0:
        raise VideoEvaluationError("--skip-context must be non-negative.")

    gt_video = decode_video(gt_path, label="Ground truth")
    pred_video = decode_video(pred_path, label="Prediction")
    aligned = align_video_pair(
        gt_video,
        pred_video,
        skip_context=skip_context,
        alignment=alignment,
        max_frame_mismatch_ratio=max_frame_mismatch_ratio,
        max_frame_mismatch_frames=max_frame_mismatch_frames,
    )

    future_gt = aligned.ground_truth_frames
    future_pred = aligned.prediction_frames
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
        "alignment_policy": alignment,
        "alignment_method": aligned.details["alignment_method"],
        "alignment": aligned.details,
        "alignment_warnings": aligned.warnings,
        "warnings": aligned.warnings,
        "ground_truth_original_frame_count": gt_video.frame_count,
        "prediction_original_frame_count": pred_video.frame_count,
        "ground_truth_frame_count": gt_video.frame_count,
        "prediction_frame_count": pred_video.frame_count,
        "evaluated_frame_count": len(future_gt),
        "evaluated_ground_truth_frames": len(future_gt),
        "evaluated_prediction_frames": len(future_pred),
        "ground_truth_frames_trimmed": aligned.details["ground_truth_frames_trimmed"],
        "prediction_frames_trimmed": aligned.details["prediction_frames_trimmed"],
        "ground_truth_context_frames_skipped": skip_context,
        "prediction_context_frames_skipped": skip_context,
        "ground_truth_original_resolution": aligned.details[
            "ground_truth_original_resolution"
        ],
        "prediction_original_resolution": aligned.details[
            "prediction_original_resolution"
        ],
        "evaluated_resolution": aligned.details["evaluated_resolution"],
        "resizing_occurred": aligned.details["resizing_occurred"],
        "ground_truth_original_fps": gt_video.fps,
        "prediction_original_fps": pred_video.fps,
        "fps_differed": aligned.details["fps_differed"],
        "fps": gt_video.fps,
        "prediction_fps": pred_video.fps,
        "resolution": aligned.details["evaluated_resolution"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if aligned.warnings:
        result.issues = list(dict.fromkeys([*aligned.warnings, *result.issues]))
    return result


def decode_video(path: Path, *, label: str) -> DecodedVideo:
    """Decode a video into RGB uint8 frames and basic metadata."""

    if not path.exists():
        raise VideoEvaluationError(f"{label} video does not exist: {path}")
    if not path.is_file():
        raise VideoEvaluationError(f"{label} path is not a file: {path}")
    if path.suffix.lower() not in VIDEO_EXTENSIONS:
        supported = ", ".join(sorted(VIDEO_EXTENSIONS))
        raise VideoEvaluationError(
            f"{label} video has unsupported extension '{path.suffix}'. "
            f"Supported video extensions: {supported}."
        )

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


def align_video_pair(
    ground_truth: DecodedVideo,
    prediction: DecodedVideo,
    *,
    skip_context: int,
    alignment: str = "strict",
    max_frame_mismatch_ratio: float = 0.25,
    max_frame_mismatch_frames: int = 8,
) -> AlignedVideoPair:
    """Return future frames aligned under the requested policy."""

    if alignment not in {"strict", "safe"}:
        raise VideoEvaluationError("alignment must be either 'strict' or 'safe'.")
    if max_frame_mismatch_ratio < 0:
        raise VideoEvaluationError("max_frame_mismatch_ratio must be non-negative.")
    if max_frame_mismatch_frames < 0:
        raise VideoEvaluationError("max_frame_mismatch_frames must be non-negative.")

    if alignment == "strict":
        validate_video_pair(ground_truth, prediction, skip_context=skip_context)
        future_gt = ground_truth.frames[skip_context:]
        future_pred = prediction.frames[skip_context:]
        return AlignedVideoPair(
            ground_truth_frames=future_gt,
            prediction_frames=future_pred,
            warnings=[],
            details={
                "mode": "strict",
                "alignment_method": "strict_frame_index_alignment",
                "frame_alignment": "all_future_frames",
                "resolution_policy": "exact_match",
                "fps_policy": "exact_with_tolerance",
                "frame_count_policy": "exact_match_after_context",
                "ground_truth_original_frame_count": ground_truth.frame_count,
                "prediction_original_frame_count": prediction.frame_count,
                "ground_truth_future_frame_count": len(future_gt),
                "prediction_future_frame_count": len(future_pred),
                "ground_truth_frames_trimmed": 0,
                "prediction_frames_trimmed": 0,
                "evaluated_frame_count": len(future_gt),
                "ground_truth_original_resolution": (
                    f"{ground_truth.width}x{ground_truth.height}"
                ),
                "prediction_original_resolution": (
                    f"{prediction.width}x{prediction.height}"
                ),
                "evaluated_resolution": f"{ground_truth.width}x{ground_truth.height}",
                "resizing_occurred": False,
                "ground_truth_original_fps": ground_truth.fps,
                "prediction_original_fps": prediction.fps,
                "fps_differed": False,
            },
        )

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

    gt_future_count = ground_truth.frame_count - skip_context
    pred_future_count = prediction.frame_count - skip_context
    common_count = min(gt_future_count, pred_future_count)
    if common_count <= 0:
        raise VideoEvaluationError(
            "No aligned future frames remain after context removal."
        )

    mismatch = abs(gt_future_count - pred_future_count)
    max_allowed = max(
        max_frame_mismatch_frames,
        int(
            math.ceil(
                max(gt_future_count, pred_future_count) * max_frame_mismatch_ratio
            )
        ),
    )
    warnings: list[str] = []
    if mismatch > max_allowed:
        raise VideoEvaluationError(
            "Frame-count mismatch is too large to align safely. "
            f"Ground-truth future frames: {gt_future_count}; "
            f"prediction future frames: {pred_future_count}; "
            f"maximum allowed mismatch: {max_allowed}. "
            "Provide videos with the same future horizon or adjust the advanced mismatch limit."
        )
    if mismatch:
        gt_trimmed = gt_future_count - common_count
        pred_trimmed = pred_future_count - common_count
        warnings.append(
            "Frame-count mismatch: scoring the common future-frame prefix only "
            f"({common_count} frame(s)); ground truth had {gt_future_count}, "
            f"prediction had {pred_future_count}. Removed {gt_trimmed} ground-truth "
            f"future frame(s) and {pred_trimmed} prediction future frame(s)."
        )
    else:
        gt_trimmed = 0
        pred_trimmed = 0

    future_gt = ground_truth.frames[skip_context : skip_context + common_count]
    future_pred = prediction.frames[skip_context : skip_context + common_count]

    resized_prediction = False
    if (ground_truth.width, ground_truth.height) != (
        prediction.width,
        prediction.height,
    ):
        future_pred = [
            _resize_rgb_frame(frame, ground_truth.width, ground_truth.height)
            for frame in future_pred
        ]
        resized_prediction = True
        warnings.append(
            "Prediction frames were resized from "
            f"{prediction.width}x{prediction.height} to "
            f"{ground_truth.width}x{ground_truth.height} before evaluation."
        )

    fps_mismatch = False
    if ground_truth.fps is None and prediction.fps is not None:
        warnings.append(
            "Ground-truth FPS metadata was unavailable; scoring uses frame index alignment."
        )
    elif ground_truth.fps is not None and prediction.fps is None:
        warnings.append(
            "Prediction FPS metadata was unavailable; scoring uses frame index alignment."
        )
    elif ground_truth.fps is not None and prediction.fps is not None:
        tolerance = max(0.05, max(ground_truth.fps, prediction.fps) * 0.01)
        if abs(ground_truth.fps - prediction.fps) > tolerance:
            fps_mismatch = True
            warnings.append(
                "FPS mismatch: scoring uses frame index alignment, not time resampling "
                f"(ground truth {ground_truth.fps:.3f} FPS, "
                f"prediction {prediction.fps:.3f} FPS)."
            )

    return AlignedVideoPair(
        ground_truth_frames=future_gt,
        prediction_frames=future_pred,
        warnings=warnings,
        details={
            "mode": "safe",
            "alignment_method": "safe_common_future_prefix_frame_index_alignment",
            "frame_alignment": "common_future_prefix",
            "frame_count_policy": "trim_common_prefix_with_major_mismatch_rejection",
            "resolution_policy": "resize_prediction_to_ground_truth",
            "fps_policy": "frame_index_alignment_with_warning",
            "ground_truth_original_frame_count": ground_truth.frame_count,
            "prediction_original_frame_count": prediction.frame_count,
            "ground_truth_future_frame_count": gt_future_count,
            "prediction_future_frame_count": pred_future_count,
            "frame_count_mismatch": mismatch,
            "max_allowed_frame_count_mismatch": max_allowed,
            "ground_truth_frames_trimmed": gt_trimmed,
            "prediction_frames_trimmed": pred_trimmed,
            "evaluated_frame_count": common_count,
            "resizing_occurred": resized_prediction,
            "resized_prediction": resized_prediction,
            "fps_differed": fps_mismatch,
            "fps_mismatch": fps_mismatch,
            "ground_truth_original_resolution": (
                f"{ground_truth.width}x{ground_truth.height}"
            ),
            "prediction_original_resolution": (
                f"{prediction.width}x{prediction.height}"
            ),
            "evaluated_resolution": f"{ground_truth.width}x{ground_truth.height}",
            "ground_truth_original_fps": ground_truth.fps,
            "prediction_original_fps": prediction.fps,
        },
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


def save_comparison_artifacts(
    ground_truth: str | Path,
    prediction: str | Path,
    output_dir: str | Path,
    *,
    skip_context: int = 0,
    alignment: str = "safe",
    max_frame_mismatch_ratio: float = 0.25,
    max_frame_mismatch_frames: int = 8,
    max_frames: int = 8,
) -> dict[str, Path]:
    """Save small human-inspection artifacts for a video pair."""

    gt_video = decode_video(Path(ground_truth), label="Ground truth")
    pred_video = decode_video(Path(prediction), label="Prediction")
    aligned = align_video_pair(
        gt_video,
        pred_video,
        skip_context=skip_context,
        alignment=alignment,
        max_frame_mismatch_ratio=max_frame_mismatch_ratio,
        max_frame_mismatch_frames=max_frame_mismatch_frames,
    )
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    contact_sheet = output / "comparison.png"
    _write_contact_sheet(
        aligned.ground_truth_frames,
        aligned.prediction_frames,
        contact_sheet,
        max_frames=max_frames,
    )
    return {"comparison_png": contact_sheet}


def create_saved_video_demo_pair(output_dir: str | Path) -> tuple[Path, Path]:
    """Create a tiny deterministic MP4 pair for quick local demos."""

    try:
        import imageio.v2 as imageio
    except ImportError as exc:  # pragma: no cover - exercised only without extras
        raise VideoEvaluationError(
            "The saved-video demo requires the optional video dependencies. "
            "Install WorldBench with the video extra."
        ) from exc

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    ground_truth = output / "ground_truth.mp4"
    prediction = output / "predicted_future.mp4"
    frames = [_demo_frame(index, delta=0) for index in range(8)]
    predicted = [_demo_frame(index, delta=6 if index >= 3 else 2) for index in range(8)]
    imageio.mimwrite(ground_truth, frames, fps=6, macro_block_size=1)
    imageio.mimwrite(prediction, predicted, fps=6, macro_block_size=1)
    return ground_truth, prediction


def _resize_rgb_frame(frame: np.ndarray, width: int, height: int) -> np.ndarray:
    image = Image.fromarray(frame, mode="RGB")
    resampling = getattr(Image, "Resampling", Image).BILINEAR
    return np.asarray(image.resize((width, height), resampling), dtype=np.uint8)


def _write_contact_sheet(
    ground_truth_frames: list[np.ndarray],
    prediction_frames: list[np.ndarray],
    output_path: Path,
    *,
    max_frames: int,
) -> None:
    if not ground_truth_frames or not prediction_frames:
        raise VideoEvaluationError("No aligned frames are available for comparison.")

    count = min(len(ground_truth_frames), len(prediction_frames), max_frames)
    if count <= 0:
        raise VideoEvaluationError("No aligned frames are available for comparison.")
    indices = np.linspace(
        0, min(len(ground_truth_frames), len(prediction_frames)) - 1, count
    )
    selected = [int(round(index)) for index in indices]
    height, width = ground_truth_frames[0].shape[:2]
    label_height = 18
    gap = 4
    sheet = Image.new(
        "RGB",
        (width * 2 + gap, (height + label_height) * count),
        color=(245, 245, 245),
    )
    for row, index in enumerate(selected):
        y = row * (height + label_height)
        ref = Image.fromarray(ground_truth_frames[index], mode="RGB")
        pred = Image.fromarray(prediction_frames[index], mode="RGB")
        draw = ImageDraw.Draw(sheet)
        draw.text((2, y + 2), "Ground truth", fill=(20, 20, 20))
        draw.text((width + gap + 2, y + 2), "Prediction", fill=(20, 20, 20))
        sheet.paste(ref, (0, y + label_height))
        sheet.paste(pred, (width + gap, y + label_height))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def _demo_frame(index: int, *, delta: int) -> np.ndarray:
    width, height = 48, 32
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, :, 0] = np.clip(35 + index * 9 + delta, 0, 255)
    frame[:, :, 1] = np.clip(70 + index * 5 + delta, 0, 255)
    frame[:, :, 2] = np.clip(110 + index * 3 + delta, 0, 255)
    x0 = 5 + index
    frame[9:17, x0 : x0 + 8, :] = np.clip([190 + delta, 45, 45], 0, 255)
    frame[18:25, 30:38, :] = np.clip([40, 160 + delta, 80], 0, 255)
    return frame


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
