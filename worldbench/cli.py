"""WorldBench command line interface."""

from __future__ import annotations

from datetime import datetime
import importlib.util
from pathlib import Path
import tempfile

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from worldbench.backends.benchmark import BenchmarkBackend
from worldbench.backends.demo import DemoBackend
from worldbench.backends.lerobot import (
    create_lerobot_style_demo_source,
    import_lerobot_repo,
    import_lerobot_style,
    parse_episode_selection,
)
from worldbench.dashboard import launch_dashboard
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

console = Console()


@click.group(help="Evaluate robotics world models for control-useful prediction quality.")
def app() -> None:
    pass


@app.command()
@click.argument("path", type=click.Path(path_type=Path))
def init(path: Path) -> None:
    """Create a sample WorldBench dataset folder structure."""

    created = DemoBackend().init_structure(path)
    console.print(Panel.fit(f"Created WorldBench dataset template at [bold]{created}[/bold]"))
    console.print("Add numbered PNG frames under episode_001/frames and predictions under episode_001/predictions.")


@app.command()
@click.argument("output", required=False, default="examples/demo_dataset", type=click.Path(path_type=Path))
def demo(output: Path) -> None:
    """Generate a complete synthetic demo dataset and good/bad model outputs."""

    created = DemoBackend().create(output)
    console.print(Panel.fit(f"Demo dataset ready at [bold green]{created}[/bold green]"))
    console.print("Try:")
    console.print(f"  worldbench validate {created}")
    console.print(f"  worldbench eval {created} --predictions {created / 'good_model'}")
    console.print(f"  worldbench eval {created} --predictions {created / 'bad_model'}")


@app.command()
@click.argument("dataset_path", type=click.Path(path_type=Path))
def validate(dataset_path: Path) -> None:
    """Validate a WorldBench dataset."""

    report = validate_dataset(dataset_path)
    if report.is_valid:
        console.print(f"[bold green]Valid dataset[/bold green]: {report.episode_count} episode(s), {report.frame_count} frame(s)")
    else:
        console.print("[bold red]Dataset is invalid[/bold red]")

    if report.issues:
        table = Table(title="Validation Issues")
        table.add_column("Level")
        table.add_column("Path")
        table.add_column("Message")
        for issue in report.issues:
            style = "red" if issue.level == "error" else "yellow"
            table.add_row(f"[{style}]{issue.level}[/{style}]", issue.path or "", issue.message)
        console.print(table)

    raise click.exceptions.Exit(0 if report.is_valid else 1)


@app.command()
@click.argument("benchmark_path", required=False, type=click.Path(path_type=Path))
@click.option("--demo", is_flag=True, help="Generate the lightweight synthetic benchmark suite before running it.")
@click.option(
    "--output-root",
    type=click.Path(path_type=Path),
    default=Path(".worldbench/benchmarks"),
    help="Benchmark result storage root.",
)
def benchmark(benchmark_path: Path | None, demo: bool, output_root: Path) -> None:
    """Run WorldBench benchmark scenarios."""

    root = benchmark_path or Path("benchmarks")
    if demo:
        root = BenchmarkBackend().create(root)
    if not root.exists():
        raise click.ClickException(f"Benchmark path does not exist: {root}. Use --demo to generate synthetic scenarios.")

    payload = run_benchmark_suite(root)
    saved = save_benchmark_artifacts(payload, output_root)
    _print_benchmark_summary(payload)
    console.print(f"[green]Saved benchmark:[/green] {saved['json']}")
    console.print(f"[green]Markdown report:[/green] {saved['markdown']}")


