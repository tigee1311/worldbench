"""Project configuration and metric coverage helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


METRIC_NAMES = (
    "visual_similarity",
    "action_consistency",
    "temporal_stability",
    "object_permanence",
    "contact_realism",
)
DEFAULT_WEIGHTS = {
    "visual_similarity": 0.25,
    "action_consistency": 0.30,
    "temporal_stability": 0.20,
    "object_permanence": 0.15,
    "contact_realism": 0.10,
}


class MetricConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    enabled: bool = True
    required: bool = False
    weight: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)


class GateConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    min_composite_improvement: float = Field(default=0.0, allow_inf_nan=False)
    max_episode_regressions: int | None = Field(default=None, ge=0)
    max_metric_drop: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    max_horizon_drop: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    min_metric_coverage: float = Field(default=0.0, ge=0.0, le=1.0, allow_inf_nan=False)
    min_metric_count: int = Field(default=1, ge=0)
    min_configured_weight_coverage: float = Field(
        default=0.0, ge=0.0, le=1.0, allow_inf_nan=False
    )
    strict_config_match: bool = True


class OutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    json_output: bool = Field(default=True, alias="json", serialization_alias="json")
    markdown_output: bool = Field(
        default=True, alias="markdown", serialization_alias="markdown"
    )


class WorldBenchConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metrics: dict[str, MetricConfig]
    gate: GateConfig = Field(default_factory=GateConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    @model_validator(mode="after")
    def validate_metrics(self) -> "WorldBenchConfig":
        unknown = sorted(set(self.metrics) - set(METRIC_NAMES))
        if unknown:
            raise ValueError(f"Unknown metrics: {', '.join(unknown)}")
        for name in METRIC_NAMES:
            if name not in self.metrics:
                self.metrics[name] = MetricConfig(weight=DEFAULT_WEIGHTS[name])
        required_disabled = [
            name
            for name, item in self.metrics.items()
            if item.required and not item.enabled
        ]
        if required_disabled:
            raise ValueError(
                f"Required metrics must be enabled: {', '.join(required_disabled)}"
            )
        if not any(item.enabled for item in self.metrics.values()):
            raise ValueError("At least one metric must be enabled.")
        if sum(item.weight for item in self.metrics.values() if item.enabled) <= 0:
            raise ValueError("Enabled metric weights must sum to more than zero.")
        return self

    @property
    def enabled_metrics(self) -> list[str]:
        return [name for name in METRIC_NAMES if self.metrics[name].enabled]

    @property
    def required_metrics(self) -> list[str]:
        return [name for name in METRIC_NAMES if self.metrics[name].required]

    @property
    def configured_weights(self) -> dict[str, float]:
        return {name: self.metrics[name].weight for name in self.enabled_metrics}

    def evaluation_dict(self) -> dict[str, Any]:
        return {
            "metrics": {
                name: self.metrics[name].model_dump(mode="json")
                for name in METRIC_NAMES
            }
        }

    @property
    def configuration_hash(self) -> str:
        canonical = json.dumps(
            self.evaluation_dict(), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def default_config() -> WorldBenchConfig:
    return WorldBenchConfig(
        metrics={
            name: MetricConfig(weight=weight)
            for name, weight in DEFAULT_WEIGHTS.items()
        }
    )


def load_config(path: str | Path | None = None) -> tuple[WorldBenchConfig, Path | None]:
    candidate = Path(path) if path is not None else Path("worldbench.yml")
    if path is None and not candidate.is_file():
        return default_config(), None
    if not candidate.is_file():
        raise ValueError(f"WorldBench configuration file does not exist: {candidate}")
    try:
        data = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
        return WorldBenchConfig.model_validate(data), candidate
    except (yaml.YAMLError, ValueError) as exc:
        raise ValueError(
            f"Invalid WorldBench configuration in {candidate}: {exc}"
        ) from exc


def coverage_for(
    configured_metrics: list[str],
    configured_weights: dict[str, float],
    available_metrics: list[str],
) -> dict[str, Any]:
    available = [name for name in configured_metrics if name in available_metrics]
    unsupported = [name for name in configured_metrics if name not in available]
    total_weight = sum(configured_weights.get(name, 0.0) for name in configured_metrics)
    available_weight = sum(configured_weights.get(name, 0.0) for name in available)
    effective = {
        name: configured_weights.get(name, 0.0) / available_weight
        for name in available
        if available_weight > 0
    }
    return {
        "available_metrics": available,
        "unsupported_metrics": unsupported,
        "configured_metrics": configured_metrics,
        "available_metric_count": len(available),
        "configured_metric_count": len(configured_metrics),
        "metric_coverage": len(available) / len(configured_metrics)
        if configured_metrics
        else 0.0,
        "configured_weight_coverage": available_weight / total_weight
        if total_weight
        else 0.0,
        "effective_normalized_weights": effective,
    }
