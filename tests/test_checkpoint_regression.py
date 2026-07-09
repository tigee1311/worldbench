from __future__ import annotations

from pathlib import Path
import copy

from click.testing import CliRunner
import imageio.v2 as imageio
import numpy as np
import pytest

from worldbench.cli import app
from worldbench.runners.regression import (
    build_gate_comparison,
    evaluate_video_batch,
)
from worldbench.runners.video import VideoEvaluationError, evaluate_video_pair
from worldbench.utils import read_json, write_json


def test_eval_video_valid_pair_saves_future_only_result(tmp_path: Path) -> None:
    gt = tmp_path / "sample_gt.mp4"
    pred = tmp_path / "sample_pred.mp4"
    _write_video(gt, _frames(12))
    _write_video(pred, _frames(12, delta=2))

    result = evaluate_video_pair(gt, pred, skip_context=4, name="sample")

    assert result.provenance["ground_truth_frame_count"] == 12
    assert result.provenance["prediction_frame_count"] == 12
    assert result.provenance["evaluated_frame_count"] == 8
    assert result.metrics["visual_similarity"].is_available
    assert result.metrics["action_consistency"].status == "unsupported"
    assert "t+1" in result.horizon
    assert result.horizon["t+1"]["metrics"]["visual_similarity"]["mean"] > 80
    assert result.episodes[0].horizon["t+1"]["metrics"]["visual_similarity"]["score"] > 80
    assert "action_consistency" not in result.horizon["t+1"]["metrics"]
    assert "action_consistency" in result.horizon["t+1"]["unavailable_metrics"]


def test_eval_video_cli_saves_normal_result_structure(tmp_path: Path) -> None:
    gt = tmp_path / "gt.mp4"
    pred = tmp_path / "pred.mp4"
    _write_video(gt, _frames(6))
    _write_video(pred, _frames(6, delta=1))
    output_root = tmp_path / "runs"

    result = CliRunner().invoke(
        app,
        [
            "eval-video",
            "--ground-truth",
            str(gt),
            "--prediction",
            str(pred),
            "--skip-context",
            "2",
            "--output-root",
            str(output_root),
        ],
    )

    assert result.exit_code == 0, result.output
    saved = read_json(output_root / "latest" / "result.json")
    assert saved["result_type"] == "evaluation"
    assert saved["provenance"]["evaluated_frame_count"] == 4
    assert saved["episodes"][0]["horizon"]["t+1"]["sample_count"] == 1
    assert "Saved run directory" in result.output


@pytest.mark.parametrize("skip_context", [-1])
def test_eval_video_rejects_negative_skip_context(tmp_path: Path, skip_context: int) -> None:
    gt = tmp_path / "gt.mp4"
    pred = tmp_path / "pred.mp4"
    _write_video(gt, _frames(4))
    _write_video(pred, _frames(4))

    with pytest.raises(VideoEvaluationError, match="non-negative"):
        evaluate_video_pair(gt, pred, skip_context=skip_context)


def test_eval_video_rejects_skip_context_too_large(tmp_path: Path) -> None:
    gt = tmp_path / "gt.mp4"
    pred = tmp_path / "pred.mp4"
    _write_video(gt, _frames(4))
    _write_video(pred, _frames(4))

    with pytest.raises(VideoEvaluationError, match="leaves no ground-truth future"):
        evaluate_video_pair(gt, pred, skip_context=4)


def test_eval_video_rejects_future_frame_count_mismatch(tmp_path: Path) -> None:
    gt = tmp_path / "gt.mp4"
    pred = tmp_path / "pred.mp4"
    _write_video(gt, _frames(6))
    _write_video(pred, _frames(5))

    with pytest.raises(VideoEvaluationError, match="requires matching future lengths"):
        evaluate_video_pair(gt, pred, skip_context=2)


def test_eval_video_rejects_resolution_mismatch(tmp_path: Path) -> None:
    gt = tmp_path / "gt.mp4"
    pred = tmp_path / "pred.mp4"
    _write_video(gt, _frames(5, size=(32, 24)))
    _write_video(pred, _frames(5, size=(40, 24)))

    with pytest.raises(VideoEvaluationError, match="resolution differs"):
        evaluate_video_pair(gt, pred, skip_context=1)


def test_eval_video_rejects_fps_mismatch(tmp_path: Path) -> None:
    gt = tmp_path / "gt.mp4"
    pred = tmp_path / "pred.mp4"
    _write_video(gt, _frames(5), fps=5)
    _write_video(pred, _frames(5), fps=10)

    with pytest.raises(VideoEvaluationError, match="FPS differs"):
        evaluate_video_pair(gt, pred, skip_context=1)


