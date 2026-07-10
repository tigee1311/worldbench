from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from worldbench.backends.frame_freeze import freeze_frames, freeze_rollout_predictions


def _make_source_frames(root: Path, count: int = 6) -> Path:
    frames = root
    frames.mkdir(parents=True, exist_ok=True)
    for idx in range(count):
        image = Image.new(
            "RGB", (8, 8), (idx * 30 % 255, idx * 50 % 255, idx * 70 % 255)
        )
        image.save(frames / f"{idx:06d}.png")
    return frames


def _load_rgb(path: Path) -> list[tuple[int, int, int]]:
    with Image.open(path) as image:
        return [
            tuple(pixel) for pixel in np.asarray(image.convert("RGB")).reshape(-1, 3)
        ]


def test_freeze_frames_zero_percent_preserves_source_and_filenames(
    tmp_path: Path,
) -> None:
    source = _make_source_frames(tmp_path / "source" / "frames")
    original = {path.name: path.read_bytes() for path in source.iterdir()}

    result = freeze_frames(source, tmp_path / "out", severity=0.0, seed=42)

    assert result.source_frames == 6
    assert result.frozen_frames == 0
    assert [path.name for path in result.output_paths] == sorted(original)
    assert all(
        (tmp_path / "out" / name).read_bytes() == data
        for name, data in original.items()
    )
    assert {path.name: path.read_bytes() for path in source.iterdir()} == original


def test_freeze_frames_higher_severity_freezes_more_frames(tmp_path: Path) -> None:
    source = _make_source_frames(tmp_path / "source" / "frames")

    low = freeze_frames(source, tmp_path / "low", severity=0.05, seed=42)
    high = freeze_frames(source, tmp_path / "high", severity=0.5, seed=42)

    assert low.frozen_frames < high.frozen_frames
    assert low.output_paths[0].name == "000000.png"
    assert high.output_paths[0].name == "000000.png"
    assert _load_rgb(high.output_paths[0]) == _load_rgb(source / "000000.png")


def test_freeze_frames_deterministic_and_constant_length(tmp_path: Path) -> None:
    source = _make_source_frames(tmp_path / "source" / "frames")

    first = freeze_frames(source, tmp_path / "first", severity=0.3, seed=7)
    second = freeze_frames(source, tmp_path / "second", severity=0.3, seed=7)

    assert len(first.output_paths) == len(second.output_paths) == 6
    assert [path.name for path in first.output_paths] == [
        path.name for path in second.output_paths
    ]
    assert [path.read_bytes() for path in first.output_paths] == [
        path.read_bytes() for path in second.output_paths
    ]


def test_freeze_frames_invalid_severity_raises(tmp_path: Path) -> None:
    source = _make_source_frames(tmp_path / "source" / "frames")

    with pytest.raises(ValueError, match="between 0 and 1"):
        freeze_frames(source, tmp_path / "out", severity=-0.1)
    with pytest.raises(ValueError, match="between 0 and 1"):
        freeze_frames(source, tmp_path / "out", severity=1.1)


def test_freeze_rollout_predictions_writes_prediction_layout(tmp_path: Path) -> None:
    source = tmp_path / "dataset"
    _make_source_frames(source / "episode_000000" / "frames")
    results = freeze_rollout_predictions(
        source, tmp_path / "predictions", severity=0.2, seed=3
    )

    assert len(results) == 1
    assert (
        tmp_path / "predictions" / "episode_000000" / "predictions" / "000000.png"
    ).exists()
