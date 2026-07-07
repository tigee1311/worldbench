"""Pydantic schemas used by the WorldBench SDK and CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class ActionRecord(BaseModel):
    """Single robot action aligned to a rollout timestep."""

    t: int
    timestamp: float | None = None
    source_control_index: int | None = None
    source_control_timestamp: float | None = None
    source_video_frame_index: int | None = None
    source_video_timestamp: float | None = None
    action: Any = "noop"
    dx: float = 0.0
    dy: float = 0.0
    gripper: str | None = None


class StateRecord(BaseModel):
    """Simple robot/object state used by lightweight synthetic evaluators."""

    t: int
    timestamp: float | None = None
    source_control_index: int | None = None
    source_control_timestamp: float | None = None
    source_video_frame_index: int | None = None
    source_video_timestamp: float | None = None
    observation_state: Any = None
    robot_x: float | None = None
    robot_y: float | None = None
    object_x: float | None = None
    object_y: float | None = None


class EpisodeMetadata(BaseModel):
    """Metadata for one rollout episode."""

    name: str = "episode"
    robot: str = "unknown"
    task: str = "unknown"
    fps: float = 5.0
    description: str = ""
    source: str | None = None
    repo_id: str | None = None
    episode_index: int | None = None
    camera_key: str | None = None
    timeline: Literal["video", "control"] | None = None
    video_fps: float | None = None
    alignment_strategy: dict[str, str] | None = None
    source_control_steps: int | None = None
    source_unique_video_frames: int | None = None
    source_referenced_video_frames: int | None = None
    exported_timesteps: int | None = None


class ValidationIssue(BaseModel):
    """Validation issue emitted by dataset checks."""

    level: Literal["error", "warning"] = "error"
    message: str
    path: str | None = None


class ValidationReport(BaseModel):
    """Dataset validation result."""

    dataset_path: str
    episode_count: int = 0
    frame_count: int = 0
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(issue.level == "error" for issue in self.issues)


class MetricResult(BaseModel):
    """Score and supporting evidence for one metric."""

    name: str
    score: float | None = None
    status: Literal["available", "unsupported"] = "available"
    reason: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)

    @property
    def is_available(self) -> bool:
        return self.status == "available" and self.score is not None

    @property
    def display_score(self) -> str:
        return "N/A" if not self.is_available else f"{self.score:.1f}"


class EpisodeResult(BaseModel):
    """All metric outputs for one episode."""

    episode: str
    score: float = Field(ge=0.0, le=100.0)
    metrics: dict[str, MetricResult] = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    """Serializable result object returned by WorldBench evaluations."""

    dataset_path: str
    predictions_path: str | None = None
    created_at: str
    score: float = Field(ge=0.0, le=100.0)
    metrics: dict[str, MetricResult] = Field(default_factory=dict)
    episodes: list[EpisodeResult] = Field(default_factory=list)
    weights: dict[str, float] = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)
    main_failure: str = "No dominant failure detected."

    @property
    def overall_score(self) -> float:
        return self.score

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def save_json(self, path: str | Path) -> Path:
        """Save the result as JSON and return the written path."""

        from worldbench.utils import write_json

        output = Path(path)
        write_json(output, self.to_dict())
        return output

    def save_report(self, path: str | Path) -> Path:
        """Generate a Markdown report for this result."""

        from worldbench.runners.reporter import save_markdown_report

        return save_markdown_report(self, path)

    def print_summary(self) -> None:
        """Print a compact Rich summary table."""

        from rich.console import Console
        from rich.table import Table

        console = Console()
        console.rule("[bold]WorldBench Evaluation Report[/bold]")
        console.print(f"[bold]Overall Score:[/bold] {self.score:.1f}/100")
        console.print(f"[bold]Main failure:[/bold] {self.main_failure}")

        table = Table(title="Metric Scores", show_lines=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Weight", justify="right")
        for name, result in self.metrics.items():
            weight = "N/A" if not result.is_available else f"{self.weights.get(name, 0):.0%}"
            table.add_row(name.replace("_", " ").title(), result.display_score, weight)
        console.print(table)
        unavailable = [f"{name.replace('_', ' ').title()}: {result.reason}" for name, result in self.metrics.items() if not result.is_available and result.reason]
        if unavailable:
            console.print("\n".join(unavailable))