def test_eval_video_rejects_unreadable_video(tmp_path: Path) -> None:
    gt = tmp_path / "gt.mp4"
    pred = tmp_path / "pred.mp4"
    gt.write_text("not a video", encoding="utf-8")
    _write_video(pred, _frames(4))

    with pytest.raises(VideoEvaluationError, match="unreadable"):
        evaluate_video_pair(gt, pred, skip_context=1)


def test_eval_batch_pairs_by_relative_path_and_aggregates_available_values(
    tmp_path: Path,
) -> None:
    gt_root = tmp_path / "eval_suite"
    pred_root = tmp_path / "checkpoint_184"
    _write_video(gt_root / "episode_001.mp4", _frames(6))
    _write_video(gt_root / "nested" / "episode_002.mp4", _frames(4, delta=4))
    _write_video(pred_root / "episode_001.mp4", _frames(6, delta=1))
    _write_video(pred_root / "nested" / "episode_002.mp4", _frames(4, delta=7))

    payload, paths = evaluate_video_batch(
        gt_root,
        pred_root,
        name="checkpoint_184",
        skip_context=2,
        output_root=tmp_path / "batches",
        output=tmp_path / "checkpoint_184.json",
    )

    assert payload["episode_ids"] == ["episode_001.mp4", "nested/episode_002.mp4"]
    assert payload["episode_count"] == 2
    scores = [episode["score"] for episode in payload["episodes"]]
    assert payload["aggregate"]["overall"]["mean"] == pytest.approx(float(np.mean(scores)))
    assert payload["aggregate"]["overall"]["median"] == pytest.approx(float(np.median(scores)))
    assert payload["aggregate"]["overall"]["std"] == pytest.approx(float(np.std(scores)))
    assert payload["aggregate"]["overall"]["p10"] == pytest.approx(float(np.percentile(scores, 10)))
    assert payload["aggregate"]["overall"]["p25"] == pytest.approx(float(np.percentile(scores, 25)))
    assert payload["aggregate"]["overall"]["p50"] == pytest.approx(float(np.percentile(scores, 50)))
    assert payload["aggregate"]["overall"]["p75"] == pytest.approx(float(np.percentile(scores, 75)))
    assert payload["aggregate"]["overall"]["p90"] == pytest.approx(float(np.percentile(scores, 90)))
    assert payload["aggregate"]["metrics"]["action_consistency"]["status"] == "unsupported"
    assert payload["aggregate"]["metrics"]["visual_similarity"]["available_count"] == 2
    assert payload["horizon"]["t+1"]["metrics"]["visual_similarity"]["count"] == 2
    assert payload["horizon"]["t+3"]["metrics"]["visual_similarity"]["count"] == 1
    assert paths["json"].exists()
    assert paths["latest_json"].exists()
    assert paths["output_json"].exists()
    assert Path(payload["episodes"][0]["result_path"]).exists()


def test_eval_batch_rejects_missing_and_extra_predictions(tmp_path: Path) -> None:
    gt_root = tmp_path / "eval_suite"
    pred_root = tmp_path / "checkpoint"
    _write_video(gt_root / "episode_001.mp4", _frames(4))
    _write_video(gt_root / "episode_002.mp4", _frames(4))
    _write_video(pred_root / "episode_001.mp4", _frames(4))
    _write_video(pred_root / "episode_003.mp4", _frames(4))

    with pytest.raises(ValueError) as exc:
        evaluate_video_batch(gt_root, pred_root, output_root=tmp_path / "batches")

    message = str(exc.value)
    assert "Missing predictions: 1" in message
    assert "Prediction-only episodes: 1" in message
    assert "episode_002.mp4" in message
    assert "episode_003.mp4" in message


def test_gate_passes_when_candidate_improves(tmp_path: Path) -> None:
    baseline, candidate = _baseline_candidate_batches(tmp_path)

    comparison = build_gate_comparison(baseline, candidate)

    assert comparison["status"] == "PASS"
    assert comparison["overall"]["change"] > 0
    assert comparison["episodes"]["improved_count"] == 2
    assert not any(item["metric"] == "action_consistency" for item in comparison["metrics"])