@app.command("import-lerobot")
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
        "Experimental LeRobot-style import remains available for local folders and --demo."
    )

    try:
        if demo:
            if repo_id is not None:
                raise click.ClickException("--demo cannot be combined with --repo-id.")
            with tempfile.TemporaryDirectory(prefix="worldbench-lerobot-style-") as tmpdir:
                source = create_lerobot_style_demo_source(Path(tmpdir) / "source")
                report = import_lerobot_style(source, output_path)
        elif repo_id is not None:
            if input_path is not None:
                raise click.ClickException("Do not provide input_path when using --repo-id.")
            selected_episodes = parse_episode_selection(episodes)
            report = import_lerobot_repo(
                repo_id,
                output_path,
                episodes=selected_episodes,
                camera_key=camera_key,
                timeline=timeline,
            )
        else:
            if input_path is None:
                raise click.ClickException("Provide input_path, use --demo, or use --repo-id.")
            console.print("Using legacy local LeRobot-style folder converter.")
            report = import_lerobot_style(input_path, output_path)
    except click.ClickException:
        raise
    except Exception as exc:  # noqa: BLE001
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
            table.add_row(f"[{style}]{issue.level}[/{style}]", issue.path or "", issue.message)
        console.print(table)
    raise click.exceptions.Exit(0 if report.is_valid else 1)


@app.command(name="eval")
@click.argument("dataset_path", type=click.Path(path_type=Path))
@click.option("--predictions", "-p", type=click.Path(path_type=Path), default=None, help="Prediction folder or model run root.")
@click.option(
    "--output-root",
    type=click.Path(path_type=Path),
    default=Path(".worldbench/runs"),
    help="Run storage root.",
)
def eval_cmd(dataset_path: Path, predictions: Path | None, output_root: Path) -> None:
    """Run all WorldBench metrics and save result.json."""

    runner = EvaluationRunner(dataset_path, predictions=predictions)
    result = runner.run()
    result_path = _save_result(result, output_root)
    result.print_summary()
    console.print(f"[green]Saved result:[/green] {result_path}")
    console.print(f"[green]Latest alias:[/green] {output_root / 'latest' / 'result.json'}")


@app.command()
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
def compare(target: Path, run_b: Path | None, models: tuple[str, str] | None, output_root: Path) -> None:
    """Compare result files or two model folders inside a dataset."""

    if models is not None:
        comparison = compare_model_folders(target, models[0], models[1])
        saved = save_comparison_artifacts(comparison, output_root)
        _print_rich_comparison(comparison)
        console.print(f"[green]Saved comparison:[/green] {saved['json']}")
        console.print(f"[green]Markdown report:[/green] {saved['markdown']}")
        return

    if run_b is None:
        raise click.ClickException("Provide two result JSON files, or use --models MODEL_A MODEL_B with a dataset path.")

    legacy = compare_results(target, run_b)
    comparison = compare_result_files(target, run_b)
    saved = save_comparison_artifacts(comparison, output_root)
    table = Table(title="WorldBench Run Comparison")
    table.add_column("Metric", style="cyan")
    table.add_column("Run A", justify="right")
    table.add_column("Run B", justify="right")
    table.add_column("Delta", justify="right")
    table.add_row(
        "Overall",
        f"{legacy['run_a_score']:.1f}",
        f"{legacy['run_b_score']:.1f}",
        f"{legacy['delta']:+.1f}",
    )
    for name, values in legacy["metrics"].items():
        table.add_row(
            name.replace("_", " ").title(),
            f"{values['run_a']:.1f}",
            f"{values['run_b']:.1f}",
            f"{values['delta']:+.1f}",
        )
    console.print(table)
    console.print(f"Winner: [bold]{legacy['winner']}[/bold]")
    console.print(f"[green]Saved comparison:[/green] {saved['json']}")


