from __future__ import annotations

import builtins
from pathlib import Path

from click.testing import CliRunner
import imageio.v2 as imageio
import numpy as np
import pytest

from worldbench.cli import app
from worldbench.runners.video import VideoEvaluationError, evaluate_video_pair
from worldbench.utils import read_json


def test_eval_videos_beginner_command_saves_json_summary_and_artifact(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "inputs with spaces"
    ground_truth = input_dir / "ground truth video.mp4"
    prediction = input_dir / "prediction video.mp4"
    _write_video(ground_truth, _frames(8))
    _write_video(prediction, _frames(8, delta=2))
    output_dir = tmp_path / "results with spaces"

    result = CliRunner().invoke(
        app,
        [
            "eval-videos",
            "--ground-truth",
            str(ground_truth),
            "--prediction",
            str(prediction),
            "--output",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "WorldBench Saved Video Evaluation" in result.output
    assert "Ground truth:" in result.output
    assert "Composite Score" in result.output
    assert "Saved JSON" in result.output
    assert "Saved comparison image" in result.output
    assert (output_dir / "result.json").exists()
    assert (output_dir / "summary.md").exists()
    assert (output_dir / "artifacts" / "comparison.png").exists()

    saved = read_json(output_dir / "result.json")
    assert saved["result_type"] == "evaluation"
    assert saved["provenance"]["alignment_policy"] == "safe"
    assert saved["provenance"]["ground_truth_original_frame_count"] == 8
    assert saved["provenance"]["prediction_original_frame_count"] == 8
    assert saved["provenance"]["evaluated_frame_count"] == 8
    assert saved["provenance"]["ground_truth_frames_trimmed"] == 0
    assert saved["provenance"]["prediction_frames_trimmed"] == 0
    assert saved["provenance"]["ground_truth_original_resolution"] == "32x24"
    assert saved["provenance"]["prediction_original_resolution"] == "32x24"
    assert saved["provenance"]["evaluated_resolution"] == "32x24"
    assert saved["provenance"]["resizing_occurred"] is False
    assert saved["provenance"]["ground_truth_original_fps"] == pytest.approx(5.0)
    assert saved["provenance"]["prediction_original_fps"] == pytest.approx(5.0)
    assert saved["provenance"]["fps_differed"] is False
    assert saved["provenance"]["alignment_method"]
    assert saved["provenance"]["warnings"] == []
    assert "coverage" in saved
    assert saved["metrics"]["visual_similarity"]["status"] == "available"
    assert saved["metrics"]["temporal_stability"]["status"] == "available"
    assert saved["metrics"]["action_consistency"]["status"] == "unsupported"
    assert saved["metrics"]["object_permanence"]["status"] == "unsupported"
    assert saved["metrics"]["contact_realism"]["status"] == "unsupported"

    summary = (output_dir / "summary.md").read_text(encoding="utf-8")
    assert "Ground truth path" in summary
    assert "Prediction path" in summary
    assert "Original ground-truth frame count" in summary
    assert "Frames trimmed from ground truth" in summary
    assert "Metric coverage" in summary


def test_eval_videos_reference_alias_defaults_to_local_output_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reference = tmp_path / "reference.mp4"
    prediction = tmp_path / "prediction.mp4"
    _write_video(reference, _frames(4))
    _write_video(prediction, _frames(4, delta=1))
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "eval-videos",
            "--reference",
            str(reference),
            "--prediction",
            str(prediction),
            "--no-save-comparison",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "worldbench-video-results" / "result.json").exists()
    assert not (tmp_path / "worldbench-video-results" / "artifacts").exists()


def test_eval_videos_help_includes_beginner_example() -> None:
    result = CliRunner().invoke(app, ["eval-videos", "--help"])

    assert result.exit_code == 0
    assert "Evaluate one saved predicted robot future against ground truth" in result.output
    assert "Example:" in result.output
    assert "worldbench eval-videos" in result.output
    assert "--ground-truth ground_truth.mp4" in result.output
    assert "--prediction predicted_future.mp4" in result.output
    assert "--output results/" in result.output


def test_eval_videos_rejects_both_ground_truth_and_reference(
    tmp_path: Path,
) -> None:
    ground_truth = tmp_path / "ground_truth.mp4"
    reference = tmp_path / "reference.mp4"
    prediction = tmp_path / "prediction.mp4"
    _write_video(ground_truth, _frames(4))
    _write_video(reference, _frames(4))
    _write_video(prediction, _frames(4))

    result = CliRunner().invoke(
        app,
        [
            "eval-videos",
            "--ground-truth",
            str(ground_truth),
            "--reference",
            str(reference),
            "--prediction",
            str(prediction),
        ],
    )

    assert result.exit_code != 0
    assert "Use exactly one of --ground-truth or --reference" in result.output


def test_eval_videos_rejects_neither_ground_truth_nor_reference(
    tmp_path: Path,
) -> None:
    prediction = tmp_path / "prediction.mp4"
    _write_video(prediction, _frames(4))

    result = CliRunner().invoke(
        app,
        ["eval-videos", "--prediction", str(prediction)],
    )

    assert result.exit_code != 0
    assert "Provide exactly one of --ground-truth or --reference" in result.output


def test_eval_videos_rejects_missing_prediction_outside_demo(tmp_path: Path) -> None:
    ground_truth = tmp_path / "ground_truth.mp4"
    _write_video(ground_truth, _frames(4))

    result = CliRunner().invoke(
        app,
        ["eval-videos", "--ground-truth", str(ground_truth)],
    )

    assert result.exit_code != 0
    assert "Provide --prediction" in result.output


def test_eval_videos_demo_runs_without_user_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "demo_results"

    result = CliRunner().invoke(
        app, ["eval-videos", "--demo", "--output", str(output_dir)]
    )

    assert result.exit_code == 0, result.output
    assert "Synthetic demonstration data" in result.output
    assert "Not a model-quality result" in result.output
    assert "Not a benchmark result" in result.output
    assert (output_dir / "demo_inputs" / "ground_truth.mp4").exists()
    assert (output_dir / "demo_inputs" / "predicted_future.mp4").exists()
    assert (output_dir / "result.json").exists()
    saved = read_json(output_dir / "result.json")
    assert saved["provenance"]["demo"] is True
    summary = (output_dir / "summary.md").read_text(encoding="utf-8")
    assert "Synthetic demonstration data" in summary
    assert "Not a model-quality result" in summary
    assert "Not a benchmark result" in summary


def test_eval_videos_trims_small_frame_count_mismatch(tmp_path: Path) -> None:
    ground_truth = tmp_path / "ground_truth.mp4"
    prediction = tmp_path / "prediction.mp4"
    _write_video(ground_truth, _frames(8))
    _write_video(prediction, _frames(7, delta=1))
    output_dir = tmp_path / "results"

    result = CliRunner().invoke(
        app,
        [
            "eval-videos",
            "--ground-truth",
            str(ground_truth),
            "--prediction",
            str(prediction),
            "--output",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Frame-count mismatch" in result.output
    saved = read_json(output_dir / "result.json")
    assert saved["provenance"]["evaluated_frame_count"] == 7
    assert saved["provenance"]["alignment"]["frame_count_mismatch"] == 1
    assert saved["provenance"]["ground_truth_frames_trimmed"] == 1
    assert saved["provenance"]["prediction_frames_trimmed"] == 0
    assert "Removed 1 ground-truth future frame(s)" in " ".join(
        saved["provenance"]["warnings"]
    )


def test_eval_videos_rejects_major_frame_count_mismatch(tmp_path: Path) -> None:
    ground_truth = tmp_path / "ground_truth.mp4"
    prediction = tmp_path / "prediction.mp4"
    _write_video(ground_truth, _frames(20))
    _write_video(prediction, _frames(5))

    result = CliRunner().invoke(
        app,
        [
            "eval-videos",
            "--ground-truth",
            str(ground_truth),
            "--prediction",
            str(prediction),
        ],
    )

    assert result.exit_code != 0
    assert "Frame-count mismatch is too large" in result.output


def test_eval_videos_resizes_prediction_to_ground_truth(tmp_path: Path) -> None:
    ground_truth = tmp_path / "ground_truth.mp4"
    prediction = tmp_path / "prediction.mp4"
    _write_video(ground_truth, _frames(6, size=(32, 24)))
    _write_video(prediction, _frames(6, size=(40, 30), delta=3))
    output_dir = tmp_path / "results"

    result = CliRunner().invoke(
        app,
        [
            "eval-videos",
            "--ground-truth",
            str(ground_truth),
            "--prediction",
            str(prediction),
            "--output",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Prediction frames were resized from 40x30 to 32x24" in result.output
    saved = read_json(output_dir / "result.json")
    assert saved["provenance"]["prediction_original_resolution"] == "40x30"
    assert saved["provenance"]["evaluated_resolution"] == "32x24"
    assert saved["provenance"]["resizing_occurred"] is True
    assert saved["metrics"]["visual_similarity"]["status"] == "available"


def test_eval_videos_warns_on_fps_mismatch_and_scores_by_frame_index(
    tmp_path: Path,
) -> None:
    ground_truth = tmp_path / "ground_truth.mp4"
    prediction = tmp_path / "prediction.mp4"
    _write_video(ground_truth, _frames(6), fps=5)
    _write_video(prediction, _frames(6, delta=2), fps=10)
    output_dir = tmp_path / "results"

    result = CliRunner().invoke(
        app,
        [
            "eval-videos",
            "--ground-truth",
            str(ground_truth),
            "--prediction",
            str(prediction),
            "--output",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "FPS mismatch" in result.output
    saved = read_json(output_dir / "result.json")
    assert saved["provenance"]["ground_truth_original_fps"] == pytest.approx(5.0)
    assert saved["provenance"]["prediction_original_fps"] == pytest.approx(10.0)
    assert saved["provenance"]["fps_differed"] is True
    assert saved["metrics"]["visual_similarity"]["status"] == "available"


def test_eval_videos_rejects_existing_file_output(tmp_path: Path) -> None:
    ground_truth = tmp_path / "ground_truth.mp4"
    prediction = tmp_path / "prediction.mp4"
    output = tmp_path / "result-file"
    _write_video(ground_truth, _frames(4))
    _write_video(prediction, _frames(4))
    output.write_text("not a directory", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "eval-videos",
            "--ground-truth",
            str(ground_truth),
            "--prediction",
            str(prediction),
            "--output",
            str(output),
        ],
    )

    assert result.exit_code != 0
    assert "not a directory" in result.output


def test_eval_videos_reports_missing_and_corrupted_files(tmp_path: Path) -> None:
    prediction = tmp_path / "prediction.mp4"
    _write_video(prediction, _frames(4))
    missing = tmp_path / "missing.mp4"

    missing_result = CliRunner().invoke(
        app,
        [
            "eval-videos",
            "--ground-truth",
            str(missing),
            "--prediction",
            str(prediction),
        ],
    )

    assert missing_result.exit_code != 0
    assert "does not exist" in missing_result.output

    corrupted = tmp_path / "corrupted.mp4"
    corrupted.write_text("not a video", encoding="utf-8")
    corrupt_result = CliRunner().invoke(
        app,
        [
            "eval-videos",
            "--ground-truth",
            str(corrupted),
            "--prediction",
            str(prediction),
        ],
    )

    assert corrupt_result.exit_code != 0
    assert "unreadable" in corrupt_result.output
    assert "Re-encode it as a standard MP4/H.264 file" in corrupt_result.output
    assert "ffmpeg version" not in corrupt_result.output


def test_eval_videos_reports_unsupported_extension(tmp_path: Path) -> None:
    ground_truth = tmp_path / "ground_truth.txt"
    prediction = tmp_path / "prediction.mp4"
    ground_truth.write_text("not a video", encoding="utf-8")
    _write_video(prediction, _frames(4))

    result = CliRunner().invoke(
        app,
        [
            "eval-videos",
            "--ground-truth",
            str(ground_truth),
            "--prediction",
            str(prediction),
        ],
    )

    assert result.exit_code != 0
    assert "unsupported extension" in result.output


def test_eval_videos_reports_missing_optional_video_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ground_truth = tmp_path / "ground_truth.mp4"
    prediction = tmp_path / "prediction.mp4"
    _write_video(ground_truth, _frames(4))
    _write_video(prediction, _frames(4))
    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("imageio"):
            raise ImportError("imageio unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(VideoEvaluationError, match="video extra"):
        evaluate_video_pair(ground_truth, prediction)


def test_eval_videos_scores_are_deterministic(tmp_path: Path) -> None:
    ground_truth = tmp_path / "ground_truth.mp4"
    prediction = tmp_path / "prediction.mp4"
    _write_video(ground_truth, _frames(6))
    _write_video(prediction, _frames(6, delta=2))

    first = evaluate_video_pair(ground_truth, prediction, alignment="safe")
    second = evaluate_video_pair(ground_truth, prediction, alignment="safe")

    assert second.score == pytest.approx(first.score)
    for metric_name in first.metrics:
        if first.metrics[metric_name].score is None:
            assert second.metrics[metric_name].score is None
        else:
            assert second.metrics[metric_name].score == pytest.approx(
                first.metrics[metric_name].score
            )
        assert second.metrics[metric_name].status == first.metrics[metric_name].status
    assert second.horizon["t+1"]["metrics"] == first.horizon["t+1"]["metrics"]


def test_eval_video_existing_command_remains_strict(tmp_path: Path) -> None:
    ground_truth = tmp_path / "ground_truth.mp4"
    prediction = tmp_path / "prediction.mp4"
    _write_video(ground_truth, _frames(6))
    _write_video(prediction, _frames(5))

    result = CliRunner().invoke(
        app,
        [
            "eval-video",
            "--ground-truth",
            str(ground_truth),
            "--prediction",
            str(prediction),
        ],
    )

    assert result.exit_code != 0
    assert "requires matching future lengths" in result.output


def test_beginner_docs_do_not_use_baseline_as_two_video_reference() -> None:
    roots = [
        Path("README.md"),
        Path("docs/CLI.md"),
        Path("docs/SAVED_VIDEO_EVALUATION.md"),
        Path("examples/colab/worldbench_saved_video_demo.ipynb"),
    ]
    patterns = [
        "reference " + "baseline",
        "baseline" + ".mp4",
        "prediction " + "candidate",
        "candidate" + ".mp4",
    ]
    matches = []
    for root in roots:
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for pattern in patterns:
                if pattern in text:
                    matches.append(f"{path}: {pattern}")

    assert matches == []


def _frames(
    count: int,
    *,
    size: tuple[int, int] = (32, 24),
    delta: int = 0,
) -> list[np.ndarray]:
    width, height = size
    frames = []
    for index in range(count):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :, 0] = np.clip(40 + index * 8 + delta, 0, 255)
        frame[:, :, 1] = np.clip(80 + index * 5 + delta, 0, 255)
        frame[:, :, 2] = np.clip(120 + index * 3 + delta, 0, 255)
        frame[4:10, 4 + index % 8 : 10 + index % 8, :] = np.clip(
            [190 + delta, 40 + delta, 40 + delta],
            0,
            255,
        )
        frames.append(frame)
    return frames


def _write_video(path: Path, frames: list[np.ndarray], *, fps: int = 5) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimwrite(path, frames, fps=fps, macro_block_size=1)
