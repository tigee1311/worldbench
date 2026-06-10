"""Markdown report generation."""

from __future__ import annotations

from pathlib import Path

from worldbench.schemas import EvaluationResult
from worldbench.utils import markdown_table, write_json


def generate_markdown_report(result: EvaluationResult) -> str:
    metric_rows = [
        [
            name.replace("_", " ").title(),
            f"{metric.score:.1f}/100",
            f"{result.weights.get(name, 0.0):.0%}",
        ]
        for name, metric in result.metrics.items()
    ]
    episode_rows = [
        [
            episode.episode,
            f"{episode.score:.1f}/100",
            ", ".join(f"{name}={metric.score:.1f}" for name, metric in episode.metrics.items()),
        ]
        for episode in result.episodes
    ]
    evidence = collect_evidence(result)
    next_steps = suggested_next_steps(result)

    sections = [
        "# WorldBench Evaluation Report",
        "",
        f"**Overall Score:** {result.score:.1f}/100",
        "",
        f"**Main failure:** {result.main_failure}",
        "",
        "## Metric Scores",
        "",
        markdown_table(["Metric", "Score", "Weight"], metric_rows),
        "",
        "## Per-Episode Scores",
        "",
        markdown_table(["Episode", "Score", "Metric Breakdown"], episode_rows),
        "",
        "## Evidence",
        "",
        "\n".join(f"- {item}" for item in evidence) if evidence else "- No major metric issues were detected.",
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
        evidence.extend(metric.issues)
    for episode in result.episodes:
        for issue in episode.issues:
            tagged = f"{episode.episode}: {issue}"
            if tagged not in evidence:
                evidence.append(tagged)
    return evidence[:12]


def suggested_next_steps(result: EvaluationResult) -> list[str]:
    ordered = sorted(result.metrics.values(), key=lambda metric: metric.score)
    suggestions: list[str] = []
    for metric in ordered[:3]:
        if metric.name == "action_consistency":
            suggestions.append("Add stronger action conditioning and evaluate held-out action sequences.")
        elif metric.name == "contact_realism":
            suggestions.append("Increase interaction examples with explicit pre-contact and post-contact dynamics.")
        elif metric.name == "temporal_stability":
            suggestions.append("Audit prediction rollout recurrence and add losses that discourage flicker.")
        elif metric.name == "object_permanence":
            suggestions.append("Track object permanence through occlusion, contact, and gripper state changes.")
        elif metric.name == "visual_similarity":
            suggestions.append("Improve visual reconstruction quality before relying on generated futures for planning.")
    suggestions.append("Run WorldBench on a held-out robot-object interaction split before comparing models.")
    return list(dict.fromkeys(suggestions))


def save_report_json_copy(result: EvaluationResult, output_dir: str | Path) -> Path:
    return write_json(Path(output_dir) / "result.json", result.to_dict())

