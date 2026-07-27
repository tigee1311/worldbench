from __future__ import annotations

from pathlib import Path

from worldbench.runners.regression import _safe_artifact_name
from worldbench.utils import write_json
from worldbench.verification import verify_result_file


def test_episode_artifact_name_rejects_path_traversal_shape() -> None:
    name = _safe_artifact_name("../../private/key.mp4")

    assert "/" not in name
    assert "\\" not in name
    assert name != ".."
    assert name.endswith("key.mp4")


def test_verify_run_does_not_follow_parent_directory_traversal(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"video")
    result = tmp_path / "nested" / "result.json"
    write_json(
        result,
        {
            "result_type": "evaluation",
            "worldbench_version": "0.4.1",
            "configuration": {},
            "configuration_hash": "legacy",
            "provenance": {
                "metric_plugins": {},
                "input_files": [
                    {
                        "role": "ground_truth_video",
                        "path": "../outside.mp4",
                        "path_redacted": False,
                        "sha256": "sha256:not-the-point",
                    }
                ],
            },
        },
    )

    verification = verify_result_file(result)

    assert verification.status == "FAIL"
    assert any("does not exist" in issue.message for issue in verification.errors)
