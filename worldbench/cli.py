"""WorldBench command line interface."""

from __future__ import annotations

from datetime import datetime
import importlib.util
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from worldbench.backends.demo import DemoBackend
from worldbench.dashboard import launch_dashboard
from worldbench.dataset import validate_dataset
from worldbench.runners.comparator import compare_results, load_result
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
@click.argument("run_a", type=click.Path(path_type=Path))
@click.argument("run_b", type=click.Path(path_type=Path))
def compare(run_a: Path, run_b: Path) -> None:
    """Compare two WorldBench result JSON files or run directories."""

    comparison = compare_results(run_a, run_b)
    table = Table(title="WorldBench Run Comparison")
    table.add_column("Metric", style="cyan")
    table.add_column("Run A", justify="right")
    table.add_column("Run B", justify="right")
    table.add_column("Delta", justify="right")
    table.add_row("Overall", f"{comparison['run_a_score']:.1f}", f"{comparison['run_b_score']:.1f}", f"{comparison['delta']:+.1f}")
    for name, values in comparison["metrics"].items():
        table.add_row(
            name.replace("_", " ").title(),
            f"{values['run_a']:.1f}",
            f"{values['run_b']:.1f}",
            f"{values['delta']:+.1f}",
        )
    console.print(table)
    console.print(f"Winner: [bold]{comparison['winner']}[/bold]")


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


def _save_result(result, output_root: Path) -> Path:
    run_dir = output_root / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    result_path = run_dir / "result.json"
    result.save_json(result_path)
    latest_dir = output_root / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    result.save_json(latest_dir / "result.json")
    return result_path


if __name__ == "__main__":
    app()
