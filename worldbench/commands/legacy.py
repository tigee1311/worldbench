"""Compatibility and deprecated development CLI commands."""

from __future__ import annotations

from pathlib import Path

import click
from rich.panel import Panel
from rich.table import Table

from worldbench.backends.benchmark import BenchmarkBackend
from worldbench.backends.demo import DemoBackend
from worldbench.commands.common import (
    console,
    format_cli_delta,
    format_cli_score,
    load_project_config,
    save_result,
)
from worldbench.dataset import validate_dataset
from worldbench.runners.benchmark import run_benchmark_suite, save_benchmark_artifacts
from worldbench.runners.comparator import (
    compare_model_folders,
    compare_result_files,
    compare_results,
    load_result,
    save_comparison_artifacts,
)
from worldbench.runners.evaluator import EvaluationRunner
from worldbench.runners.reporter import save_markdown_report


@click.command(hidden=True)
@click.argument("path", type=click.Path(path_type=Path))
def init(path: Path) -> None:
    """Create a sample WorldBench dataset folder structure."""

    created = DemoBackend().init_structure(path)
    console.print(
        Panel.fit(f"Created WorldBench dataset template at [bold]{created}[/bold]")
    )
    console.print(
        "Add numbered PNG frames under episode_001/frames and predictions under episode_001/predictions."
    )


@click.command(hidden=True)
@click.argument(
    "output",
    required=False,
    default="examples/demo_dataset",
    type=click.Path(path_type=Path),
)
def demo(output: Path) -> None:
    """Generate a synthetic development fixture and model outputs."""

    console.print(
        "[yellow]Deprecated:[/yellow] `worldbench demo` is a development fixture generator and will be removed in 0.5. Use `python scripts/dev/make_synthetic_fixture.py` in a repository checkout."
    )
    created = DemoBackend().create(output)
    console.print(
        Panel.fit(f"Development fixture ready at [bold green]{created}[/bold green]")
    )
    console.print("Try:")
    console.print(f"  worldbench validate {created}")
    console.print(f"  worldbench eval {created} --predictions {created / 'good_model'}")
    console.print(f"  worldbench eval {created} --predictions {created / 'bad_model'}")


@click.command()
@click.argument("dataset_path", type=click.Path(path_type=Path))
def validate(dataset_path: Path) -> None:
    """Validate a WorldBench dataset."""

    report = validate_dataset(dataset_path)
    if report.is_valid:
        console.print(
            f"[bold green]Valid dataset[/bold green]: {report.episode_count} episode(s), {report.frame_count} frame(s)"
        )
    else:
        console.print("[bold red]Dataset is invalid[/bold red]")

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


@click.command(hidden=True)
@click.argument("benchmark_path", required=False, type=click.Path(path_type=Path))
@click.option(
    "--demo",
    is_flag=True,
    hidden=True,
    help="Generate the lightweight synthetic benchmark suite before running it.",
)
@click.option(
    "--output-root",
    type=click.Path(path_type=Path),
    default=Path(".worldbench/benchmarks"),
    help="Benchmark result storage root.",
)
def benchmark(benchmark_path: Path | None, demo: bool, output_root: Path) -> None:
    """Run WorldBench benchmark scenarios."""

    console.print(
        "[yellow]Deprecated:[/yellow] `worldbench benchmark` runs synthetic development scenarios, not a standardized robotics benchmark; it will be removed in 0.5."
    )
    root = benchmark_path or Path("benchmarks")
    if demo:
        root = BenchmarkBackend().create(root)
    if not root.exists():
        raise click.ClickException(
            f"Benchmark path does not exist: {root}. Use --demo to generate synthetic scenarios."
        )

    payload = run_benchmark_suite(root)
    saved = save_benchmark_artifacts(payload, output_root)
    _print_benchmark_summary(payload)
    console.print(f"[green]Saved benchmark:[/green] {saved['json']}")
    console.print(f"[green]Markdown report:[/green] {saved['markdown']}")


