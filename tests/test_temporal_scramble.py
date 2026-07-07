from __future__ import annotations

from pathlib import Path

from PIL import Image
import pytest

from worldbench.backends.frame_scramble import scramble_frames, scramble_rollout_predictions


def _make_source_frames(root: Path, count: int = 31) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for idx in range(count):
        image = Image.new("RGB", (8, 8), (idx * 7 % 255, idx * 13 % 255, idx * 19 % 255))
        image.save(root / f"{idx:06d}.png")
    return root


def _load_bytes(path: Path) -> bytes:
    return path.read_bytes()


def test_scramble_zero_percent_preserves_source_and_filenames(tmp_path: Path) -> None:
    source = _make_source_frames(tmp_path / "source")
    original = {path.name: path.read_bytes() for path in source.iterdir()}

    result = scramble_frames(source, tmp_path / "out", severity=0.0, seed=42)

    assert result.source_frames == 31
    assert result.moved_frames == 0
    assert result.moved_positions == []
    assert [path.name for path in result.output_paths] == sorted(original)
    assert {path.name: path.read_bytes() for path in source.iterdir()} == original
    assert all((tmp_path / "out" / name).read_bytes() == data for name, data in original.items())


def test_scramble_higher_severity_moves_more_frames(tmp_path: Path) -> None:
    source = _make_source_frames(tmp_path / "source")

    low = scramble_frames(source, tmp_path / "low", severity=0.05, seed=42)
    mid = scramble_frames(source, tmp_path / "mid", severity=0.15, seed=42)
    high = scramble_frames(source, tmp_path / "high", severity=0.30, seed=42)

    assert low.moved_frames < mid.moved_frames < high.moved_frames
    assert low.moved_frame_percentage < mid.moved_frame_percentage < high.moved_frame_percentage
    assert low.output_paths[0].name == "000000.png"


def test_scramble_is_deterministic_and_constant_length(tmp_path: Path) -> None:
    source = _make_source_frames(tmp_path / "source")

    first = scramble_frames(source, tmp_path / "first", severity=0.2, seed=7)
    second = scramble_frames(source, tmp_path / "second", severity=0.2, seed=7)

    assert len(first.output_paths) == len(second.output_paths) == 31
    assert [path.name for path in first.output_paths] == [path.name for path in second.output_paths]
    assert [path.read_bytes() for path in first.output_paths] == [path.read_bytes() for path in second.output_paths]


def test_scramble_invalid_severity_raises(tmp_path: Path) -> None:
    source = _make_source_frames(tmp_path / "source")

    with pytest.raises(ValueError, match="between 0 and 1"):
        scramble_frames(source, tmp_path / "out", severity=-0.1)
    with pytest.raises(ValueError, match="between 0 and 1"):
        scramble_frames(source, tmp_path / "out", severity=1.1)


def test_scramble_changes_order_without_editing_source(tmp_path: Path) -> None:
    source = _make_source_frames(tmp_path / "source")
    before = {path.name: _load_bytes(path) for path in source.iterdir()}

    result = scramble_frames(source, tmp_path / "scrambled", severity=0.3, seed=42)

    assert result.moved_frames > 0
    assert any(
        (tmp_path / "scrambled" / f"{idx:06d}.png").read_bytes() != before[f"{idx:06d}.png"]
        for idx in result.moved_positions[:3]
    )
    assert {path.name: _load_bytes(path) for path in source.iterdir()} == before
    assert result.output_paths[0].name == "000000.png"


def test_scramble_rollout_predictions_writes_prediction_layout(tmp_path: Path) -> None:
    source = tmp_path / "dataset"
    _make_source_frames(source / "episode_000000" / "frames")

    results = scramble_rollout_predictions(source, tmp_path / "predictions", severity=0.2, seed=3)

    assert len(results) == 1
    assert (tmp_path / "predictions" / "episode_000000" / "predictions" / "000000.png").exists()
