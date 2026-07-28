"""Batch checkpoint-evaluation CLI command."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
from rich.panel import Panel
from rich.table import Table

from worldbench.commands.common import console, load_project_config
from worldbench.runners.regression import evaluate_video_batch
from worldbench.runners.video import VideoEvaluationError


@click.command("eval-batch")
@click.option(
    "--ground-truth",
    "ground_truth",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory of ground-truth episode videos.",
)
@click.option(
    "--predictions",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory of predicted episode videos for one checkpoint.",
)
@click.option(
    "--name",
    default=None,
    help="Checkpoint name. Also controls the default JSON copy name.",
)
@click.option(
    "--skip-context",
    default=0,
    show_default=True,
    type=int,
    help="Number of leading context frames to exclude from every episode.",
)
@click.option(
    "--output-root",
    type=click.Path(path_type=Path),
    default=Path(".worldbench/batches"),
    help="Batch result storage root.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Optional direct JSON output path. Defaults to <name>.json when --name is set.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to worldbench.yml; auto-detected in the current directory.",
)
def eval_batch(
    ground_truth: Path,
    predictions: Path,
    name: str | None,
    skip_context: int,
    output_root: Path,
    output: Path | None,
    config_path: Path | None,
) -> None:
    """Evaluate one checkpoint across a directory of episode videos."""

    try:
        config, _ = load_project_config(config_path)
        payload, paths = evaluate_video_batch(
            ground_truth,
            predictions,
            name=name,
            skip_context=skip_context,
            output_root=output_root,
            output=output,
            config=config,
        )
    except (ValueError, VideoEvaluationError) as exc:
        raise click.UsageError(str(exc)) from exc

    print_batch_summary(payload)
    console.print(f"[green]Saved batch result:[/green] {paths['json']}")
    console.print(f"[green]Latest alias:[/green] {paths['latest_json']}")
    if "output_json" in paths:
        console.print(f"[green]Checkpoint JSON:[/green] {paths['output_json']}")


def print_batch_summary(payload: dict[str, Any]) -> None:
    checkpoint = str(payload["checkpoint_name"])
    aggregate = payload["aggregate"]
    assert isinstance(aggregate, dict)
    overall = aggregate["overall"]
    assert isinstance(overall, dict)
    metrics = aggregate["metrics"]
    assert isinstance(metrics, dict)

    console.print(Panel.fit(f"[bold]Checkpoint:[/bold] {checkpoint}"))
    console.print(f"[bold]Episodes evaluated:[/bold] {int(payload['episode_count'])}")
    console.print(f"[bold]Composite Score mean:[/bold] {float(overall['mean']):.2f}")
    console.print(
        f"[bold]Composite Score median:[/bold] {float(overall['median']):.2f}"
    )
    console.print(f"[bold]Standard deviation:[/bold] {float(overall['std']):.1f}")
    console.print(f"[bold]Minimum:[/bold] {float(overall['min']):.1f}")
    console.print(f"[bold]Maximum:[/bold] {float(overall['max']):.1f}")
    coverage = payload.get("coverage", {})
    if isinstance(coverage, dict):
        console.print(
            f"[bold]Metric coverage:[/bold] {coverage.get('available_metric_count', 0)} of "
            f"{coverage.get('configured_metric_count', 0)} configured metrics"
        )
        console.print(
            f"[bold]Configured weight coverage:[/bold] "
            f"{float(coverage.get('configured_weight_coverage', 0.0)):.0%}"
        )
        available = ", ".join(
            str(name) for name in coverage.get("available_metrics", [])
        )
        unavailable = ", ".join(
            str(name) for name in coverage.get("unsupported_metrics", [])
        )
        console.print(f"[bold]Available metrics:[/bold] {available or 'None'}")
        console.print(f"[bold]Unavailable metrics:[/bold] {unavailable or 'None'}")

    table = Table(title="Metric Aggregates")
    table.add_column("Metric", style="cyan")
    table.add_column("Mean", justify="right")
    table.add_column("Available", justify="right")
    for name, stats in metrics.items():
        assert isinstance(stats, dict)
        if stats.get("status") == "available":
            table.add_row(
                name.replace("_", " ").title(),
                f"{float(stats['mean']):.1f}",
                f"{int(stats['available_count'])}/{int(stats['total_count'])}",
            )
        else:
            table.add_row(
                name.replace("_", " ").title(),
                "N/A",
                f"0/{int(stats['total_count'])}",
            )
    console.print(table)

    worst = payload.get("worst_episodes")
    if isinstance(worst, list) and worst:
        console.print("[bold]Worst episodes:[/bold]")
        for item in worst[:5]:
            if isinstance(item, dict):
                console.print(f"  {item['episode_id']}: {float(item['score']):.1f}")
