"""Shared filesystem, image, and scoring helpers."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return float(max(low, min(high, value)))


def ensure_dir(path: str | Path) -> Path:
    output = Path(path)
    output.mkdir(parents=True, exist_ok=True)
    return output


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, data: Any) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
    return output


def list_image_files(path: str | Path) -> list[Path]:
    root = Path(path)
    if not root.exists() or not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS and p.is_file())


def load_rgb(path: str | Path, size: tuple[int, int] | None = None) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    if size is not None and image.size != size:
        image = image.resize(size)
    return np.asarray(image, dtype=np.float32)


def load_aligned_pairs(ground_truth: Iterable[Path], predictions: Iterable[Path]) -> list[tuple[np.ndarray, np.ndarray]]:
    pairs: list[tuple[np.ndarray, np.ndarray]] = []
    for gt_path, pred_path in zip(ground_truth, predictions):
        gt = load_rgb(gt_path)
        pred = load_rgb(pred_path, size=(gt.shape[1], gt.shape[0]))
        pairs.append((gt, pred))
    return pairs


def centroid_from_mask(mask: np.ndarray) -> tuple[float, float] | None:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return float(np.mean(xs)), float(np.mean(ys))


def detect_robot_centroid(image: np.ndarray) -> tuple[float, float] | None:
    """Detect the demo robot marker, falling back to a saturated foreground blob."""

    red_mask = (image[..., 0] > 150) & (image[..., 1] < 130) & (image[..., 2] < 130)
    centroid = centroid_from_mask(red_mask)
    if centroid is not None:
        return centroid

    saturation = image.max(axis=2) - image.min(axis=2)
    bright = image.mean(axis=2)
    mask = (saturation > 50) & (bright > 60)
    return centroid_from_mask(mask)


def detect_object_centroid(image: np.ndarray) -> tuple[float, float] | None:
    """Detect the demo object marker, falling back to a non-robot foreground blob."""

    green_mask = _green_object_mask(image)
    centroid = centroid_from_mask(green_mask)
    if centroid is not None:
        return centroid

    blue_mask = (image[..., 2] > 140) & (image[..., 0] < 160) & (image[..., 1] < 180)
    centroid = centroid_from_mask(blue_mask)
    if centroid is not None:
        return centroid

    saturation = image.max(axis=2) - image.min(axis=2)
    bright = image.mean(axis=2)
    mask = (saturation > 50) & (bright > 60)
    robot = detect_robot_centroid(image)
    if robot is None:
        return centroid_from_mask(mask)

    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    distances = np.sqrt((xs - robot[0]) ** 2 + (ys - robot[1]) ** 2)
    object_mask = np.zeros(mask.shape, dtype=bool)
    object_mask[ys[distances > 12], xs[distances > 12]] = True
    return centroid_from_mask(object_mask)


def object_area(image: np.ndarray) -> int:
    return int(_green_object_mask(image).sum())


def _green_object_mask(image: np.ndarray) -> np.ndarray:
    """Detect green cube/object pixels while ignoring gray-blue labels and UI text."""

    return (
        (image[..., 1] > 120)
        & (image[..., 1] > image[..., 0] + 30)
        & (image[..., 1] > image[..., 2] + 10)
    )


def vector_norm(dx: float, dy: float) -> float:
    return float(math.sqrt(dx * dx + dy * dy))


def cosine_similarity(a: tuple[float, float], b: tuple[float, float]) -> float:
    denom = vector_norm(*a) * vector_norm(*b)
    if denom == 0:
        return 0.0
    return float((a[0] * b[0] + a[1] * b[1]) / denom)


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header, separator, *body])