@click.command(name="eval")
@click.argument("dataset_path", type=click.Path(path_type=Path))
@click.option(
    "--predictions",
    "-p",
    type=click.Path(path_type=Path),
    default=None,
    help="Prediction folder or model run root.",
)
@click.option(
    "--output-root",
    type=click.Path(path_type=Path),
    default=Path(".worldbench/runs"),
    help="Run storage root.",
)
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
def eval_cmd(
    dataset_path: Path,
    predictions: Path | None,
    output_root: Path,
    config_path: Path | None,
) -> None:
    """Run all WorldBench metrics and save result.json."""

    config, _ = load_project_config(config_path)
    runner = EvaluationRunner(dataset_path, predictions=predictions)
    result = runner.run(config=config)
    result_path = save_result(result, output_root)
    result.print_summary()
    console.print(f"[green]Saved result:[/green] {result_path}")
    console.print(
        f"[green]Latest alias:[/green] {output_root / 'latest' / 'result.json'}"
    )


@click.command()
@click.argument("target", type=click.Path(path_type=Path))
@click.argument("run_b", required=False, type=click.Path(path_type=Path))
@click.option(
    "--models",
    nargs=2,
    metavar="MODEL_A MODEL_B",
    help="Compare two prediction folders inside a dataset, e.g. --models good_model bad_model.",
)
@click.option(
    "--output-root",
    type=click.Path(path_type=Path),
    default=Path(".worldbench/comparisons"),
    help="Comparison storage root.",
)
def compare(
    target: Path, run_b: Path | None, models: tuple[str, str] | None, output_root: Path
) -> None:
    """Compare result files or two model folders inside a dataset."""

    if models is not None:
        comparison = compare_model_folders(target, models[0], models[1])
        saved = save_comparison_artifacts(comparison, output_root)
        _print_rich_comparison(comparison)
        console.print(f"[green]Saved comparison:[/green] {saved['json']}")
        console.print(f"[green]Markdown report:[/green] {saved['markdown']}")
        return

    if run_b is None:
        raise click.ClickException(
            "Provide two result JSON files, or use --models MODEL_A MODEL_B with a dataset path."
        )

    legacy = compare_results(target, run_b)
    comparison = compare_result_files(target, run_b)
    saved = save_comparison_artifacts(comparison, output_root)
    table = Table(title="WorldBench Run Comparison")
    table.add_column("Metric", style="cyan")
    table.add_column("Run A", justify="right")
    table.add_column("Run B", justify="right")
    table.add_column("Delta", justify="right")
    table.add_row(
        "Composite Score",
        f"{legacy['run_a_score']:.1f}",
        f"{legacy['run_b_score']:.1f}",
        f"{legacy['delta']:+.1f}",
    )
    for name, values in legacy["metrics"].items():
        table.add_row(
            name.replace("_", " ").title(),
            format_cli_score(values["run_a"]),
            format_cli_score(values["run_b"]),
            format_cli_delta(values["delta"]),
        )
    console.print(table)
    console.print(f"Winner: [bold]{legacy['winner']}[/bold]")
    console.print(f"[green]Saved comparison:[/green] {saved['json']}")


@click.command()
@click.argument("result_json", type=click.Path(path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None)
def report(result_json: Path, output: Path | None) -> None:
    """Generate a Markdown report from a result JSON file."""

    result = load_result(result_json)
    output_path = (
        output
        or (result_json.parent if result_json.is_file() else result_json) / "report.md"
    )
    saved = save_markdown_report(result, output_path)
    console.print(f"[green]Saved report:[/green] {saved}")


@click.command("make-demo-video", hidden=True)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("assets/demo"),
    help="Demo asset output directory.",
)
def make_demo_video(output_dir: Path) -> None:
    """Generate README demo MP4, GIF, and thumbnail assets."""

    raise click.ClickException(
        "Deprecated maintainer utility. Run `python scripts/dev/make_demo_video.py` from a repository checkout."
    )


@click.command("make-screenshots", hidden=True)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("assets/screenshots"),
    help="Screenshot asset output directory.",
)
def make_screenshots(output_dir: Path) -> None:
    """Generate README dashboard and report screenshot assets."""

    raise click.ClickException(
        "Deprecated maintainer utility. Run `python scripts/dev/make_screenshots.py` from a repository checkout."
    )


