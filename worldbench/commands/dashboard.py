"""Dashboard CLI command."""

from __future__ import annotations

from pathlib import Path

import click

from worldbench.commands.common import console
from worldbench.dashboard import launch_dashboard


@click.command()
@click.argument("result_json_or_dataset_path", type=click.Path(path_type=Path))
@click.option("--host", default="127.0.0.1", help="Dashboard host.")
@click.option("--port", default=8765, type=int, help="Dashboard port.")
@click.option("--no-open", is_flag=True, help="Do not open a browser automatically.")
def dashboard(
    result_json_or_dataset_path: Path, host: str, port: int, no_open: bool
) -> None:
    """Launch a local WorldBench dashboard."""

    console.print(f"Launching dashboard for [bold]{result_json_or_dataset_path}[/bold]")
    try:
        launch_dashboard(
            result_json_or_dataset_path, host=host, port=port, open_browser=not no_open
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
