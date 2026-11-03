"""
NEXUS — Continuous Network Monitoring & Telemetry Generator.
Produces synthetic time-series telemetry per link.
Detects threshold violations and generates alerts.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class LinkTelemetry:
    link_id: str          # "src->tgt"
    source: str
    target: str
    timestamp: float      # unix seconds
    throughput_mbps: float
    latency_ms: float
    loss_rate: float      # 0.0–1.0
    jitter_ms: float
    status: str           # "OK" | "DEGRADED" | "CRITICAL"

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_id": self.link_id,
            "source": self.source,
            "target": self.target,
            "timestamp": self.timestamp,
            "throughput_mbps": self.throughput_mbps,
            "latency_ms": self.latency_ms,
            "loss_rate": self.loss_rate,
            "jitter_ms": self.jitter_ms,
            "status": self.status,
        }


@dataclass
class NetworkAlert:
    alert_id: str
    link_id: str
    severity: str         # "WARNING" | "CRITICAL"
    metric: str
    value: float
    threshold: float
    message: str
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "link_id": self.link_id,
            "severity": self.severity,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
            "timestamp": self.timestamp,
        }


def generate_link_telemetry(
    links: list[dict],
    seed: int | None = None,
    degraded_links: list[str] | None = None,
) -> list[LinkTelemetry]:
    """
    Generate one snapshot of synthetic telemetry for each link.

    links: list of {"source", "target", "bandwidth_mbps", "latency_ms"}
    degraded_links: list of link_ids ("src->tgt") to inject anomalies into
    """
    rng = random.Random(seed if seed is not None else int(time.time() * 1000) % 2**31)
    degraded_set = set(degraded_links or [])
    now = time.time()

    telemetry = []
    for lnk in links:
        src = str(lnk.get("source", "?"))
        tgt = str(lnk.get("target", "?"))
        link_id = f"{src}->{tgt}"
        bw = float(lnk.get("bandwidth_mbps", 1000.0))
        base_lat = float(lnk.get("latency_ms", 5.0))

        is_degraded = link_id in degraded_set or f"{tgt}->{src}" in degraded_set

        if is_degraded:
            throughput = round(rng.uniform(0.01, 0.3) * bw, 2)
            latency = round(base_lat * rng.uniform(3.0, 8.0), 2)
            loss_rate = round(rng.uniform(0.08, 0.4), 4)
            jitter = round(rng.uniform(10.0, 50.0), 2)
        else:
            throughput = round(rng.uniform(0.4, 0.9) * bw, 2)
            latency = round(base_lat * rng.uniform(0.8, 1.3), 2)
            loss_rate = round(rng.uniform(0.0, 0.02), 4)
            jitter = round(rng.uniform(0.1, 2.0), 2)

        if loss_rate > 0.1 or latency > base_lat * 5:
            status = "CRITICAL"
        elif loss_rate > 0.05 or latency > base_lat * 2:
            status = "DEGRADED"
        else:
            status = "OK"

        telemetry.append(LinkTelemetry(
            link_id=link_id,
            source=src,
            target=tgt,
            timestamp=now,
            throughput_mbps=throughput,
            latency_ms=latency,
            loss_rate=loss_rate,
            jitter_ms=jitter,
            status=status,
        ))

    return telemetry


def detect_alerts(telemetry: list[LinkTelemetry]) -> list[NetworkAlert]:
    """Scan telemetry snapshot and produce alerts for threshold violations."""
    alerts = []
    now = time.time()
    for i, t in enumerate(telemetry):
        if t.loss_rate > 0.1:
            alerts.append(NetworkAlert(
                alert_id=f"alert_{i}_loss_critical",
                link_id=t.link_id,
                severity="CRITICAL",
                metric="loss_rate",
                value=t.loss_rate,
                threshold=0.1,
                message=f"Link {t.link_id}: loss {t.loss_rate:.1%} exceeds critical 10%",
                timestamp=now,
            ))
        elif t.loss_rate > 0.05:
            alerts.append(NetworkAlert(
                alert_id=f"alert_{i}_loss_warning",
                link_id=t.link_id,
                severity="WARNING",
                metric="loss_rate",
                value=t.loss_rate,
                threshold=0.05,
                message=f"Link {t.link_id}: loss {t.loss_rate:.1%} exceeds warning 5%",
                timestamp=now,
            ))
        if t.status == "CRITICAL" and t.loss_rate <= 0.1:
            alerts.append(NetworkAlert(
                alert_id=f"alert_{i}_latency_critical",
                link_id=t.link_id,
                severity="CRITICAL",
                metric="latency_ms",
                value=t.latency_ms,
                threshold=0.0,
                message=f"Link {t.link_id}: latency {t.latency_ms:.1f}ms critically high",
                timestamp=now,
            ))
    return alerts

