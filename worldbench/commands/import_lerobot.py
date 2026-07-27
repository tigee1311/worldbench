"""LeRobot import CLI command."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import click
from rich.table import Table

from worldbench.backends.lerobot import (
    create_lerobot_style_demo_source,
    import_lerobot_repo,
    import_lerobot_style,
    parse_episode_selection,
)
from worldbench.commands.common import console


@click.command("import-lerobot")
@click.argument("input_path", required=False, type=click.Path(path_type=Path))
@click.option(
    "--out",
    "output_path",
    required=True,
    type=click.Path(path_type=Path),
    help="WorldBench dataset output path.",
)
@click.option(
    "--demo",
    is_flag=True,
    hidden=True,
    help="Generate and import a tiny synthetic LeRobot-style source folder.",
)
@click.option(
    "--repo-id",
    default=None,
    help="Hugging Face LeRobot dataset repo id, e.g. username/dataset.",
)
@click.option("--episodes", default=None, help="Episode selection, e.g. 0,2,4 or 0:5.")
@click.option(
    "--camera",
    "camera_key",
    default=None,
    help="LeRobot camera key, e.g. observation.images.front.",
)
@click.option(
    "--timeline",
    type=click.Choice(["video", "control"]),
    default="video",
    show_default=True,
    help="LeRobot timeline: video exports unique camera frames; control exports source control rows.",
)
def import_lerobot(
    input_path: Path | None,
    output_path: Path,
    demo: bool,
    repo_id: str | None,
    episodes: str | None,
    camera_key: str | None,
    timeline: str,
) -> None:
    """Import LeRobot data into WorldBench format."""

    console.print("[bold]LeRobot import[/bold]")
    console.print(
        "Native LeRobot import is available with --repo-id; the local LeRobot-style folder converter remains available for --demo and local folders."
    )

    try:
        if demo:
            console.print(
                "[yellow]Deprecated:[/yellow] `import-lerobot --demo` is a development fixture path and will be removed in 0.5."
            )
            if repo_id is not None:
                raise click.ClickException("--demo cannot be combined with --repo-id.")
            with tempfile.TemporaryDirectory(
                prefix="worldbench-lerobot-style-"
            ) as tmpdir:
                source = create_lerobot_style_demo_source(Path(tmpdir) / "source")
                report = import_lerobot_style(source, output_path)
        elif repo_id is not None:
            if input_path is not None:
                raise click.ClickException(
                    "Do not provide input_path when using --repo-id."
                )
            selected_episodes = parse_episode_selection(episodes)
            repo_importer = _repo_importer()
            report = repo_importer(
                repo_id,
                output_path,
                episodes=selected_episodes,
                camera_key=camera_key,
                timeline=timeline,
            )
        else:
            if input_path is None:
                raise click.ClickException(
                    "Provide input_path, use --demo, or use --repo-id."
                )
            console.print("Using legacy local LeRobot-style folder converter.")
            report = import_lerobot_style(input_path, output_path)
    except click.ClickException:
        raise
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    if report.is_valid:
        console.print(
            f"[bold green]Imported dataset[/bold green]: {output_path} "
            f"({report.episode_count} episode, {report.frame_count} frame(s))"
        )
    else:
        console.print(
            f"[bold red]Imported dataset has validation errors[/bold red]: {output_path}"
        )

    if report.issues:
        table = Table(title="Validation Issues")
        table.add_column("Level")
        table.add_column("Path")
        table.add_column("Message")
        for issue in report.issues:
            style = "red" if issue.level == "error" else "yellow"
            table.add_row(
                f"[{style}]{issue.level}[/{style}]", issue.path or "", issue.message
            )
        console.print(table)
    raise click.exceptions.Exit(0 if report.is_valid else 1)


def _repo_importer():
    cli_module = sys.modules.get("worldbench.cli")
    if cli_module is None:
        return import_lerobot_repo
    return getattr(cli_module, "import_lerobot_repo", import_lerobot_repo)
