"""Checkpoint regression gate CLI command."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from worldbench.commands.common import (
    console,
    failure_display_label,
    load_project_config,
)
from worldbench.runners.regression import (
    build_gate_comparison,
    load_batch_result,
    save_gate_artifacts,
)


@click.command("gate")
@click.option(
    "--baseline",
    required=True,
    type=click.Path(path_type=Path),
    help="Baseline checkpoint batch result JSON.",
)
@click.option(
    "--candidate",
    required=True,
    type=click.Path(path_type=Path),
    help="Candidate checkpoint batch result JSON.",
)
@click.option(
    "--max-overall-drop",
    default=0.0,
    show_default=True,
    type=click.FloatRange(min=0.0),
    help="Backward-compatible maximum allowed drop in Composite Score.",
)
@click.option(
    "--max-metric-drop",
    default=None,
    type=click.FloatRange(min=0.0),
    help="Maximum allowed drop for any comparable metric mean.",
)
@click.option(
    "--max-horizon-drop",
    default=None,
    type=click.FloatRange(min=0.0),
    help="Maximum allowed drop for any comparable per-horizon metric mean.",
)
@click.option(
    "--output-root",
    type=click.Path(path_type=Path),
    default=Path(".worldbench/gates"),
    help="Gate result storage root.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to worldbench.yml; auto-detected in the current directory.",
)
@click.option(
    "--require-metric",
    "required_metrics",
    multiple=True,
    help="Metric that must be available in the candidate; repeatable.",
)
@click.option(
    "--min-metric-count",
    type=click.IntRange(min=0),
    default=None,
    help="Minimum number of available configured metrics.",
)
@click.option(
    "--min-metric-coverage",
    type=click.FloatRange(min=0.0, max=1.0),
    default=None,
    help="Minimum available/configured metric ratio.",
)
@click.option(
    "--min-configured-weight-coverage",
    type=click.FloatRange(min=0.0, max=1.0),
    default=None,
    help="Minimum fraction of configured metric weight represented by available metrics.",
)
@click.option(
    "--strict-config-match/--no-strict-config-match",
    default=None,
    help="Fail on different metric profiles, weights, or horizons.",
)
@click.option(
    "--max-episode-regressions",
    type=click.IntRange(min=0),
    default=None,
    help="Maximum candidate episodes allowed to regress.",
)
@click.option(
    "--min-composite-improvement",
    type=float,
    default=None,
    help="Minimum required candidate composite-score change.",
)
@click.option(
    "--bootstrap-samples",
    type=click.IntRange(min=0),
    default=0,
    show_default=True,
    help="Enable paired bootstrap confidence interval with this sample count.",
)
@click.option(
    "--bootstrap-seed",
    type=int,
    default=42,
    show_default=True,
    help="Deterministic seed for paired bootstrap resampling.",
)
@click.option(
    "--confidence-level",
    type=click.FloatRange(min=0.0, max=1.0, min_open=True, max_open=True),
    default=0.95,
    show_default=True,
    help="Confidence level for paired bootstrap interval.",
)
@click.option(
    "--min-confidence-lower-bound",
    type=float,
    default=None,
    help="Opt-in gate: require the bootstrap lower bound to be at least this delta.",
)
def gate(
    baseline: Path,
    candidate: Path,
    max_overall_drop: float,
    max_metric_drop: float | None,
    max_horizon_drop: float | None,
    output_root: Path,
    config_path: Path | None,
    required_metrics: tuple[str, ...],
    min_metric_count: int | None,
    min_metric_coverage: float | None,
    min_configured_weight_coverage: float | None,
    strict_config_match: bool | None,
    max_episode_regressions: int | None,
    min_composite_improvement: float | None,
    bootstrap_samples: int,
    bootstrap_seed: int,
    confidence_level: float,
    min_confidence_lower_bound: float | None,
) -> None:
    """Return PASS or FAIL for a candidate checkpoint regression gate."""

    try:
        config, _ = load_project_config(config_path)
        gate_config = config.gate
        baseline_payload = load_batch_result(baseline)
        candidate_payload = load_batch_result(candidate)
        comparison = build_gate_comparison(
            baseline_payload,
            candidate_payload,
            max_overall_drop=max_overall_drop,
            max_metric_drop=gate_config.max_metric_drop
            if max_metric_drop is None
            else max_metric_drop,
            max_horizon_drop=gate_config.max_horizon_drop
            if max_horizon_drop is None
            else max_horizon_drop,
            required_metrics=list(required_metrics) or config.required_metrics,
            min_metric_count=gate_config.min_metric_count
            if min_metric_count is None
            else min_metric_count,
            min_metric_coverage=gate_config.min_metric_coverage
            if min_metric_coverage is None
            else min_metric_coverage,
            min_configured_weight_coverage=(
                gate_config.min_configured_weight_coverage
                if min_configured_weight_coverage is None
                else min_configured_weight_coverage
            ),
            strict_config_match=gate_config.strict_config_match
            if strict_config_match is None
            else strict_config_match,
            max_episode_regressions=(
                gate_config.max_episode_regressions
                if max_episode_regressions is None
                else max_episode_regressions
            ),
            min_composite_improvement=(
                gate_config.min_composite_improvement
                if min_composite_improvement is None
                else min_composite_improvement
            ),
            bootstrap_samples=bootstrap_samples,
            bootstrap_seed=bootstrap_seed,
            confidence_level=confidence_level,
            min_confidence_lower_bound=min_confidence_lower_bound,
        )
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc

    paths = save_gate_artifacts(comparison, output_root=output_root)
    print_gate_summary(comparison)
    console.print(f"[green]Saved gate result:[/green] {paths['json']}")
    console.print(f"[green]Latest alias:[/green] {paths['latest_json']}")
    if comparison["status"] == "FAIL":
        raise click.exceptions.Exit(1)


def print_gate_summary(comparison: dict[str, Any]) -> None:
    status = str(comparison["status"])
    color = "green" if status == "PASS" else "red"
    console.print(f"[bold {color}]{status}[/bold {color}]")

    baseline = comparison["baseline"]
    candidate = comparison["candidate"]
    overall = comparison["overall"]
    episodes = comparison["episodes"]
    assert isinstance(baseline, dict)
    assert isinstance(candidate, dict)
    assert isinstance(overall, dict)
    assert isinstance(episodes, dict)

    console.print(f"\nBaseline:  {baseline.get('checkpoint_name')}")
    console.print(f"Candidate: {candidate.get('checkpoint_name')}")
    console.print("\n[bold]Composite Score:[/bold]")
    console.print(
        f"{float(overall['baseline']):.1f} -> {float(overall['candidate']):.1f}"
    )
    console.print(f"Change: {float(overall['change']):+.1f}")
    uncertainty = comparison.get("uncertainty")
    if isinstance(uncertainty, dict):
        interval = uncertainty.get("confidence_interval", [])
        if isinstance(interval, list) and len(interval) == 2:
            console.print(
                "[bold]Paired bootstrap interval:[/bold] "
                f"{float(uncertainty.get('confidence_level', 0.0)):.0%} "
                f"[{float(interval[0]):+.2f}, {float(interval[1]):+.2f}] "
                f"from {uncertainty.get('episode_count')} episode(s)"
            )
    coverage = comparison.get("coverage", {})
    if isinstance(coverage, dict):
        console.print(
            f"Metric coverage: {coverage.get('available_metric_count', 0)} of "
            f"{coverage.get('configured_metric_count', 0)}"
        )
        console.print(
            f"Configured weight coverage: "
            f"{float(coverage.get('configured_weight_coverage', 0.0)):.0%}"
        )
        available = ", ".join(
            str(name) for name in coverage.get("available_metrics", [])
        )
        unavailable = ", ".join(
            str(name) for name in coverage.get("unsupported_metrics", [])
        )
        console.print(f"Available metrics: {available or 'None'}")
        console.print(f"Unavailable metrics: {unavailable or 'None'}")

    failures = comparison["failure_reasons"]
    assert isinstance(failures, list)
    if failures:
        console.print("\n[bold red]Regression detected:[/bold red]")
        for failure in failures[:8]:
            assert isinstance(failure, dict)
            label = failure_display_label(failure)
            if "horizon" in failure:
                label += f" {failure['horizon']} {failure.get('metric')}"
            elif "metric" in failure:
                label += f" {failure['metric']}"
            if {"baseline", "candidate", "change"}.issubset(failure):
                threshold = failure.get(
                    "allowed_drop", failure.get("required_improvement", "")
                )
                console.print(
                    f"{label}: {float(failure['baseline']):.1f} -> {float(failure['candidate']):.1f} "
                    f"({float(failure['change']):+.1f}); threshold {threshold}"
                )
            else:
                console.print(
                    f"{label}: {failure.get('details') or failure.get('metrics') or failure}"
                )
    else:
        console.print("\nNo configured regression threshold was exceeded.")

    warnings = comparison.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warning in warnings:
            console.print(f"- {warning}")

    console.print("\n[bold]Episodes:[/bold]")
    console.print(f"Improved:   {int(episodes['improved_count'])}")
    console.print(f"Regressed:  {int(episodes['regressed_count'])}")
    console.print(f"Unchanged:  {int(episodes['unchanged_count'])}")
    worst = episodes.get("worst_regressions")
    if isinstance(worst, list) and worst:
        console.print("\n[bold]Worst episodes:[/bold]")
        for item in worst[:5]:
            if isinstance(item, dict):
                console.print(f"{item['episode_id']}    {float(item['change']):+.1f}")
