"""Explicit extension interfaces for WorldBench plugins.

WorldBench does not download or install plugins dynamically. Third-party code must
be imported and registered by the calling application.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, Literal, Protocol, TypeVar, runtime_checkable

from worldbench.dataset import Episode
from worldbench.schemas import ActionRecord, MetricResult


@dataclass(frozen=True)
class MetricRequirements:
    """Signals a metric needs before it can return a meaningful score."""

    input_modalities: tuple[str, ...] = ("rgb_frames",)
    requires_actions: bool = False
    requires_states: bool = False
    requires_tracking: bool = False
    supports_video_pairs: bool = True
    notes: str = ""


@dataclass(frozen=True)
class PluginCapabilities:
    """Simple capability declaration shared by adapters."""

    inputs: tuple[str, ...] = field(default_factory=tuple)
    outputs: tuple[str, ...] = field(default_factory=tuple)
    limitations: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class NormalizedActions:
    """Action records emitted by an explicit action adapter."""

    schema: str
    actions: tuple[ActionRecord, ...]
    adapter_name: str
    adapter_version: str
    warnings: tuple[str, ...] = field(default_factory=tuple)


@runtime_checkable
class MetricPlugin(Protocol):
    """Protocol implemented by metric plugins."""

    name: str
    version: str
    requirements: MetricRequirements

    def evaluate(self, episode: Episode, prediction_frames: list[Path]) -> MetricResult:
        """Evaluate one episode and return an available, unsupported, or error result."""


@runtime_checkable
class ActionAdapter(Protocol):
    """Protocol implemented by action-normalization adapters."""

    name: str
    version: str
    supported_schema: str
    capabilities: PluginCapabilities

    def normalize(self, actions: object) -> NormalizedActions:
        """Normalize raw actions into WorldBench action records."""


@runtime_checkable
class DatasetAdapter(Protocol):
    """Protocol implemented by dataset import adapters."""

    name: str
    version: str
    supported_schema: str
    capabilities: PluginCapabilities

    def can_load(self, source: object) -> bool:
        """Return whether this adapter supports the source."""


@runtime_checkable
class PredictionFormatAdapter(Protocol):
    """Protocol implemented by prediction-format adapters."""

    name: str
    version: str
    supported_schema: str
    capabilities: PluginCapabilities

    def can_load(self, source: object) -> bool:
        """Return whether this adapter supports the source."""


class UnsupportedPluginResult(ValueError):
    """Raised by plugins when inputs are valid but unsupported."""


PluginErrorPolicy = Literal["record", "fail-fast"]


T = TypeVar("T")


class DeterministicRegistry(Generic[T]):
    """Name-keyed plugin registry with stable sorted iteration."""

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self._items: dict[str, T] = {}

    def register(self, plugin: T) -> T:
        name = _plugin_name(plugin)
        version = _plugin_version(plugin)
        if not name:
            raise ValueError(f"{self.kind} plugin name must be a non-empty string.")
        if not version:
            raise ValueError(f"{self.kind} plugin '{name}' version must be non-empty.")
        if name in self._items:
            raise ValueError(f"Duplicate {self.kind} plugin name: {name}")
        self._items[name] = plugin
        return plugin

    def get(self, name: str) -> T:
        try:
            return self._items[name]
        except KeyError as exc:
            raise KeyError(f"Unknown {self.kind} plugin: {name}") from exc

    def items(self) -> tuple[T, ...]:
        return tuple(self._items[name] for name in sorted(self._items))

    def versions(self) -> dict[str, str]:
        return {
            name: _plugin_version(self._items[name]) for name in sorted(self._items)
        }


class PluginRegistry:
    """Container for all explicitly registered WorldBench extensions."""

    def __init__(self) -> None:
        self.metrics: DeterministicRegistry[MetricPlugin] = DeterministicRegistry(
            "metric"
        )
        self.action_adapters: DeterministicRegistry[ActionAdapter] = (
            DeterministicRegistry("action adapter")
        )
        self.dataset_adapters: DeterministicRegistry[DatasetAdapter] = (
            DeterministicRegistry("dataset adapter")
        )
        self.prediction_adapters: DeterministicRegistry[PredictionFormatAdapter] = (
            DeterministicRegistry("prediction adapter")
        )

    def register_metric(self, plugin: MetricPlugin) -> MetricPlugin:
        return self.metrics.register(plugin)

    def register_action_adapter(self, plugin: ActionAdapter) -> ActionAdapter:
        return self.action_adapters.register(plugin)

    def register_dataset_adapter(self, plugin: DatasetAdapter) -> DatasetAdapter:
        return self.dataset_adapters.register(plugin)

    def register_prediction_adapter(
        self, plugin: PredictionFormatAdapter
    ) -> PredictionFormatAdapter:
        return self.prediction_adapters.register(plugin)

    def provenance(self) -> dict[str, Any]:
        return {
            "metric_plugins": self.metrics.versions(),
            "action_adapters": self.action_adapters.versions(),
            "dataset_adapters": self.dataset_adapters.versions(),
            "prediction_adapters": self.prediction_adapters.versions(),
        }


def evaluate_metric_plugin(
    plugin: MetricPlugin,
    episode: Episode,
    prediction_frames: list[Path],
    *,
    error_policy: PluginErrorPolicy = "record",
) -> MetricResult:
    """Evaluate a plugin and isolate unsupported/error results."""

    if error_policy not in {"record", "fail-fast"}:
        raise ValueError("plugin error policy must be either 'record' or 'fail-fast'.")
    plugin_name = _plugin_name(plugin)
    try:
        result = plugin.evaluate(episode, prediction_frames)
    except UnsupportedPluginResult as exc:
        return MetricResult(
            name=plugin_name,
            score=None,
            status="unsupported",
            reason=_short_error(exc),
            issues=[_short_error(exc)],
        )
    except Exception as exc:
        if error_policy == "fail-fast":
            raise
        return _plugin_error_result(
            plugin_name,
            exc.__class__.__name__,
            (
                f"Metric plugin '{plugin_name}' raised unexpected "
                f"{exc.__class__.__name__}: {_short_error(exc)}"
            ),
        )

    if not isinstance(result, MetricResult):
        reason = (
            f"Metric plugin '{plugin_name}' returned {type(result).__name__}; "
            "expected MetricResult."
        )
        if error_policy == "fail-fast":
            raise TypeError(reason)
        return _plugin_error_result(plugin_name, "InvalidPluginResult", reason)

    if result.name != plugin_name:
        reason = (
            f"Metric plugin returned result name '{result.name}', "
            f"expected '{plugin_name}'."
        )
        if error_policy == "fail-fast":
            raise ValueError(reason)
        return _plugin_error_result(plugin_name, "InvalidPluginResult", reason)
    if result.status == "error" and not result.error_type:
        return result.model_copy(update={"error_type": "PluginError"})
    return result


def _plugin_error_result(
    plugin_name: str,
    error_type: str,
    reason: str,
) -> MetricResult:
    sanitized_reason = _redact_sensitive_text(reason)
    return MetricResult(
        name=plugin_name,
        score=None,
        status="error",
        error_type=_sanitize_error_type(error_type),
        reason=sanitized_reason,
        issues=[sanitized_reason],
    )


def _sanitize_error_type(error_type: str) -> str:
    safe = "".join(
        char for char in str(error_type) if char.isalnum() or char in {"_", "."}
    )
    return safe[:80] or "PluginError"


def _redact_sensitive_text(text: str) -> str:
    home = str(Path.home())
    redacted = text.replace(home, "<home>")
    parts = []
    for token in redacted.split():
        lower = token.lower()
        if any(
            marker in lower for marker in ("token=", "password=", "secret=", "key=")
        ):
            parts.append("<redacted>")
        elif "/Users/" in token:
            parts.append("<redacted-path>")
        else:
            parts.append(token)
    return " ".join(parts)


def metric_plugin_provenance(metrics: list[MetricPlugin]) -> dict[str, str]:
    """Return deterministic metric-name to version mapping."""

    return {
        metric.name: _plugin_version(metric)
        for metric in sorted(metrics, key=_plugin_name)
    }


def _plugin_name(plugin: object) -> str:
    return str(getattr(plugin, "name", "") or "")


def _plugin_version(plugin: object) -> str:
    return str(getattr(plugin, "version", "") or "unversioned")


def _short_error(exc: Exception) -> str:
    text = str(exc).strip()
    if not text:
        return exc.__class__.__name__
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    safe = _redact_sensitive_text(first)
    return safe[:177] + "..." if len(safe) > 180 else safe
