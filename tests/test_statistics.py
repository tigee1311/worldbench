from __future__ import annotations

import pytest

from worldbench.config import coverage_for
from worldbench.runners.regression import build_gate_comparison
from worldbench.statistics import paired_bootstrap_interval


def test_paired_bootstrap_is_deterministic_for_mixed_deltas() -> None:
    deltas = [-1.0, 0.5, 2.0, 3.5, -0.25]

    first = paired_bootstrap_interval(deltas, bootstrap_samples=500, bootstrap_seed=7)
    second = paired_bootstrap_interval(deltas, bootstrap_samples=500, bootstrap_seed=7)

    assert second.to_dict() == first.to_dict()
    assert first.paired_delta_mean == pytest.approx(0.95)
    assert first.confidence_interval[0] <= first.paired_delta_mean
    assert first.confidence_interval[1] >= first.paired_delta_mean


def test_paired_bootstrap_constant_deltas_have_constant_interval() -> None:
    result = paired_bootstrap_interval([1.5, 1.5, 1.5], bootstrap_samples=100)

    assert result.paired_delta_mean == pytest.approx(1.5)
    assert result.confidence_interval == pytest.approx((1.5, 1.5))
    assert result.small_sample_warning is True


def test_paired_bootstrap_one_episode_warns_and_is_exact() -> None:
    result = paired_bootstrap_interval([2.25], bootstrap_samples=100)

    assert result.episode_count == 1
    assert result.confidence_interval == pytest.approx((2.25, 2.25))
    assert result.small_sample_warning is True


def test_paired_bootstrap_zero_episodes_is_rejected() -> None:
    with pytest.raises(ValueError, match="At least one"):
        paired_bootstrap_interval([])


def test_paired_bootstrap_confidence_level_changes_interval_width() -> None:
    narrow = paired_bootstrap_interval(
        [-2.0, -1.0, 1.0, 2.0, 4.0],
        bootstrap_samples=1000,
        confidence_level=0.80,
    )
    wide = paired_bootstrap_interval(
        [-2.0, -1.0, 1.0, 2.0, 4.0],
        bootstrap_samples=1000,
        confidence_level=0.95,
    )

    assert (wide.confidence_interval[1] - wide.confidence_interval[0]) >= (
        narrow.confidence_interval[1] - narrow.confidence_interval[0]
    )


def test_paired_bootstrap_seed_is_recorded_and_changes_resampling() -> None:
    first = paired_bootstrap_interval(
        [0.0, 1.0, 2.0, 4.0], bootstrap_samples=50, bootstrap_seed=1
    )
    second = paired_bootstrap_interval(
        [0.0, 1.0, 2.0, 4.0], bootstrap_samples=50, bootstrap_seed=2
    )

    assert first.bootstrap_seed == 1
    assert second.bootstrap_seed == 2
    assert first.confidence_interval != second.confidence_interval


def test_gate_keeps_uncertainty_disabled_by_default() -> None:
    comparison = build_gate_comparison(_batch([80, 80]), _batch([82, 82]))

    assert comparison["status"] == "PASS"
    assert comparison["uncertainty"] is None


def test_gate_adds_opt_in_uncertainty_and_lower_bound_passes() -> None:
    comparison = build_gate_comparison(
        _batch([80, 81, 82]),
        _batch([82, 83, 84]),
        bootstrap_samples=200,
        min_confidence_lower_bound=1.0,
    )

    assert comparison["status"] == "PASS"
    assert comparison["uncertainty"]["paired_delta_mean"] == pytest.approx(2.0)
    assert comparison["uncertainty"]["confidence_interval"] == pytest.approx([2.0, 2.0])
    assert any("small episode count" in warning for warning in comparison["warnings"])


def test_gate_opt_in_confidence_lower_bound_can_fail() -> None:
    comparison = build_gate_comparison(
        _batch([80, 81, 82]),
        _batch([82, 83, 84]),
        bootstrap_samples=200,
        min_confidence_lower_bound=3.0,
    )

    assert comparison["status"] == "FAIL"
    assert any(
        item["kind"] == "confidence_lower_bound"
        for item in comparison["failure_reasons"]
    )


def test_confidence_lower_bound_requires_bootstrap_samples() -> None:
    with pytest.raises(ValueError, match="requires --bootstrap-samples"):
        build_gate_comparison(
            _batch([80]),
            _batch([81]),
            min_confidence_lower_bound=0.0,
        )


def _batch(scores: list[float]) -> dict:
    configured = ["visual_similarity"]
    weights = {"visual_similarity": 1.0}
    episodes = [
        {"episode_id": f"episode_{index:03d}.mp4", "score": score}
        for index, score in enumerate(scores)
    ]
    mean = sum(scores) / len(scores)
    return {
        "schema_version": "2",
        "result_type": "batch_evaluation",
        "checkpoint_name": "checkpoint",
        "skip_context": 0,
        "episode_count": len(scores),
        "episode_ids": [episode["episode_id"] for episode in episodes],
        "dataset_identifier": "sha256:dataset",
        "episodes": episodes,
        "aggregate": {
            "overall": {"mean": mean},
            "composite_score": {"mean": mean},
            "metrics": {
                "visual_similarity": {
                    "status": "available",
                    "mean": mean,
                    "available_count": len(scores),
                    "total_count": len(scores),
                }
            },
        },
        "horizon": {},
        "enabled_metrics": configured,
        "required_metrics": [],
        "configured_weights": weights,
        "configuration_hash": "same",
        "coverage": coverage_for(configured, weights, configured),
    }
