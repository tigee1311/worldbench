"""Deterministic WorldBench performance and memory benchmark harness."""

from __future__ import annotations

import argparse
import json
import platform
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any, Callable

import imageio.v2 as imageio
import numpy as np

from worldbench.runners.regression import evaluate_video_batch
from worldbench.runners.video import evaluate_video_pair, save_comparison_artifacts
from worldbench.version import WORLD_BENCH_VERSION


def run_benchmarks(*, quick: bool = False) -> dict[str, Any]:
    cases = [
        ("short_64", 8, (64, 64)),
        ("short_256", 6 if quick else 8, (256, 256)),
        ("long_64", 24 if quick else 96, (64, 64)),
    ]
    payload: dict[str, Any] = {
        "status": "informational",
        "strict_timing_gate": False,
        "environment": _environment(),
        "cases": {},
    }
    with tempfile.TemporaryDirectory(prefix="worldbench-perf-") as tmpdir:
        root = Path(tmpdir)
        for name, frame_count, size in cases:
            gt = root / f"{name}_ground_truth.mp4"
            pred = root / f"{name}_prediction.mp4"
            _write_video(gt, _frames(frame_count, size=size))
            _write_video(pred, _frames(frame_count, size=size, delta=3))
            result, timing = _measure(
                lambda gt_path=gt, pred_path=pred: evaluate_video_pair(
                    gt_path, pred_path, alignment="safe"
                )
            )
            payload["cases"][name] = {
                **timing,
                "frame_count": frame_count,
                "resolution": f"{size[0]}x{size[1]}",
                "frames_per_second": round(
                    frame_count / max(timing["wall_time_seconds"], 1e-9), 2
                ),
                "score": round(float(result.score), 4),
            }

        batch_gt = root / "batch_gt"
        batch_pred = root / "batch_pred"
        for idx in range(3 if quick else 5):
            episode_name = f"episode_{idx:03d}.mp4"
            _write_video(batch_gt / episode_name, _frames(8, size=(64, 64), delta=idx))
            _write_video(
                batch_pred / episode_name, _frames(8, size=(64, 64), delta=idx + 2)
            )
        batch_result, timing = _measure(
            lambda: evaluate_video_batch(
                batch_gt,
                batch_pred,
                name="candidate",
                output_root=root / "batch_outputs",
                output=root / "candidate.json",
            )
        )
        payload["cases"]["batch_episode_evaluation"] = {
            **timing,
            "episode_count": batch_result[0]["episode_count"],
        }

        result_json = root / "serialization.json"
        evaluation = evaluate_video_pair(
            root / "short_64_ground_truth.mp4",
            root / "short_64_prediction.mp4",
            alignment="safe",
        )
        _, timing = _measure(lambda: evaluation.save_json(result_json))
        payload["cases"]["result_serialization"] = timing

        _, timing = _measure(
            lambda: save_comparison_artifacts(
                root / "short_64_ground_truth.mp4",
                root / "short_64_prediction.mp4",
                root / "comparison",
            )
        )
        payload["cases"]["comparison_image_generation"] = timing
    return payload


def write_report(payload: dict[str, Any], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/performance/latest.json"),
    )
    args = parser.parse_args()
    output = write_report(run_benchmarks(quick=args.quick), args.output)
    print(f"Wrote {output}")


def _measure(func: Callable[[], Any]) -> tuple[Any, dict[str, Any]]:
    tracemalloc.start()
    start = time.perf_counter()
    result = func()
    wall_time = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, {
        "wall_time_seconds": round(wall_time, 6),
        "peak_tracemalloc_mb": round(peak / (1024 * 1024), 3),
    }


def _environment() -> dict[str, str]:
    return {
        "worldbench_version": WORLD_BENCH_VERSION,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
    }


def _frames(count: int, *, size: tuple[int, int], delta: int = 0) -> list[np.ndarray]:
    width, height = size
    frames: list[np.ndarray] = []
    for index in range(count):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :, 0] = np.clip(40 + index * 3 + delta, 0, 255)
        frame[:, :, 1] = np.clip(70 + index * 2 + delta, 0, 255)
        frame[:, :, 2] = 110
        x = min(width - 10, 4 + index * max(1, width // (count + 3)))
        y = height // 2 - 5
        frame[y : y + 10, x : x + 10, :] = np.array([35, 210, 80], dtype=np.uint8)
        frames.append(frame)
    return frames


def _write_video(path: Path, frames: list[np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimwrite(path, frames, fps=6, macro_block_size=1)


if __name__ == "__main__":
    main()
