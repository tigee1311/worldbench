"""Saved-video CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
from rich.panel import Panel

from worldbench.commands.common import (
    console,
    load_project_config,
    prepare_output_dir,
    save_result,
)
from worldbench.runners.reporter import save_markdown_report
from worldbench.runners.video import (
    VideoEvaluationError,
    create_saved_video_demo_pair,
    evaluate_video_pair,
)
from worldbench.runners.video import (
    save_comparison_artifacts as save_video_comparison_artifacts,
)


@click.command("eval-video")
@click.option(
    "--ground-truth",
    "ground_truth",
    required=True,
    type=click.Path(path_type=Path),
    help="Ground-truth rollout video containing context and future frames.",
)
@click.option(
    "--prediction",
    required=True,
    type=click.Path(path_type=Path),
    help="Predicted video containing the same context and future frame count.",
)
@click.option(
    "--skip-context",
    default=0,
    show_default=True,
    type=int,
    help="Number of leading context frames to exclude from scoring.",
)
@click.option(
    "--name", default=None, help="Optional display name for this video evaluation."
)
@click.option(
    "--output-root",
    type=click.Path(path_type=Path),
    default=Path(".worldbench/runs"),
    help="Run storage root.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to worldbench.yml; auto-detected in the current directory.",
)
def eval_video(
    ground_truth: Path,
    prediction: Path,
    skip_context: int,
    name: str | None,
    output_root: Path,
    config_path: Path | None,
) -> None:
    """Evaluate one predicted future video against one ground-truth video."""

    try:
        config, _ = load_project_config(config_path)
        result = evaluate_video_pair(
            ground_truth,
            prediction,
            skip_context=skip_context,
            name=name,
            config=config,
        )
    except VideoEvaluationError as exc:
        raise click.ClickException(str(exc)) from exc

    result_path = save_result(result, output_root)
    provenance = result.provenance
    console.print(Panel.fit("[bold]WorldBench Video Evaluation[/bold]"))
    console.print(
        f"Ground truth frames: {provenance['ground_truth_frame_count']} | "
        f"Prediction frames: {provenance['prediction_frame_count']} | "
        f"Evaluated future frames: {provenance['evaluated_frame_count']}"
    )
    result.print_summary()
    console.print(f"[green]Saved result:[/green] {result_path}")
    console.print(f"[green]Saved run directory:[/green] {result_path.parent}")


@click.command("eval-videos")
@click.option(
    "--ground-truth",
    "ground_truth",
    type=click.Path(path_type=Path),
    default=None,
    help="Ground-truth future video. Required unless --demo is used.",
)
@click.option(
    "--reference",
    "reference",
    type=click.Path(path_type=Path),
    default=None,
    help="Backward-compatible alias for --ground-truth.",
)
@click.option(
    "--prediction",
    type=click.Path(path_type=Path),
    default=None,
    help="Predicted or generated video. Required unless --demo is used.",
)
@click.option(
    "--output",
    "output_dir",
    type=click.Path(path_type=Path),
    default=Path("worldbench-video-results"),
    show_default=True,
    help="Directory for result.json, summary.md, and comparison artifacts.",
)
@click.option(
    "--skip-context",
    default=0,
    show_default=True,
    type=int,
    help="Number of leading context frames to exclude from scoring.",
)
@click.option(
    "--name", default=None, help="Optional display name for this video evaluation."
)
@click.option(
    "--save-comparison/--no-save-comparison",
    default=True,
    show_default=True,
    help="Save a small ground-truth-vs-prediction contact sheet when possible.",
)
@click.option(
    "--demo",
    is_flag=True,
    help="Generate and evaluate a tiny built-in MP4 pair without user files.",
)
@click.option(
    "--max-frame-mismatch-ratio",
    default=0.25,
    show_default=True,
    type=click.FloatRange(min=0.0),
    hidden=True,
    help="Advanced: largest tolerated future-frame mismatch ratio before failing.",
)
@click.option(
    "--max-frame-mismatch-frames",
    default=8,
    show_default=True,
    type=click.IntRange(min=0),
    hidden=True,
    help="Advanced: largest tolerated absolute future-frame mismatch before failing.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to worldbench.yml; auto-detected in the current directory.",
)
def eval_videos(
    ground_truth: Path | None,
    reference: Path | None,
    prediction: Path | None,
    output_dir: Path,
    skip_context: int,
    name: str | None,
    save_comparison: bool,
    demo: bool,
    max_frame_mismatch_ratio: float,
    max_frame_mismatch_frames: int,
    config_path: Path | None,
) -> None:
    """Evaluate one saved predicted robot future against ground truth.

    \b
    Example:
      worldbench eval-videos \\
        --ground-truth ground_truth.mp4 \\
        --prediction predicted_future.mp4 \\
        --output results/
    """

    if demo:
        if ground_truth is not None or reference is not None or prediction is not None:
            raise click.UsageError(
                "--demo cannot be combined with --ground-truth, --reference, or --prediction."
            )
        output_dir = prepare_output_dir(output_dir)
        try:
            ground_truth, prediction = create_saved_video_demo_pair(
                output_dir / "demo_inputs"
            )
        except VideoEvaluationError as exc:
            raise click.ClickException(str(exc)) from exc
        console.print(
            "[yellow]Synthetic demonstration data:[/yellow] generated "
            f"{ground_truth} and {prediction}"
        )
        console.print(
            "[yellow]Demo notice:[/yellow] Not a model-quality result. Not a benchmark result."
        )
    else:
        if ground_truth is not None and reference is not None:
            raise click.UsageError(
                "Use exactly one of --ground-truth or --reference, not both."
            )
        if ground_truth is None and reference is None:
            raise click.UsageError(
                "Provide exactly one of --ground-truth or --reference, or use --demo."
            )
        if prediction is None:
            raise click.UsageError(
                "Provide --prediction, or use --demo for a tiny built-in example."
            )
        ground_truth = ground_truth or reference
        output_dir = prepare_output_dir(output_dir)

    assert ground_truth is not None
    assert prediction is not None
    try:
        config, _ = load_project_config(config_path)
        result = evaluate_video_pair(
            ground_truth,
            prediction,
            skip_context=skip_context,
            name=name,
            config=config,
            alignment="safe",
            max_frame_mismatch_ratio=max_frame_mismatch_ratio,
            max_frame_mismatch_frames=max_frame_mismatch_frames,
        )
    except VideoEvaluationError as exc:
        raise click.ClickException(str(exc)) from exc

    if demo:
        result.provenance["demo"] = True
        result.provenance["demo_notice"] = [
            "Synthetic demonstration data.",
            "Not a model-quality result.",
            "Not a benchmark result.",
        ]

    result_path = result.save_json(output_dir / "result.json")
    report_path = _save_saved_video_report(result, output_dir / "summary.md")
    artifact_paths: dict[str, Path] = {}
    if save_comparison:
        try:
            artifact_paths = save_video_comparison_artifacts(
                ground_truth,
                prediction,
                output_dir / "artifacts",
                skip_context=skip_context,
                alignment="safe",
                max_frame_mismatch_ratio=max_frame_mismatch_ratio,
                max_frame_mismatch_frames=max_frame_mismatch_frames,
            )
        except VideoEvaluationError as exc:
            console.print(f"[yellow]Comparison artifact skipped:[/yellow] {exc}")

    _print_saved_video_summary(
        result,
        ground_truth=ground_truth,
        prediction=prediction,
        result_path=result_path,
        report_path=report_path,
        artifact_paths=artifact_paths,
    )


def _print_saved_video_summary(
    result: Any,
    *,
    ground_truth: Path,
    prediction: Path,
    result_path: Path,
    report_path: Path,
    artifact_paths: dict[str, Path],
) -> None:
    provenance = result.provenance
    alignment = provenance.get("alignment", {})
    warnings = provenance.get("alignment_warnings", [])
    console.print(Panel.fit("[bold]WorldBench Saved Video Evaluation[/bold]"))
    if provenance.get("demo"):
        console.print("[yellow]Synthetic demonstration data[/yellow]")
        console.print(
            "[yellow]Not a model-quality result. Not a benchmark result.[/yellow]"
        )
    console.print(f"[bold]Ground truth:[/bold] {ground_truth}")
    console.print(f"[bold]Prediction:[/bold] {prediction}")
    console.print(
        "[bold]Frames:[/bold] "
        f"ground truth {provenance.get('ground_truth_frame_count')} | "
        f"prediction {provenance.get('prediction_frame_count')} | "
        f"scored {provenance.get('evaluated_frame_count')}"
    )
    if isinstance(alignment, dict):
        console.print(
            "[bold]Alignment:[/bold] "
            f"{alignment.get('frame_alignment', 'unknown')} | "
            f"{alignment.get('resolution_policy', 'unknown')} | "
            f"{alignment.get('fps_policy', 'unknown')}"
        )
    if isinstance(warnings, list) and warnings:
        console.print("[yellow]Alignment notes:[/yellow]")
        for warning in warnings:
            console.print(f"  - {warning}")

    result.print_summary()
    console.print(f"[green]Saved JSON:[/green] {result_path}")
    console.print(f"[green]Saved Markdown:[/green] {report_path}")
    if artifact_paths:
        for label, path in artifact_paths.items():
            artifact_label = (
                "comparison image" if label == "comparison_image" else label
            )
            console.print(f"[green]Saved {artifact_label}:[/green] {path}")


def _save_saved_video_report(result: Any, path: Path) -> Path:
    report_path = save_markdown_report(result, path)
    provenance = result.provenance
    alignment = provenance.get("alignment", {})
    warnings = provenance.get("alignment_warnings", [])
    demo_notice = provenance.get("demo_notice", [])
    lines = [
        "",
        "## Saved Video Provenance",
        "",
        f"- Ground truth path: `{provenance.get('ground_truth_path')}`",
        f"- Prediction path: `{provenance.get('prediction_path')}`",
        f"- Original ground-truth frame count: `{provenance.get('ground_truth_original_frame_count')}`",
        f"- Original prediction frame count: `{provenance.get('prediction_original_frame_count')}`",
        f"- Evaluated frame count: `{provenance.get('evaluated_frame_count')}`",
        f"- Frames trimmed from ground truth: `{provenance.get('ground_truth_frames_trimmed')}`",
        f"- Frames trimmed from prediction: `{provenance.get('prediction_frames_trimmed')}`",
        f"- Original ground-truth resolution: `{provenance.get('ground_truth_original_resolution')}`",
        f"- Original prediction resolution: `{provenance.get('prediction_original_resolution')}`",
        f"- Evaluated resolution: `{provenance.get('evaluated_resolution')}`",
        f"- Resizing occurred: `{provenance.get('resizing_occurred')}`",
        f"- Original ground-truth FPS: `{provenance.get('ground_truth_original_fps')}`",
        f"- Original prediction FPS: `{provenance.get('prediction_original_fps')}`",
        f"- FPS differed: `{provenance.get('fps_differed')}`",
        f"- Alignment method: `{provenance.get('alignment_method')}`",
        f"- Metric coverage: `{result.coverage.get('available_metric_count', 0)} of {result.coverage.get('configured_metric_count', 0)} configured metrics`",
        "",
        "### Alignment Details",
        "",
    ]
    if isinstance(alignment, dict):
        for key in sorted(alignment):
            lines.append(f"- `{key}`: `{alignment[key]}`")
    else:
        lines.append("- None")
    lines.extend(["", "### Warnings", ""])
    if isinstance(warnings, list) and warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None")
    if isinstance(demo_notice, list) and demo_notice:
        lines.extend(["", "### Demo Notice", ""])
        lines.extend(f"- {notice}" for notice in demo_notice)
    report_path.write_text(
        report_path.read_text(encoding="utf-8") + "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return report_path
