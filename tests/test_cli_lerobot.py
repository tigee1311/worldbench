from __future__ import annotations

from pathlib import Path
from typing import Any

from click.testing import CliRunner

from worldbench import cli
from worldbench.cli import app
from worldbench.schemas import ValidationReport


def test_import_lerobot_cli_defaults_to_video_timeline(
    monkeypatch, tmp_path: Path
) -> None:
    captured: dict[str, Any] = {}

    def fake_import_lerobot_repo(
        repo_id: str, output_path: Path, **kwargs: Any
    ) -> ValidationReport:
        kwargs["repo_id"] = repo_id
        kwargs["output_path"] = output_path
        captured.update(kwargs)
        return ValidationReport(
            dataset_path=str(kwargs["output_path"]), episode_count=1, frame_count=2
        )

    monkeypatch.setattr(cli, "import_lerobot_repo", fake_import_lerobot_repo)

    result = CliRunner().invoke(
        app,
        [
            "import-lerobot",
            "--repo-id",
            "user/dataset",
            "--episodes",
            "0:1",
            "--out",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["timeline"] == "video"


def test_import_lerobot_cli_accepts_control_timeline(
    monkeypatch, tmp_path: Path
) -> None:
    captured: dict[str, Any] = {}

    def fake_import_lerobot_repo(
        repo_id: str, output_path: Path, **kwargs: Any
    ) -> ValidationReport:
        kwargs["repo_id"] = repo_id
        kwargs["output_path"] = output_path
        captured.update(kwargs)
        return ValidationReport(
            dataset_path=str(kwargs["output_path"]), episode_count=1, frame_count=6
        )

    monkeypatch.setattr(cli, "import_lerobot_repo", fake_import_lerobot_repo)

    result = CliRunner().invoke(
        app,
        [
            "import-lerobot",
            "--repo-id",
            "user/dataset",
            "--episodes",
            "0:1",
            "--camera",
            "observation.images.front",
            "--timeline",
            "control",
            "--out",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["timeline"] == "control"
    assert captured["camera_key"] == "observation.images.front"


def test_import_lerobot_cli_rejects_invalid_timeline(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "import-lerobot",
            "--repo-id",
            "user/dataset",
            "--timeline",
            "invalid",
            "--out",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "Invalid value for '--timeline'" in result.output
