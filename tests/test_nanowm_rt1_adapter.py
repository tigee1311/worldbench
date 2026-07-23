from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import socket
import sys
from typing import Any

import imageio.v2 as imageio
import numpy as np
from PIL import Image
import pytest

from worldbench.utils import read_json


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "nanowm_rt1"
    / "prepare_worldbench_inputs.py"
)
SPEC = importlib.util.spec_from_file_location("nanowm_rt1_adapter", MODULE_PATH)
assert SPEC is not None
adapter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["nanowm_rt1_adapter"] = adapter
SPEC.loader.exec_module(adapter)


def test_single_episode_frame_preparation(tmp_path: Path) -> None:
    gt = _frame_dir(tmp_path / "gt", frame_count=3)
    baseline = _frame_dir(tmp_path / "baseline", frame_count=3, delta=4)
    output = tmp_path / "prepared"

    manifest = _prepare(
        tmp_path,
        ground_truth=gt,
        baseline=baseline,
        output_dir=output,
        episode_ids=["episode_000"],
    )

    assert manifest["episodes"][0]["episode_id"] == "episode_000"
    assert (output / "ground_truth" / "episode_000.mp4").exists()
    assert (output / "baseline" / "episode_000.mp4").exists()
    assert manifest["candidate_directory"] is None
    assert read_json(output / "manifest.json")["adapter"] == adapter.ADAPTER_NAME


def test_baseline_and_candidate_preparation(tmp_path: Path) -> None:
    gt = _episode_tree(tmp_path / "gt", ["episode_001"])
    baseline = _episode_tree(tmp_path / "baseline", ["episode_001"], delta=3)
    candidate = _episode_tree(tmp_path / "candidate", ["episode_001"], delta=1)
    output = tmp_path / "prepared"

    manifest = _prepare(
        tmp_path,
        ground_truth=gt,
        baseline=baseline,
        candidate=candidate,
        output_dir=output,
    )

    assert manifest["candidate_checkpoint"] == "nanowm-300k"
    assert (output / "candidate" / "episode_001.mp4").exists()
    assert manifest["episodes"][0]["prediction_frames"] == 2


def test_deterministic_episode_ordering(tmp_path: Path) -> None:
    gt = _episode_tree(tmp_path / "gt", ["episode_b", "episode_a"])
    baseline = _episode_tree(tmp_path / "baseline", ["episode_b", "episode_a"], delta=2)

    manifest = _prepare(
        tmp_path,
        ground_truth=gt,
        baseline=baseline,
        output_dir=tmp_path / "prepared",
    )

    assert [item["episode_id"] for item in manifest["episodes"]] == [
        "episode_a",
        "episode_b",
    ]


def test_missing_ground_truth_rejected(tmp_path: Path) -> None:
    baseline = _frame_dir(tmp_path / "baseline")

    with pytest.raises(adapter.AdapterError, match="Ground truth path does not exist"):
        _prepare(
            tmp_path,
            ground_truth=tmp_path / "missing",
            baseline=baseline,
            output_dir=tmp_path / "prepared",
            episode_ids=["episode_000"],
        )


def test_missing_baseline_prediction_rejected(tmp_path: Path) -> None:
    gt = _episode_tree(tmp_path / "gt", ["episode_001", "episode_002"])
    baseline = _episode_tree(tmp_path / "baseline", ["episode_001"])

    with pytest.raises(adapter.AdapterError, match="missing baseline: episode_002"):
        _prepare(
            tmp_path, ground_truth=gt, baseline=baseline, output_dir=tmp_path / "out"
        )


def test_mismatched_episode_names_rejected(tmp_path: Path) -> None:
    gt = _episode_tree(tmp_path / "gt", ["episode_001"])
    baseline = _episode_tree(tmp_path / "baseline", ["episode_002"])

    with pytest.raises(adapter.AdapterError, match="episode_001"):
        _prepare(
            tmp_path, ground_truth=gt, baseline=baseline, output_dir=tmp_path / "out"
        )


