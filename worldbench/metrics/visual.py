"""Visual prediction quality metrics."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from worldbench.dataset import Episode
from worldbench.schemas import MetricResult
from worldbench.utils import clamp, load_aligned_pairs


class VisualSimilarityMetric:
    """Compare predicted frames against ground-truth rollout frames."""

    name = "visual_similarity"

    def evaluate(self, episode: Episode, prediction_frames: list[Path]) -> MetricResult:
        pairs = load_aligned_pairs(episode.frames, prediction_frames)
        if not pairs:
            return MetricResult(name=self.name, score=0.0, issues=["No aligned frame pairs available."])

        mses: list[float] = []
        psnrs: list[float] = []
        ssims: list[float] = []
        for gt, pred in pairs:
            mse = float(np.mean((gt - pred) ** 2))
            mses.append(mse)
            psnrs.append(_psnr(mse))
            ssims.append(_ssim(gt, pred))

        mean_mse = float(np.mean(mses))
        mean_psnr = float(np.mean(psnrs))
        mean_ssim = float(np.mean(ssims))
        mse_score = clamp(100.0 * (1.0 - mean_mse / (255.0**2)))
        psnr_score = clamp((mean_psnr / 40.0) * 100.0)
        ssim_score = clamp(mean_ssim * 100.0)
        score = clamp(0.35 * mse_score + 0.30 * psnr_score + 0.35 * ssim_score)

        issues = []
        if score < 60:
            issues.append("Predicted frames diverge strongly from ground truth.")
        elif mean_ssim < 0.75:
            issues.append("Predicted frames preserve broad color statistics but lose structural similarity.")

        return MetricResult(
            name=self.name,
            score=score,
            details={
                "mse": mean_mse,
                "psnr": mean_psnr,
                "ssim": mean_ssim,
                "frame_pairs": len(pairs),
                "components": {
                    "mse_score": mse_score,
                    "psnr_score": psnr_score,
                    "ssim_score": ssim_score,
                },
            },
            issues=issues,
        )


def _psnr(mse: float) -> float:
    if mse <= 1e-9:
        return 60.0
    return float(20.0 * math.log10(255.0 / math.sqrt(mse)))


def _ssim(gt: np.ndarray, pred: np.ndarray) -> float:
    try:
        from skimage.metrics import structural_similarity

        return float(structural_similarity(gt.astype(np.uint8), pred.astype(np.uint8), channel_axis=2, data_range=255))
    except Exception:  # noqa: BLE001
        return _fallback_ssim(gt, pred)


def _fallback_ssim(gt: np.ndarray, pred: np.ndarray) -> float:
    gt_luma = gt.mean(axis=2)
    pred_luma = pred.mean(axis=2)
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    mu_x = float(gt_luma.mean())
    mu_y = float(pred_luma.mean())
    sigma_x = float(gt_luma.var())
    sigma_y = float(pred_luma.var())
    sigma_xy = float(((gt_luma - mu_x) * (pred_luma - mu_y)).mean())
    numerator = (2 * mu_x * mu_y + c1) * (2 * sigma_xy + c2)
    denominator = (mu_x**2 + mu_y**2 + c1) * (sigma_x + sigma_y + c2)
    if denominator == 0:
        return 1.0
    return float(max(0.0, min(1.0, numerator / denominator)))

