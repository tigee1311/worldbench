"""Research-only corruption harness for candidate video metrics."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
from PIL import Image, ImageFilter

FrameMetric = Callable[[np.ndarray, np.ndarray], float | None]


def current_visual_similarity(reference: np.ndarray, prediction: np.ndarray) -> float:
    return _clamp(
        100.0 - float(np.mean(np.abs(reference - prediction))) / 255.0 * 100.0
    )


def temporal_motion_similarity(
    reference: np.ndarray, prediction: np.ndarray
) -> float | None:
    if len(reference) < 2 or len(prediction) < 2:
        return None
    ref_motion = np.diff(reference, axis=0)
    pred_motion = np.diff(prediction, axis=0)
    return _clamp(
        100.0 - float(np.mean(np.abs(ref_motion - pred_motion))) / 255.0 * 100.0
    )


def frame_difference_trajectory_similarity(
    reference: np.ndarray, prediction: np.ndarray
) -> float | None:
    if len(reference) < 2 or len(prediction) < 2:
        return None
    ref_energy = np.mean(np.abs(np.diff(reference, axis=0)), axis=(1, 2, 3))
    pred_energy = np.mean(np.abs(np.diff(prediction, axis=0)), axis=(1, 2, 3))
    scale = max(float(np.max(ref_energy)), 1.0)
    return _clamp(
        100.0 - float(np.mean(np.abs(ref_energy - pred_energy))) / scale * 100.0
    )


def object_track_displacement_similarity(
    reference: np.ndarray, prediction: np.ndarray
) -> float | None:
    ref_track = _track_green_object(reference)
    pred_track = _track_green_object(prediction)
    if ref_track is None or pred_track is None:
        return None
    distances = np.linalg.norm(ref_track - pred_track, axis=1)
    diagonal = float(np.hypot(reference.shape[2], reference.shape[1]))
    return _clamp(100.0 - float(np.mean(distances)) / diagonal * 100.0)


METRICS: dict[str, FrameMetric] = {
    "current_visual_similarity": current_visual_similarity,
    "temporal_motion_similarity": temporal_motion_similarity,
    "frame_difference_trajectory_similarity": frame_difference_trajectory_similarity,
    "object_track_displacement_similarity": object_track_displacement_similarity,
}


def run_harness(
    *,
    severities: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0),
    repeats: int = 3,
    frame_count: int = 12,
    size: tuple[int, int] = (64, 64),
) -> dict[str, Any]:
    reference = _synthetic_video(frame_count=frame_count, size=size)
    corruptions = {
        "frame_freeze": _corrupt_freeze,
        "temporal_scramble": _corrupt_scramble,
        "blur": _corrupt_blur,
        "dropped_frames": _corrupt_drop_frames,
        "speed_changes": _corrupt_speed,
        "spatial_shifts": _corrupt_shift,
    }
    report: dict[str, Any] = {
        "status": "research_only",
        "production_metrics_changed": False,
        "severities": list(severities),
        "repeats": repeats,
        "metrics": {},
        "corruptions": {},
    }
    metric_runtimes: dict[str, list[float]] = {name: [] for name in METRICS}
    for corruption_name, corruption in corruptions.items():
        corruption_payload: dict[str, Any] = {}
        for metric_name, metric in METRICS.items():
            scores: list[float | None] = []
            for severity in severities:
                repeated_scores: list[float] = []
                for repeat in range(repeats):
                    prediction = corruption(reference, severity, seed=repeat)
                    start = time.perf_counter()
                    score = metric(reference, prediction)
                    metric_runtimes[metric_name].append(time.perf_counter() - start)
                    if score is not None:
                        repeated_scores.append(float(score))
                scores.append(
                    round(float(np.mean(repeated_scores)), 4)
                    if repeated_scores
                    else None
                )
            available_scores = [score for score in scores if score is not None]
            corruption_payload[metric_name] = {
                "scores": scores,
                "monotonic_under_severity": _monotonic_nonincreasing(available_scores),
                "sensitivity": round(available_scores[0] - available_scores[-1], 4)
                if len(available_scores) >= 2
                else None,
            }
        report["corruptions"][corruption_name] = corruption_payload
    for metric_name, runtimes in metric_runtimes.items():
        report["metrics"][metric_name] = {
            "mean_runtime_ms": round(float(np.mean(runtimes)) * 1000.0, 4)
            if runtimes
            else None,
            "practical_on_cpu": bool(not runtimes or np.mean(runtimes) < 0.25),
            "likely_multimodal_future_risk": metric_name
            in {
                "current_visual_similarity",
                "object_track_displacement_similarity",
            },
        }
    return report


def write_report(payload: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "corruption_harness.json"
    markdown_path = output_dir / "corruption_harness.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(_markdown(payload), encoding="utf-8")
    return json_path, markdown_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/metric_research"),
        help="Directory for small research artifacts.",
    )
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    payload = run_harness(repeats=args.repeats)
    json_path, markdown_path = write_report(payload, args.output_dir)
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")


def _synthetic_video(*, frame_count: int, size: tuple[int, int]) -> np.ndarray:
    width, height = size
    video = np.zeros((frame_count, height, width, 3), dtype=np.float32)
    for idx in range(frame_count):
        video[idx, :, :, 0] = 32 + idx * 4
        video[idx, :, :, 1] = 45
        video[idx, :, :, 2] = 76
        x = min(width - 10, 4 + idx * max(1, width // (frame_count + 3)))
        y = height // 2 - 4
        video[idx, y : y + 8, x : x + 8, :] = np.array([30, 210, 80])
    return video


def _corrupt_freeze(video: np.ndarray, severity: float, *, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    corrupted = video.copy()
    for idx in range(1, len(corrupted)):
        if rng.random() < severity:
            corrupted[idx] = corrupted[idx - 1]
    return corrupted


def _corrupt_scramble(video: np.ndarray, severity: float, *, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    corrupted = video.copy()
    count = int(round((len(video) - 1) * severity))
    indices = np.arange(1, len(video))
    rng.shuffle(indices)
    selected = sorted(indices[:count])
    corrupted[selected] = corrupted[list(reversed(selected))]
    return corrupted


def _corrupt_blur(video: np.ndarray, severity: float, *, seed: int) -> np.ndarray:
    del seed
    radius = max(0.0, severity * 3.0)
    return np.stack(
        [
            np.asarray(
                Image.fromarray(frame.astype(np.uint8)).filter(
                    ImageFilter.GaussianBlur(radius=radius)
                ),
                dtype=np.float32,
            )
            for frame in video
        ]
    )


def _corrupt_drop_frames(
    video: np.ndarray, severity: float, *, seed: int
) -> np.ndarray:
    del seed
    corrupted = video.copy()
    if severity <= 0:
        return corrupted
    step = max(2, int(round(1.0 / max(severity, 0.05))))
    for idx in range(step, len(corrupted), step):
        corrupted[idx] = corrupted[idx - 1]
    return corrupted


def _corrupt_speed(video: np.ndarray, severity: float, *, seed: int) -> np.ndarray:
    del seed
    if severity <= 0:
        return video.copy()
    indices = np.linspace(0, len(video) - 1, len(video))
    shifted = np.clip(indices * (1.0 + severity * 0.6), 0, len(video) - 1)
    return video[np.rint(shifted).astype(int)].copy()


def _corrupt_shift(video: np.ndarray, severity: float, *, seed: int) -> np.ndarray:
    del seed
    shift = int(round(severity * 8))
    return np.roll(video, shift=shift, axis=2)


def _track_green_object(video: np.ndarray) -> np.ndarray | None:
    points: list[tuple[float, float]] = []
    for frame in video:
        mask = (
            (frame[:, :, 1] > 140)
            & (frame[:, :, 1] > frame[:, :, 0] + 60)
            & (frame[:, :, 1] > frame[:, :, 2] + 40)
        )
        ys, xs = np.nonzero(mask)
        if len(xs) == 0:
            return None
        points.append((float(np.mean(xs)), float(np.mean(ys))))
    return np.asarray(points, dtype=np.float32)


def _monotonic_nonincreasing(values: list[float], *, tolerance: float = 0.5) -> bool:
    return all(
        next_value <= value + tolerance
        for value, next_value in zip(values, values[1:], strict=False)
    )


def _clamp(value: float) -> float:
    return float(max(0.0, min(100.0, value)))


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Metric Research Corruption Harness",
        "",
        "Status: research only. Production metrics were not changed.",
        "",
        "## Metric Runtime",
        "",
        "| Metric | Mean runtime ms | Practical on CPU | Multimodal-future risk |",
        "| --- | ---: | --- | --- |",
    ]
    for name, details in payload["metrics"].items():
        lines.append(
            f"| {name} | {details['mean_runtime_ms']} | {details['practical_on_cpu']} | {details['likely_multimodal_future_risk']} |"
        )
    lines.extend(["", "## Corruption Sensitivity", ""])
    for corruption, metrics in payload["corruptions"].items():
        lines.extend(
            [
                f"### {corruption}",
                "",
                "| Metric | Monotonic | Sensitivity | Scores |",
                "| --- | --- | ---: | --- |",
            ]
        )
        for name, details in metrics.items():
            lines.append(
                f"| {name} | {details['monotonic_under_severity']} | {details['sensitivity']} | {details['scores']} |"
            )
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
