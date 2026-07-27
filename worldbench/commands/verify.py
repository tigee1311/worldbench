"""Verify saved WorldBench run artifacts."""

from __future__ import annotations

from pathlib import Path

import click

from worldbench.commands.common import console
from worldbench.verification import verify_result_file


@click.command("verify-run")
@click.argument("result_json", type=click.Path(path_type=Path))
def verify_run(result_json: Path) -> None:
    """Verify hashes, configuration, versions, and local inputs for a result JSON."""

    result = verify_result_file(result_json)
    color = "green" if result.status == "PASS" else "red"
    console.print(f"[bold {color}]{result.status}[/bold {color}]")
    console.print(f"Result type: {result.result_type or 'unknown'}")
    console.print(f"Checked input files: {result.checked_input_files}")
    for issue in result.issues:
        label = "ERROR" if issue.severity == "error" else "WARNING"
        style = "red" if issue.severity == "error" else "yellow"
        console.print(f"[{style}]{label}:[/{style}] {issue.message}")
    if result.status == "FAIL":
        raise click.exceptions.Exit(1)
