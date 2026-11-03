"""
NEXUS — Failure Prediction Engine.
Uses linear regression on telemetry trend to predict time-to-failure.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class LinkPrediction:
    link_id: str
    failure_probability: float    # 0.0–1.0
    trend_slope: float            # positive = degrading
    estimated_ttf_seconds: float | None  # None if not trending to failure
    current_loss_rate: float
    current_latency_ms: float
    confidence: float             # 0.0–1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_id": self.link_id,
            "failure_probability": self.failure_probability,
            "trend_slope": self.trend_slope,
            "estimated_ttf_seconds": self.estimated_ttf_seconds,
            "current_loss_rate": self.current_loss_rate,
            "current_latency_ms": self.current_latency_ms,
            "confidence": self.confidence,
        }


def _linear_regression(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Return (slope, intercept) via least squares."""
    n = len(xs)
    if n < 2:
        return 0.0, ys[0] if ys else 0.0
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)
    denom = n * sum_x2 - sum_x ** 2
    if abs(denom) < 1e-9:
        return 0.0, sum_y / n
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def predict_link_failures(
    telemetry_history: list[list[dict]],
    failure_threshold_loss: float = 0.15,
) -> list[LinkPrediction]:
    """
    Predict failure probability per link from N historical telemetry snapshots.

    telemetry_history: list of snapshots (oldest first). Each snapshot is a list of:
        {"link_id": str, "loss_rate": float, "latency_ms": float, "timestamp": float}
    """
    if not telemetry_history:
        return []

    # Collect per-link time series
    link_series: dict[str, dict] = {}
    for snapshot in telemetry_history:
        for reading in snapshot:
            lid = reading.get("link_id", "unknown")
            if lid not in link_series:
                link_series[lid] = {"timestamps": [], "loss_rates": [], "latencies": []}
            link_series[lid]["timestamps"].append(float(reading.get("timestamp", 0.0)))
            link_series[lid]["loss_rates"].append(float(reading.get("loss_rate", 0.0)))
            link_series[lid]["latencies"].append(float(reading.get("latency_ms", 0.0)))

    predictions = []
    for lid, series in link_series.items():
        xs = list(range(len(series["timestamps"])))
        loss_slope, _ = _linear_regression(xs, series["loss_rates"])

        n_points = len(xs)
        confidence = min(1.0, n_points / 10.0)

        current_loss = series["loss_rates"][-1]
        current_lat = series["latencies"][-1]

        # Steps until loss >= threshold
        if loss_slope > 1e-6:
            steps_to_failure = (failure_threshold_loss - current_loss) / loss_slope
            ttf_seconds = max(0.0, steps_to_failure * 30.0) if steps_to_failure > 0 else 0.0
        else:
            ttf_seconds = None

        # Failure probability via sigmoid of degradation level
        degradation = current_loss / failure_threshold_loss
        if loss_slope > 0:
            degradation += 0.3  # trend penalty
        prob = round(1.0 / (1.0 + math.exp(-6.0 * (degradation - 0.5))), 4)
        prob = max(0.0, min(1.0, prob))

        predictions.append(LinkPrediction(
            link_id=lid,
            failure_probability=prob,
            trend_slope=round(loss_slope, 6),
            estimated_ttf_seconds=round(ttf_seconds, 1) if ttf_seconds is not None else None,
            current_loss_rate=round(current_loss, 4),
            current_latency_ms=round(current_lat, 2),
            confidence=round(confidence, 3),
        ))

    return sorted(predictions, key=lambda p: p.failure_probability, reverse=True)