def test_gate_cli_exit_zero_on_pass(tmp_path: Path) -> None:
    baseline, candidate = _baseline_candidate_batches(tmp_path)
    baseline_path = tmp_path / "baseline.json"
    candidate_path = tmp_path / "candidate.json"
    write_json(baseline_path, baseline)
    write_json(candidate_path, candidate)

    result = CliRunner().invoke(
        app,
        [
            "gate",
            "--baseline",
            str(baseline_path),
            "--candidate",
            str(candidate_path),
            "--output-root",
            str(tmp_path / "gates"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "PASS" in result.output
    assert (tmp_path / "gates" / "latest" / "gate.json").exists()


def test_gate_fails_overall_metric_and_horizon_regressions(tmp_path: Path) -> None:
    baseline, candidate = _baseline_candidate_batches(tmp_path)

    overall = build_gate_comparison(candidate, baseline)
    metric = build_gate_comparison(
        candidate,
        baseline,
        max_overall_drop=100,
        max_metric_drop=0,
        max_horizon_drop=100,
    )
    horizon = build_gate_comparison(
        candidate,
        baseline,
        max_overall_drop=100,
        max_metric_drop=100,
        max_horizon_drop=0,
    )

    assert overall["status"] == "FAIL"
    assert any(reason["kind"] == "overall" for reason in overall["failure_reasons"])
    assert metric["status"] == "FAIL"
    assert any(reason["kind"] == "metric" for reason in metric["failure_reasons"])
    assert horizon["status"] == "FAIL"
    assert any(reason["kind"] == "horizon" for reason in horizon["failure_reasons"])


def test_gate_cli_exit_one_on_valid_regression_fail(tmp_path: Path) -> None:
    baseline, candidate = _baseline_candidate_batches(tmp_path)
    baseline_path = tmp_path / "baseline.json"
    candidate_path = tmp_path / "candidate.json"
    write_json(baseline_path, candidate)
    write_json(candidate_path, baseline)

    result = CliRunner().invoke(
        app,
        [
            "gate",
            "--baseline",
            str(baseline_path),
            "--candidate",
            str(candidate_path),
            "--output-root",
            str(tmp_path / "gates"),
        ],
    )

    assert result.exit_code == 1, result.output
    assert "FAIL" in result.output
    assert "Regression detected" in result.output


def test_gate_rejects_mismatched_episode_sets_with_usage_error(tmp_path: Path) -> None:
    baseline, candidate = _baseline_candidate_batches(tmp_path)
    candidate = copy.deepcopy(candidate)
    candidate["episode_ids"] = candidate["episode_ids"][:-1]
    candidate["episodes"] = candidate["episodes"][:-1]
    baseline_path = tmp_path / "baseline.json"
    candidate_path = tmp_path / "candidate.json"
    write_json(baseline_path, baseline)
    write_json(candidate_path, candidate)

    result = CliRunner().invoke(
        app,
        [
            "gate",
            "--baseline",
            str(baseline_path),
            "--candidate",
            str(candidate_path),
        ],
    )

    assert result.exit_code == 2
    assert "different episode sets" in result.output


def _baseline_candidate_batches(tmp_path: Path) -> tuple[dict, dict]:
    gt_root = tmp_path / "suite"
    baseline_root = tmp_path / "checkpoint_183"
    candidate_root = tmp_path / "checkpoint_184"
    for episode, delta in [("episode_001.mp4", 0), ("episode_002.mp4", 4)]:
        gt_frames = _frames(6, delta=delta)
        _write_video(gt_root / episode, gt_frames)
        _write_video(baseline_root / episode, _degraded_frames(6, delta=delta + 35))
        _write_video(candidate_root / episode, gt_frames)

    baseline, _ = evaluate_video_batch(
        gt_root,
        baseline_root,
        name="checkpoint_183",
        skip_context=2,
        output_root=tmp_path / "baseline_runs",
        output=tmp_path / "checkpoint_183.json",
    )
    candidate, _ = evaluate_video_batch(
        gt_root,
        candidate_root,
        name="checkpoint_184",
        skip_context=2,
        output_root=tmp_path / "candidate_runs",
        output=tmp_path / "checkpoint_184.json",
    )
    return baseline, candidate


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


def _degraded_frames(count: int, *, delta: int = 0) -> list[np.ndarray]:
    frames = _frames(count, delta=delta)
    for index, frame in enumerate(frames):
        if index % 2:
            frame[:, :, :] = 255 - frame
    return frames


def _write_video(path: Path, frames: list[np.ndarray], *, fps: int = 5) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimwrite(path, frames, fps=fps, macro_block_size=1)
