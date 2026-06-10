"""Local laptop execution backend."""

from __future__ import annotations

from pathlib import Path

from worldbench.dataset import RolloutDataset, load_dataset, validate_dataset
from worldbench.runners.evaluator import EvaluationRunner
from worldbench.schemas import EvaluationResult, ValidationReport


class LocalBackend:
    """Small backend that runs all evaluation locally with NumPy/Pillow."""

    def load(self, dataset_path: str | Path) -> RolloutDataset:
        return load_dataset(dataset_path)

    def validate(self, dataset_path: str | Path) -> ValidationReport:
        return validate_dataset(dataset_path)

    def evaluate(self, dataset_path: str | Path, predictions: str | Path | None = None) -> EvaluationResult:
        return EvaluationRunner(dataset_path, predictions=predictions).run()

