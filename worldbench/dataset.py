"""Dataset loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from worldbench.schemas import ActionRecord, EpisodeMetadata, StateRecord, ValidationIssue, ValidationReport
from worldbench.utils import list_image_files, read_json


@dataclass(frozen=True)
class Episode:
    """Loaded rollout episode with aligned files and structured logs."""

    name: str
    path: Path
    frames: list[Path]
    predictions: list[Path]
    actions: list[ActionRecord]
    states: list[StateRecord]
    metadata: EpisodeMetadata


@dataclass(frozen=True)
class RolloutDataset:
    """Robot rollout dataset rooted at a dataset directory."""

    path: Path
    episodes: list[Episode]

    def episode_names(self) -> list[str]:
        return [episode.name for episode in self.episodes]

    def __iter__(self) -> Iterable[Episode]:
        return iter(self.episodes)

    def __len__(self) -> int:
        return len(self.episodes)


def validate_dataset(path: str | Path) -> ValidationReport:
    """Validate the WorldBench dataset folder structure."""

    dataset_path = Path(path)
    issues: list[ValidationIssue] = []
    episode_count = 0
    frame_count = 0

    if not dataset_path.exists():
        return ValidationReport(
            dataset_path=str(dataset_path),
            issues=[ValidationIssue(level="error", message="Dataset path does not exist.", path=str(dataset_path))],
        )
    if not dataset_path.is_dir():
        return ValidationReport(
            dataset_path=str(dataset_path),
            issues=[ValidationIssue(level="error", message="Dataset path is not a directory.", path=str(dataset_path))],
        )

    episode_dirs = sorted(p for p in dataset_path.iterdir() if p.is_dir() and p.name.startswith("episode_"))
    if not episode_dirs:
        issues.append(ValidationIssue(level="error", message="No episode_* directories found.", path=str(dataset_path)))

    for episode_dir in episode_dirs:
        episode_count += 1
        frames_dir = episode_dir / "frames"
        predictions_dir = episode_dir / "predictions"
        actions_path = episode_dir / "actions.json"
        states_path = episode_dir / "states.json"
        metadata_path = episode_dir / "metadata.json"

        if not frames_dir.is_dir():
            issues.append(ValidationIssue(level="error", message="Missing frames/ directory.", path=str(frames_dir)))
        else:
            frames = list_image_files(frames_dir)
            frame_count += len(frames)
            if not frames:
                issues.append(ValidationIssue(level="error", message="No image frames found.", path=str(frames_dir)))

        if not predictions_dir.is_dir():
            issues.append(
                ValidationIssue(
                    level="warning",
                    message="Missing predictions/ directory. External predictions can still be passed with --predictions.",
                    path=str(predictions_dir),
                )
            )

        _validate_json_records(actions_path, ActionRecord, "actions.json", issues)
        _validate_json_records(states_path, StateRecord, "states.json", issues)
        _validate_metadata(metadata_path, issues)

    return ValidationReport(
        dataset_path=str(dataset_path),
        episode_count=episode_count,
        frame_count=frame_count,
        issues=issues,
    )


def load_dataset(path: str | Path) -> RolloutDataset:
    """Load a validated WorldBench rollout dataset."""

    dataset_path = Path(path)
    report = validate_dataset(dataset_path)
    if not report.is_valid:
        messages = "; ".join(issue.message for issue in report.issues if issue.level == "error")
        raise ValueError(f"Invalid WorldBench dataset: {messages}")

    episodes: list[Episode] = []
    for episode_dir in sorted(p for p in dataset_path.iterdir() if p.is_dir() and p.name.startswith("episode_")):
        actions = [ActionRecord.model_validate(item) for item in read_json(episode_dir / "actions.json")]
        states = [StateRecord.model_validate(item) for item in read_json(episode_dir / "states.json")]
        metadata = EpisodeMetadata.model_validate(read_json(episode_dir / "metadata.json"))
        episodes.append(
            Episode(
                name=episode_dir.name,
                path=episode_dir,
                frames=list_image_files(episode_dir / "frames"),
                predictions=list_image_files(episode_dir / "predictions"),
                actions=actions,
                states=states,
                metadata=metadata,
            )
        )

    return RolloutDataset(path=dataset_path, episodes=episodes)


def _validate_json_records(path: Path, model: type, label: str, issues: list[ValidationIssue]) -> None:
    if not path.is_file():
        issues.append(ValidationIssue(level="error", message=f"Missing {label}.", path=str(path)))
        return
    try:
        data = read_json(path)
    except Exception as exc:  # noqa: BLE001
        issues.append(ValidationIssue(level="error", message=f"Could not parse {label}: {exc}", path=str(path)))
        return
    if not isinstance(data, list):
        issues.append(ValidationIssue(level="error", message=f"{label} must be a JSON list.", path=str(path)))
        return
    for idx, item in enumerate(data):
        try:
            model.model_validate(item)
        except ValidationError as exc:
            issues.append(ValidationIssue(level="error", message=f"Invalid {label} record {idx}: {exc}", path=str(path)))


def _validate_metadata(path: Path, issues: list[ValidationIssue]) -> None:
    if not path.is_file():
        issues.append(ValidationIssue(level="error", message="Missing metadata.json.", path=str(path)))
        return
    try:
        EpisodeMetadata.model_validate(read_json(path))
    except Exception as exc:  # noqa: BLE001
        issues.append(ValidationIssue(level="error", message=f"Invalid metadata.json: {exc}", path=str(path)))

