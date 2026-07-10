"""Markdown report generation."""

from __future__ import annotations

from pathlib import Path

from worldbench.schemas import EvaluationResult
from worldbench.utils import markdown_table, write_json


def generate_markdown_report(result: EvaluationResult) -> str:
    metric_rows = [
        [
            name.replace("_", " ").title(),
            f"{metric.score:.1f}/100"
            if metric.is_available and metric.score is not None
            else "N/A",
            f"{result.effective_normalized_weights.get(name, 0.0):.0%}"
            if metric.is_available
            else "N/A",
        ]
        for name, metric in result.metrics.items()
    ]
    episode_rows = [
        [
            episode.episode,
            f"{episode.score:.1f}/100",
            ", ".join(
                f"{name}={metric.score:.1f}"
                if metric.is_available and metric.score is not None
                else f"{name}=N/A"
                for name, metric in episode.metrics.items()
            ),
        ]
        for episode in result.episodes
    ]
    evidence = collect_evidence(result)
    next_steps = suggested_next_steps(result)

    sections = [
        "# WorldBench Evaluation Report",
        "",
        f"**Composite Score:** {result.score:.2f}/100",
        "",
        f"**Metric coverage:** {result.coverage.get('available_metric_count', 0)} of {result.coverage.get('configured_metric_count', 0)} configured metrics",
        "",
        f"**Configured weight coverage:** {float(result.coverage.get('configured_weight_coverage', 0.0)):.0%}",
        "",
        f"**Main failure:** {result.main_failure}",
        "",
        "## Metric Scores",
        "",
        markdown_table(["Metric", "Score", "Effective Weight"], metric_rows),
        "",
        "### Unsupported Metrics",
        "",
        "\n".join(
            f"- {name.replace('_', ' ').title()}"
            for name in result.coverage.get("unsupported_metrics", [])
        )
        or "- None",
        "",
        "## Per-Episode Scores",
        "",
        markdown_table(["Episode", "Score", "Metric Breakdown"], episode_rows),
        "",
        "## Evidence",
        "",
        "\n".join(f"- {item}" for item in evidence)
        if evidence
        else "- No major metric issues were detected.",
        "",
        "## Suggested Next Steps",
        "",
        "\n".join(f"- {item}" for item in next_steps),
        "",
        "## Run Metadata",
        "",
        f"- Dataset: `{result.dataset_path}`",
        f"- Predictions: `{result.predictions_path or 'episode predictions folders'}`",
        f"- Created: `{result.created_at}`",
        f"- WorldBench version: `{result.worldbench_version or 'legacy artifact'}`",
        f"- Schema version: `{result.schema_version}`",
        f"- Configuration hash: `{result.configuration_hash or 'unavailable'}`",
        "",
    ]
    return "\n".join(sections)


def save_markdown_report(result: EvaluationResult, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(generate_markdown_report(result), encoding="utf-8")
    return output


def collect_evidence(result: EvaluationResult) -> list[str]:
    evidence: list[str] = []
    for metric in result.metrics.values():
        if metric.reason:
            evidence.append(metric.reason)
        evidence.extend(metric.issues)
    for episode in result.episodes:
        for metric in episode.metrics.values():
            evidence.extend(
                _metric_detail_evidence(episode.episode, metric.name, metric.details)
            )
        for issue in episode.issues:
            tagged = f"{episode.episode}: {issue}"
            if tagged not in evidence:
                evidence.append(tagged)
    return list(dict.fromkeys(evidence))[:16]


def _metric_detail_evidence(
    episode_name: str, metric_name: str, details: dict
) -> list[str]:
    evidence: list[str] = []
    prefix = f"{episode_name}: "
    if metric_name == "action_consistency":
        mismatch = details.get("mismatch_percentage")
        if isinstance(mismatch, (int, float)) and mismatch > 0:
            evidence.append(
                f"{prefix}{mismatch:.0f}% of commanded action steps mismatched predicted visual motion."
            )
        failures = details.get("failures")
        if isinstance(failures, list) and failures:
            first = failures[0]
            if isinstance(first, dict):
                evidence.append(
                    f"{prefix}first action mismatch at t={first.get('t')}: "
                    f"command `{first.get('action')}` produced dx={first.get('observed_dx')}, dy={first.get('observed_dy')}."
                )
    elif metric_name == "contact_realism":
        first_motion = details.get("first_object_motion_frame")
        first_contact = details.get("first_contact_frame")
        if details.get("moved_before_contact"):
            evidence.append(
                f"{prefix}object began moving at frame {first_motion}; estimated contact was frame {first_contact}."
            )
    elif metric_name == "object_permanence":
        missing = details.get("missing_frames")
        disappearance = details.get("disappearance_percentage")
        if isinstance(missing, list) and missing:
            evidence.append(
                f"{prefix}object missing frames: {missing[:8]} ({float(disappearance or 0):.0f}% disappearance)."
            )
    elif metric_name == "temporal_stability":
        flicker = details.get("flicker_frames")
        largest = details.get("largest_jump_frame")
        if isinstance(flicker, list) and flicker:
            evidence.append(
                f"{prefix}flicker/jump frames: {flicker[:8]}; largest jump at frame {largest}."
            )
    return evidence


def suggested_next_steps(result: EvaluationResult) -> list[str]:
    ordered = sorted(
        result.metrics.values(),
        key=lambda metric: (
            metric.score if metric.is_available and metric.score is not None else 101.0
        ),
    )
    suggestions: list[str] = []
    for metric in ordered[:3]:
        if not metric.is_available:
            suggestions.append(
                f"Review {metric.name.replace('_', ' ')} support for the current action format."
            )
            continue
        if metric.name == "action_consistency":
            suggestions.append(
                "Add stronger action conditioning and evaluate held-out action sequences."
            )
        elif metric.name == "contact_realism":
            suggestions.append(
                "Increase interaction examples with explicit pre-contact and post-contact dynamics."
            )
        elif metric.name == "temporal_stability":
            suggestions.append(
                "Audit prediction rollout recurrence and add losses that discourage flicker."
            )
        elif metric.name == "object_permanence":
            suggestions.append(
                "Track object permanence through occlusion, contact, and gripper state changes."
            )
        elif metric.name == "visual_similarity":
            suggestions.append(
                "Improve visual reconstruction quality before relying on generated futures for planning."
            )
    suggestions.append(
        "Run WorldBench on a held-out robot-object interaction split before comparing models."
    )
    return list(dict.fromkeys(suggestions))


def save_report_json_copy(result: EvaluationResult, output_dir: str | Path) -> Path:
    return write_json(Path(output_dir) / "result.json", result.to_dict())