def _print_rich_comparison(comparison: dict[str, object]) -> None:
    label_a = str(comparison["label_a"])
    label_b = str(comparison["label_b"])
    overall = comparison["overall"]
    assert isinstance(overall, dict)
    metrics = comparison["metrics"]
    assert isinstance(metrics, list)
    largest_gaps = comparison["largest_gaps"]
    assert isinstance(largest_gaps, list)

    winner = str(overall["winner"])
    loser = str(overall["loser"])
    if winner == "tie":
        summary = f"[bold]{label_a}[/bold] and [bold]{label_b}[/bold] are tied."
    else:
        summary = (
            f"[bold]{winner}[/bold] beats [bold]{loser}[/bold] by "
            f"[bold green]+{float(overall['winner_margin']):.1f}[/bold green] Composite Score points."
        )
    console.print(Panel.fit(summary, title="WorldBench Model Comparison"))

    table = Table(title="Metric Deltas")
    table.add_column("Metric", style="cyan")
    table.add_column(label_a, justify="right")
    table.add_column(label_b, justify="right")
    table.add_column("Delta", justify="right")
    table.add_row(
        "Composite Score",
        f"{float(overall['score_a']):.1f}",
        f"{float(overall['score_b']):.1f}",
        f"{float(overall['delta']):+.1f}",
    )
    for metric in metrics:
        table.add_row(
            str(metric["label"]),
            format_cli_score(metric["score_a"]),
            format_cli_score(metric["score_b"]),
            format_cli_delta(metric["delta"]),
        )
    console.print(table)

    gap_lines = [
        f"- {metric['label']}: +{float(metric['winner_delta']):.1f}"
        for metric in largest_gaps
    ]
    console.print("[bold]Largest gaps:[/bold]")
    console.print("\n".join(gap_lines))
    console.print("\n[bold]Conclusion:[/bold]")
    console.print(str(comparison["conclusion"]))
    coverage = comparison.get("coverage", {})
    if isinstance(coverage, dict):
        console.print("\n[bold]Metric coverage:[/bold]")
        for key, label in (("a", label_a), ("b", label_b)):
            item = coverage.get(key, {})
            if isinstance(item, dict):
                console.print(
                    f"{label}: {item.get('available_metric_count', 0)}/"
                    f"{item.get('configured_metric_count', 0)} metrics, "
                    f"{float(item.get('configured_weight_coverage', 0.0)):.0%} configured weight"
                )


def _print_benchmark_summary(payload: dict[str, object]) -> None:
    console.print(Panel.fit("[bold]WorldBench Demo Benchmark[/bold]"))
    console.print(
        f"[bold]good_model average:[/bold] {float(payload['good_model_average']):.1f}/100"
    )
    console.print(
        f"[bold]bad_model average:[/bold] {float(payload['bad_model_average']):.1f}/100"
    )
    console.print(f"[bold]overall delta:[/bold] +{float(payload['overall_delta']):.1f}")

    scenarios = payload["scenarios"]
    assert isinstance(scenarios, list)
    table = Table(title="Benchmark Scenarios")
    table.add_column("Scenario", style="cyan")
    table.add_column("good_model", justify="right")
    table.add_column("bad_model", justify="right")
    table.add_column("Delta", justify="right")
    for scenario in scenarios:
        assert isinstance(scenario, dict)
        good = scenario["good_model"]
        bad = scenario["bad_model"]
        assert isinstance(good, dict)
        assert isinstance(bad, dict)
        table.add_row(
            str(scenario["name"]),
            f"{float(good['score']):.1f}",
            f"{float(bad['score']):.1f}",
            f"{float(scenario['delta']):+.1f}",
        )
    console.print(table)

    failure_modes = payload["largest_failure_modes"]
    assert isinstance(failure_modes, list)
    console.print("[bold]Largest failure modes:[/bold]")
    console.print("\n".join(f"- {item}" for item in failure_modes))