def test_mismatched_frame_counts_rejected(tmp_path: Path) -> None:
    gt = _frame_dir(tmp_path / "gt", frame_count=3)
    baseline = _frame_dir(tmp_path / "baseline", frame_count=4)

    with pytest.raises(adapter.AdapterError, match="baseline episode_000"):
        _prepare(
            tmp_path,
            ground_truth=gt,
            baseline=baseline,
            output_dir=tmp_path / "out",
            episode_ids=["episode_000"],
        )


def test_mismatched_video_resolution_rejected(tmp_path: Path) -> None:
    gt = _frame_dir(tmp_path / "gt", size=(16, 12))
    baseline = _frame_dir(tmp_path / "baseline", size=(18, 12))

    with pytest.raises(adapter.AdapterError, match="resolution mismatch"):
        _prepare(
            tmp_path,
            ground_truth=gt,
            baseline=baseline,
            output_dir=tmp_path / "out",
            episode_ids=["episode_000"],
        )


def test_invalid_fps_metadata_rejected(tmp_path: Path) -> None:
    gt = _video(tmp_path / "gt.mp4", fps=3)
    baseline = _video(tmp_path / "baseline.mp4", fps=5, delta=2)

    with pytest.raises(adapter.AdapterError, match="FPS"):
        _prepare(
            tmp_path,
            ground_truth=gt,
            baseline=baseline,
            output_dir=tmp_path / "out",
            episode_ids=["episode_000.mp4"],
        )


def test_duplicate_episode_identifiers_rejected(tmp_path: Path) -> None:
    gt = _episode_tree(tmp_path / "gt", ["episode_001"])
    baseline = _episode_tree(tmp_path / "baseline", ["episode_001"])

    with pytest.raises(adapter.AdapterError, match="Duplicate episode identifiers"):
        _prepare(
            tmp_path,
            ground_truth=gt,
            baseline=baseline,
            output_dir=tmp_path / "out",
            episode_ids=["episode_001", "episode_001"],
        )


