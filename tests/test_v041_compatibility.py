from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from worldbench.cli import app
from worldbench.config import load_config
from worldbench.runners.regression import build_gate_comparison, load_batch_result
from worldbench.schemas import EvaluationResult
from worldbench.utils import read_json
from worldbench.verification import verify_result_file

FIXTURES = Path(__file__).parent / "fixtures" / "v0_4_1"


def test_v041_saved_video_result_loads_without_new_fields() -> None:
    payload = read_json(FIXTURES / "saved_video" / "result.json")

    result = EvaluationResult.model_validate(payload)

    assert result.result_type == "evaluation"
    assert result.schema_version == "2"
    assert result.score == pytest.approx(96.10118880756227)
    assert "input_files" not in result.provenance
    assert "uncertainty" not in payload


def test_v041_saved_video_markdown_report_is_readable() -> None:
    summary = (FIXTURES / "saved_video" / "summary.md").read_text(encoding="utf-8")

    assert "WorldBench Evaluation Report" in summary
    assert "Composite Score" in summary
    assert "Metric coverage" in summary


def test_v041_batch_results_load_and_gate_semantics_are_unchanged() -> None:
    baseline = load_batch_result(FIXTURES / "batch" / "baseline_batch_result.json")
    candidate = load_batch_result(FIXTURES / "batch" / "candidate_batch_result.json")
    v041_gate = read_json(FIXTURES / "gate" / "latest" / "gate.json")

    comparison = build_gate_comparison(
        baseline,
        candidate,
        max_overall_drop=v041_gate["thresholds"]["max_overall_drop"],
        max_metric_drop=v041_gate["thresholds"]["max_metric_drop"],
        max_horizon_drop=v041_gate["thresholds"]["max_horizon_drop"],
        required_metrics=v041_gate["thresholds"]["required_metrics"],
        min_metric_count=v041_gate["thresholds"]["min_metric_count"],
        min_metric_coverage=v041_gate["thresholds"]["min_metric_coverage"],
        min_configured_weight_coverage=v041_gate["thresholds"][
            "min_configured_weight_coverage"
        ],
        strict_config_match=v041_gate["thresholds"]["strict_config_match"],
        max_episode_regressions=v041_gate["thresholds"]["max_episode_regressions"],
        min_composite_improvement=v041_gate["thresholds"]["min_composite_improvement"],
    )

    assert baseline["result_type"] == "batch_evaluation"
    assert candidate["result_type"] == "batch_evaluation"
    assert comparison["status"] == v041_gate["status"] == "PASS"
    assert comparison["passed"] is v041_gate["passed"] is True
    assert comparison["overall"]["baseline"] == pytest.approx(
        v041_gate["overall"]["baseline"]
    )
    assert comparison["overall"]["candidate"] == pytest.approx(
        v041_gate["overall"]["candidate"]
    )
    assert comparison["overall"]["change"] == pytest.approx(
        v041_gate["overall"]["change"]
    )
    assert comparison["episodes"]["improved_count"] == 1
    assert comparison["episodes"]["regressed_count"] == 0
    assert comparison["uncertainty"] is None


def test_v041_configuration_files_load() -> None:
    config, path = load_config(FIXTURES / "worldbench.yml")
    gate_config, gate_path = load_config(FIXTURES / "gate_config.yml")

    assert path == FIXTURES / "worldbench.yml"
    assert gate_path == FIXTURES / "gate_config.yml"
    assert config.enabled_metrics == gate_config.enabled_metrics
    assert config.gate.strict_config_match is True
    assert gate_config.gate.max_episode_regressions == 0


def test_v041_nanowm_artifact_loads_as_legacy_evaluation_result() -> None:
    payload = read_json(FIXTURES / "nanowm_rt1_episode0.json")

    result = EvaluationResult.model_validate(payload)

    assert result.result_type == "evaluation"
    assert result.score == pytest.approx(92.39024104284573)
    assert result.worldbench_version is None
    assert result.provenance["worldbench_version"] == "0.1.0"


def test_v041_missing_provenance_is_reported_not_fabricated() -> None:
    verification = verify_result_file(FIXTURES / "saved_video" / "result.json")

    assert verification.status == "PASS"
    assert verification.checked_input_files == 0
    messages = [issue.message for issue in verification.warnings]
    assert any("Metric plugin versions are not recorded" in item for item in messages)
    assert any(
        "report_configuration_sha256 is not recorded" in item for item in messages
    )


def test_v041_cli_reference_alias_still_works(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "eval-videos",
            "--reference",
            str(FIXTURES / "saved_video" / "demo_inputs" / "ground_truth.mp4"),
            "--prediction",
            str(FIXTURES / "saved_video" / "demo_inputs" / "predicted_future.mp4"),
            "--output",
            str(tmp_path / "alias-result"),
            "--no-save-comparison",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = read_json(tmp_path / "alias-result" / "result.json")
    assert payload["score"] == pytest.approx(96.10118880756227)


def test_old_result_type_is_not_silently_misinterpreted(tmp_path: Path) -> None:
    malformed = tmp_path / "result.json"
    malformed.write_text(
        json.dumps(
            {
                "schema_version": "2",
                "result_type": "evaluation",
                "aggregate": {"overall": {"mean": 1.0}},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Expected a batch evaluation result"):
        load_batch_result(malformed)
