"""Statistical helpers for paired checkpoint comparisons."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PairedBootstrapResult:
    method: str
    paired_delta_mean: float
    confidence_level: float
    confidence_interval: tuple[float, float]
    bootstrap_samples: int
    bootstrap_seed: int
    episode_count: int
    small_sample_warning: bool
    small_sample_threshold: int

    def to_dict(self) -> dict[str, object]:
        return {
            "method": self.method,
            "paired_delta_mean": self.paired_delta_mean,
            "confidence_level": self.confidence_level,
            "confidence_interval": list(self.confidence_interval),
            "bootstrap_samples": self.bootstrap_samples,
            "bootstrap_seed": self.bootstrap_seed,
            "episode_count": self.episode_count,
            "small_sample_warning": self.small_sample_warning,
            "small_sample_threshold": self.small_sample_threshold,
        }


def paired_bootstrap_interval(
    deltas: list[float],
    *,
    bootstrap_samples: int = 5000,
    bootstrap_seed: int = 42,
    confidence_level: float = 0.95,
    small_sample_threshold: int = 10,
) -> PairedBootstrapResult:
    """Estimate a confidence interval over paired episode deltas.

    The input deltas must already be paired candidate-minus-baseline values for
    the same episode identities.
    """

    if not deltas:
        raise ValueError("At least one paired episode delta is required.")
    if bootstrap_samples <= 0:
        raise ValueError("bootstrap_samples must be greater than zero.")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be between 0 and 1.")

    arr = np.asarray(deltas, dtype=float)
    rng = np.random.default_rng(bootstrap_seed)
    means = np.empty(bootstrap_samples, dtype=float)
    count = int(arr.size)
    for index in range(bootstrap_samples):
        sample_indices = rng.integers(0, count, size=count)
        means[index] = float(np.mean(arr[sample_indices]))

    alpha = 1.0 - confidence_level
    lower = float(np.percentile(means, alpha / 2.0 * 100.0))
    upper = float(np.percentile(means, (1.0 - alpha / 2.0) * 100.0))
    return PairedBootstrapResult(
        method="paired_bootstrap_episode_delta",
        paired_delta_mean=float(np.mean(arr)),
        confidence_level=confidence_level,
        confidence_interval=(lower, upper),
        bootstrap_samples=bootstrap_samples,
        bootstrap_seed=bootstrap_seed,
        episode_count=count,
        small_sample_warning=count <= small_sample_threshold,
        small_sample_threshold=small_sample_threshold,
    )