@app.command()
@click.argument("result_json", type=click.Path(path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None)
def report(result_json: Path, output: Path | None) -> None:
    """Generate a Markdown report from a result JSON file."""

    result = load_result(result_json)
    output_path = output or (result_json.parent if result_json.is_file() else result_json) / "report.md"
    saved = save_markdown_report(result, output_path)
    console.print(f"[green]Saved report:[/green] {saved}")


@app.command()
@click.argument("result_json_or_dataset_path", type=click.Path(path_type=Path))
@click.option("--host", default="127.0.0.1", help="Dashboard host.")
@click.option("--port", default=8765, type=int, help="Dashboard port.")
@click.option("--no-open", is_flag=True, help="Do not open a browser automatically.")
def dashboard(result_json_or_dataset_path: Path, host: str, port: int, no_open: bool) -> None:
    """Launch a local WorldBench dashboard."""

    console.print(f"Launching dashboard for [bold]{result_json_or_dataset_path}[/bold]")
    try:
        launch_dashboard(result_json_or_dataset_path, host=host, port=port, open_browser=not no_open)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc


@app.command("make-demo-video")
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("assets/demo"), help="Demo asset output directory.")
def make_demo_video(output_dir: Path) -> None:
    """Generate README demo MP4, GIF, and thumbnail assets."""

    script_path = Path(__file__).resolve().parents[1] / "scripts" / "make_demo_video.py"
    if not script_path.is_file():
        raise click.ClickException(
            "Could not find scripts/make_demo_video.py. Run this command from the WorldBench repository checkout."
        )
    spec = importlib.util.spec_from_file_location("worldbench_make_demo_video", script_path)
    if spec is None or spec.loader is None:
        raise click.ClickException(f"Could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    build_demo_video = module.make_demo_video

    outputs = build_demo_video(output_dir)
    console.print("[bold green]Generated demo assets[/bold green]")
    for label, path in outputs.items():
        console.print(f"  {label}: {path}")


@app.command("make-screenshots")
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("assets/screenshots"),
    help="Screenshot asset output directory.",
)
def make_screenshots(output_dir: Path) -> None:
    """Generate README dashboard and report screenshot assets."""

    script_path = Path(__file__).resolve().parents[1] / "scripts" / "make_screenshots.py"
    if not script_path.is_file():
        raise click.ClickException(
            "Could not find scripts/make_screenshots.py. Run this command from the WorldBench repository checkout."
        )
    spec = importlib.util.spec_from_file_location("worldbench_make_screenshots", script_path)
    if spec is None or spec.loader is None:
        raise click.ClickException(f"Could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    build_screenshots = module.make_screenshots

    outputs = build_screenshots(output_dir)
    console.print("[bold green]Generated screenshot assets[/bold green]")
    for label, path in outputs.items():
        console.print(f"  {label}: {path}")


def _save_result(result, output_root: Path) -> Path:
    run_dir = output_root / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    result_path = run_dir / "result.json"
    result.save_json(result_path)
    latest_dir = output_root / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    result.save_json(latest_dir / "result.json")
    return result_path


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
            f"[bold green]+{float(overall['winner_margin']):.1f}[/bold green] overall points."
        )
    console.print(Panel.fit(summary, title="WorldBench Model Comparison"))

    table = Table(title="Metric Deltas")
    table.add_column("Metric", style="cyan")
    table.add_column(label_a, justify="right")
    table.add_column(label_b, justify="right")
    table.add_column("Delta", justify="right")
    table.add_row(
        "Overall",
        f"{float(overall['score_a']):.1f}",
        f"{float(overall['score_b']):.1f}",
        f"{float(overall['delta']):+.1f}",
    )
    for metric in metrics:
        table.add_row(
            str(metric["label"]),
            f"{float(metric['score_a']):.1f}",
            f"{float(metric['score_b']):.1f}",
            f"{float(metric['delta']):+.1f}",
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


def _print_benchmark_summary(payload: dict[str, object]) -> None:
    console.print(Panel.fit("[bold]WorldBench Demo Benchmark[/bold]"))
    console.print(f"[bold]good_model average:[/bold] {float(payload['good_model_average']):.1f}/100")
    console.print(f"[bold]bad_model average:[/bold] {float(payload['bad_model_average']):.1f}/100")
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


if __name__ == "__main__":
    app()
