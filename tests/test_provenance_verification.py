from __future__ import annotations

from pathlib import Path

import imageio.v2 as imageio
import numpy as np
import pytest
from click.testing import CliRunner

from worldbench.cli import app
from worldbench.runners.video import evaluate_video_pair
from worldbench.utils import read_json_limited, write_json
from worldbench.verification import verify_result_file


def test_video_result_records_hashes_versions_and_decoder_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_video(Path("ground_truth.mp4"), _frames(4))
    _write_video(Path("prediction.mp4"), _frames(4, delta=1))

    result = evaluate_video_pair(Path("ground_truth.mp4"), Path("prediction.mp4"))
    saved = result.save_json(tmp_path / "result.json")

    provenance = result.provenance
    assert provenance["ground_truth_sha256"].startswith("sha256:")
    assert provenance["prediction_sha256"].startswith("sha256:")
    assert provenance["report_configuration_sha256"].startswith("sha256:")
    assert provenance["metric_plugins"]["visual_similarity"] == "1.0"
    assert provenance["environment"]["worldbench_version"]
    assert provenance["decoder_backend"] == "imageio.v2"
    assert "ground_truth_codec_metadata" in provenance
    assert provenance["input_files"][0]["path_redacted"] is False

    verification = verify_result_file(saved)
    assert verification.status == "PASS"
    assert verification.checked_input_files == 2


def test_verify_run_detects_hash_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    ground_truth = Path("ground_truth.mp4")
    prediction = Path("prediction.mp4")
    _write_video(ground_truth, _frames(4))
    _write_video(prediction, _frames(4, delta=1))
    result = evaluate_video_pair(ground_truth, prediction)
    saved = result.save_json(tmp_path / "result.json")
    _write_video(prediction, _frames(4, delta=20))

    verification = verify_result_file(saved)

    assert verification.status == "FAIL"
    assert any("hash mismatch" in issue.message for issue in verification.errors)


def test_verify_run_detects_missing_input_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    ground_truth = Path("ground_truth.mp4")
    prediction = Path("prediction.mp4")
    _write_video(ground_truth, _frames(4))
    _write_video(prediction, _frames(4, delta=1))
    result = evaluate_video_pair(ground_truth, prediction)
    saved = result.save_json(tmp_path / "result.json")
    prediction.unlink()

    verification = verify_result_file(saved)

    assert verification.status == "FAIL"
    assert any("does not exist" in issue.message for issue in verification.errors)


def test_absolute_paths_are_redacted_by_default(tmp_path: Path) -> None:
    ground_truth = tmp_path / "ground_truth.mp4"
    prediction = tmp_path / "prediction.mp4"
    _write_video(ground_truth, _frames(4))
    _write_video(prediction, _frames(4, delta=1))

    result = evaluate_video_pair(ground_truth, prediction)

    assert result.provenance["ground_truth_path"] == "ground_truth.mp4"
    assert result.provenance["prediction_path"] == "prediction.mp4"
    assert str(tmp_path) not in result.provenance["ground_truth_path"]
    assert result.provenance["input_files"][0]["path_redacted"] is True


def test_verify_run_warns_when_paths_were_redacted(tmp_path: Path) -> None:
    ground_truth = tmp_path / "ground_truth.mp4"
    prediction = tmp_path / "prediction.mp4"
    _write_video(ground_truth, _frames(4))
    _write_video(prediction, _frames(4, delta=1))
    saved = evaluate_video_pair(ground_truth, prediction).save_json(
        tmp_path / "result.json"
    )

    verification = verify_result_file(saved)

    assert verification.status == "PASS"
    assert verification.checked_input_files == 0
    assert any("path was redacted" in issue.message for issue in verification.warnings)


def test_verify_run_detects_configuration_hash_mismatch(tmp_path: Path) -> None:
    result_path = _saved_relative_result(tmp_path)
    payload = _read_json(result_path)
    payload["configuration"]["metrics"]["visual_similarity"]["weight"] = 0.99
    write_json(result_path, payload)

    verification = verify_result_file(result_path)

    assert verification.status == "FAIL"
    assert any(
        "configuration hash mismatch" in issue.message.lower()
        for issue in verification.errors
    )


def test_verify_run_detects_metric_version_mismatch(tmp_path: Path) -> None:
    result_path = _saved_relative_result(tmp_path)
    payload = _read_json(result_path)
    payload["provenance"]["metric_plugins"]["visual_similarity"] = "999.0"
    write_json(result_path, payload)

    verification = verify_result_file(result_path)

    assert verification.status == "FAIL"
    assert any("version mismatch" in issue.message for issue in verification.errors)


def test_verify_run_rejects_malformed_json(tmp_path: Path) -> None:
    result_path = tmp_path / "bad.json"
    result_path.write_text("{not-json", encoding="utf-8")

    verification = verify_result_file(result_path)

    assert verification.status == "FAIL"
    assert any("Could not read JSON" in issue.message for issue in verification.errors)


def test_limited_json_reader_rejects_oversized_files(tmp_path: Path) -> None:
    path = tmp_path / "large.json"
    path.write_text('{"payload":"' + ("x" * 20) + '"}', encoding="utf-8")

    with pytest.raises(ValueError, match="too large"):
        read_json_limited(path, max_bytes=10)


def test_verify_run_cli_reports_failures(tmp_path: Path) -> None:
    result_path = tmp_path / "bad.json"
    result_path.write_text("[]", encoding="utf-8")

    result = CliRunner().invoke(app, ["verify-run", str(result_path)])

    assert result.exit_code == 1
    assert "FAIL" in result.output
    assert "Result JSON must be an object" in result.output


def _saved_relative_result(tmp_path: Path) -> Path:
    ground_truth = tmp_path / "ground_truth.mp4"
    prediction = tmp_path / "prediction.mp4"
    _write_video(ground_truth, _frames(4))
    _write_video(prediction, _frames(4, delta=1))
    return evaluate_video_pair(ground_truth, prediction).save_json(
        tmp_path / "result.json"
    )


def _read_json(path: Path) -> dict:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _frames(count: int, *, delta: int = 0) -> list[np.ndarray]:
    frames = []
    for index in range(count):
        frame = np.zeros((24, 32, 3), dtype=np.uint8)
        frame[:, :, 0] = np.clip(40 + index * 8 + delta, 0, 255)
        frame[:, :, 1] = np.clip(80 + index * 5 + delta, 0, 255)
        frame[:, :, 2] = np.clip(120 + index * 3 + delta, 0, 255)
        frames.append(frame)
    return frames


def _write_video(path: Path, frames: list[np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimwrite(path, frames, fps=5, macro_block_size=1)
