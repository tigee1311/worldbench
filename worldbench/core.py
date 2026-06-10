"""Public SDK surface for WorldBench."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from worldbench.dataset import RolloutDataset, load_dataset
from worldbench.metrics import (
    ActionConsistencyMetric,
    ContactRealismMetric,
    ObjectPermanenceMetric,
    TemporalStabilityMetric,
    VisualSimilarityMetric,
)
from worldbench.runners.evaluator import EvaluationRunner, EvaluatorMetric
from worldbench.schemas import EvaluationResult


@dataclass(frozen=True)
class WorldModelRun:
    """Named prediction run that can be evaluated or compared."""

    predictions: str | Path
    name: str | None = None


class Metrics:
    """Factory methods for composable WorldBench metrics."""

    @staticmethod
    def visual_similarity() -> VisualSimilarityMetric:
        return VisualSimilarityMetric()

    @staticmethod
    def action_consistency() -> ActionConsistencyMetric:
        return ActionConsistencyMetric()

    @staticmethod
    def temporal_stability() -> TemporalStabilityMetric:
        return TemporalStabilityMetric()

    @staticmethod
    def object_permanence() -> ObjectPermanenceMetric:
        return ObjectPermanenceMetric()

    @staticmethod
    def contact_realism() -> ContactRealismMetric:
        return ContactRealismMetric()

    @staticmethod
    def all() -> list[EvaluatorMetric]:
        return [
            Metrics.visual_similarity(),
            Metrics.action_consistency(),
            Metrics.temporal_stability(),
            Metrics.object_permanence(),
            Metrics.contact_realism(),
        ]


class WorldBench:
    """SDK entry point for robotics world-model evaluation."""

    def __init__(self, dataset: str | Path | RolloutDataset) -> None:
        self.dataset = load_dataset(dataset) if isinstance(dataset, (str, Path)) else dataset

    def evaluate(
        self,
        predictions: str | Path | WorldModelRun | None = None,
        metrics: list[EvaluatorMetric] | None = None,
    ) -> EvaluationResult:
        prediction_path = predictions.predictions if isinstance(predictions, WorldModelRun) else predictions
        return EvaluationRunner(self.dataset, predictions=prediction_path).run(metrics=metrics)

    def run(
        self,
        metrics: list[EvaluatorMetric] | None = None,
        predictions: str | Path | WorldModelRun | None = None,
    ) -> EvaluationResult:
        return self.evaluate(predictions=predictions, metrics=metrics)


def evaluate(dataset: str | Path | RolloutDataset, predictions: str | Path | None = None) -> EvaluationResult:
    """Convenience function for one-line evaluations."""

    return WorldBench(dataset).evaluate(predictions=predictions)

