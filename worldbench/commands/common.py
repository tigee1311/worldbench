"""Shared CLI helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import click
from rich.console import Console

from worldbench.config import load_config

console = Console()


def load_project_config(path: Path | None):
    try:
        return load_config(path)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc


def save_result(result: Any, output_root: Path) -> Path:
    run_dir = output_root / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    result_path = run_dir / "result.json"
    result.save_json(result_path)
    latest_dir = output_root / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    result.save_json(latest_dir / "result.json")
    return result_path


def prepare_output_dir(output_dir: Path) -> Path:
    if output_dir.exists() and not output_dir.is_dir():
        raise click.ClickException(
            f"Output path exists and is not a directory: {output_dir}"
        )
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise click.ClickException(
            f"Could not create output directory {output_dir}: {exc}"
        ) from exc
    return output_dir


def format_cli_score(value: object) -> str:
    return "N/A" if not isinstance(value, (int, float)) else f"{float(value):.1f}"


def format_cli_delta(value: object) -> str:
    return "N/A" if not isinstance(value, (int, float)) else f"{float(value):+.1f}"


def failure_display_label(failure: dict[str, object]) -> str:
    kind = str(failure.get("kind", "failure"))
    if kind == "overall":
        return "Composite Score"
    if kind == "composite_improvement":
        return "Composite Score improvement"
    if kind == "confidence_lower_bound":
        return "Confidence lower bound"
    return kind.replace("_", " ").title()