def test_empty_input_directory_rejected(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    baseline = _frame_dir(tmp_path / "baseline")

    with pytest.raises(adapter.AdapterError, match="No supported videos"):
        _prepare(
            tmp_path,
            ground_truth=empty,
            baseline=baseline,
            output_dir=tmp_path / "out",
            episode_ids=["episode_000"],
        )


def test_malformed_metadata_json_rejected(tmp_path: Path) -> None:
    gt = _frame_dir(tmp_path / "gt")
    baseline = _frame_dir(tmp_path / "baseline")
    metadata = tmp_path / "metadata.json"
    metadata.write_text("{not-json", encoding="utf-8")

    with pytest.raises(adapter.AdapterError, match="Could not parse metadata JSON"):
        _prepare(
            tmp_path,
            ground_truth=gt,
            baseline=baseline,
            output_dir=tmp_path / "out",
            metadata_json=metadata,
            episode_ids=["episode_000"],
        )


def test_manifest_creation_records_required_fields(tmp_path: Path) -> None:
    gt = _frame_dir(tmp_path / "gt")
    baseline = _frame_dir(tmp_path / "baseline", delta=2)
    output = tmp_path / "prepared"

    manifest = _prepare(
        tmp_path,
        ground_truth=gt,
        baseline=baseline,
        output_dir=output,
        episode_ids=["episode_000"],
    )

    assert manifest["schema_version"] == "1"
    assert manifest["dataset"] == "RT-1 / Fractal"
    assert manifest["baseline_checkpoint"] == "nanowm-50k"
    assert manifest["context_frames"] == 1
    assert manifest["prediction_frames"] == 2
    assert manifest["worldbench_version"] == "0.4.1"
    assert manifest["source_files"][0]["ground_truth"]["kind"] == "frames"


def test_source_files_remain_unchanged(tmp_path: Path) -> None:
    gt = _frame_dir(tmp_path / "gt")
    baseline = _frame_dir(tmp_path / "baseline", delta=2)
    before = _tree_hashes(tmp_path / "gt") | _tree_hashes(tmp_path / "baseline")

    _prepare(
        tmp_path,
        ground_truth=gt,
        baseline=baseline,
        output_dir=tmp_path / "prepared",
        episode_ids=["episode_000"],
    )

    after = _tree_hashes(tmp_path / "gt") | _tree_hashes(tmp_path / "baseline")
    assert before == after


def test_output_directory_must_not_overlap_sources(tmp_path: Path) -> None:
    gt = _frame_dir(tmp_path / "gt")
    baseline = _frame_dir(tmp_path / "baseline", delta=2)

    with pytest.raises(adapter.AdapterError, match="inside input source"):
        _prepare(
            tmp_path,
            ground_truth=gt,
            baseline=baseline,
            output_dir=gt / "prepared",
            episode_ids=["episode_000"],
            overwrite=True,
        )

    assert gt.exists()


def test_adapter_does_not_open_network_sockets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    gt = _frame_dir(tmp_path / "gt")
    baseline = _frame_dir(tmp_path / "baseline", delta=2)

    def fail_socket(*args: Any, **kwargs: Any) -> socket.socket:
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", fail_socket)

    _prepare(
        tmp_path,
        ground_truth=gt,
        baseline=baseline,
        output_dir=tmp_path / "prepared",
        episode_ids=["episode_000"],
    )


def test_unsupported_file_extension_rejected(tmp_path: Path) -> None:
    gt = tmp_path / "gt.txt"
    gt.write_text("not video", encoding="utf-8")
    baseline = _frame_dir(tmp_path / "baseline")

    with pytest.raises(adapter.AdapterError, match="Unsupported file extension"):
        _prepare(
            tmp_path,
            ground_truth=gt,
            baseline=baseline,
            output_dir=tmp_path / "out",
            episode_ids=["episode_000"],
        )


def _prepare(
    tmp_path: Path,
    *,
    ground_truth: Path,
    baseline: Path,
    output_dir: Path,
    candidate: Path | None = None,
    episode_ids: list[str] | None = None,
    metadata_json: Path | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    return adapter.prepare_worldbench_inputs(
        ground_truth=ground_truth,
        baseline=baseline,
        candidate=candidate,
        episode_ids=episode_ids or [],
        baseline_checkpoint="nanowm-50k",
        candidate_checkpoint="nanowm-300k" if candidate is not None else None,
        context_frames=1,
        prediction_frames=2,
        fps=3,
        dataset="RT-1 / Fractal",
        dataset_source="IPEC-COMMUNITY/fractal20220817_data_lerobot",
        camera="observation.images.image",
        metadata_json=metadata_json,
        output_dir=output_dir,
        overwrite=overwrite,
    )


def _episode_tree(root: Path, names: list[str], *, delta: int = 0) -> Path:
    for index, name in enumerate(names):
        _frame_dir(root / name, delta=delta + index)
    return root


def _frame_dir(
    path: Path,
    *,
    frame_count: int = 3,
    size: tuple[int, int] = (16, 12),
    delta: int = 0,
) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(_frames(frame_count, size=size, delta=delta)):
        Image.fromarray(frame).save(path / f"{index:06d}.png")
    return path


def _video(path: Path, *, frame_count: int = 3, fps: int = 3, delta: int = 0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimwrite(
        path, _frames(frame_count, delta=delta), fps=fps, macro_block_size=1
    )
    return path


def _frames(
    count: int,
    *,
    size: tuple[int, int] = (16, 12),
    delta: int = 0,
) -> list[np.ndarray]:
    width, height = size
    frames = []
    for index in range(count):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :, 0] = np.clip(20 + index + delta, 0, 255)
        frame[:, :, 1] = np.clip(80 + index * 2 + delta, 0, 255)
        frame[:, :, 2] = np.clip(140 + index * 3 + delta, 0, 255)
        frames.append(frame)
    return frames


def _tree_hashes(root: Path) -> dict[str, str]:
    hashes = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            hashes[path.relative_to(root).as_posix()] = digest
    return hashes
