"""Unit tests for network monitoring, telemetry, and failure prediction."""

import pytest
import time
from backend.simulation.monitor import (
    generate_link_telemetry,
    detect_alerts,
    LinkTelemetry,
    NetworkAlert,
)
from backend.simulation.prediction import (
    predict_link_failures,
    LinkPrediction,
)


def test_generate_telemetry_normal():
    links = [
        {"source": "0", "target": "1", "bandwidth_mbps": 1000.0, "latency_ms": 5.0},
        {"source": "1", "target": "2", "bandwidth_mbps": 10000.0, "latency_ms": 2.0},
    ]
    telemetry = generate_link_telemetry(links, seed=42)
    assert len(telemetry) == 2
    for t in telemetry:
        assert isinstance(t, LinkTelemetry)
        assert t.status == "OK"
        assert t.throughput_mbps > 0
        assert t.latency_ms > 0
        assert 0.0 <= t.loss_rate <= 1.0


def test_generate_telemetry_degraded_and_alerts():
    links = [
        {"source": "0", "target": "1", "bandwidth_mbps": 1000.0, "latency_ms": 5.0},
        {"source": "1", "target": "2", "bandwidth_mbps": 1000.0, "latency_ms": 5.0},
    ]
    telemetry = generate_link_telemetry(links, seed=42, degraded_links=["0->1"])
    assert len(telemetry) == 2

    # Link 0->1 should be degraded or critical
    t0 = next(t for t in telemetry if t.link_id == "0->1")
    assert t0.status in ("DEGRADED", "CRITICAL")
    assert t0.loss_rate > 0.05

    # Detect alerts
    alerts = detect_alerts(telemetry)
    assert len(alerts) >= 1
    assert any(a.link_id == "0->1" for a in alerts)


def test_failure_prediction():
    # Build 5 consecutive snapshots where link 0->1 is progressively degrading
    now = time.time()
    snapshots = []
    for step in range(5):
        snapshots.append([
            {
                "link_id": "0->1",
                "loss_rate": 0.02 + step * 0.03,  # 0.02, 0.05, 0.08, 0.11, 0.14
                "latency_ms": 10.0 + step * 10.0,
                "timestamp": now + step * 30.0,
            },
            {
                "link_id": "1->2",
                "loss_rate": 0.001,
                "latency_ms": 2.0,
                "timestamp": now + step * 30.0,
            },
        ])

    predictions = predict_link_failures(snapshots)
    assert len(predictions) == 2

    p_degraded = next(p for p in predictions if p.link_id == "0->1")
    p_healthy = next(p for p in predictions if p.link_id == "1->2")

    assert p_degraded.failure_probability > p_healthy.failure_probability
    assert p_degraded.trend_slope > 0
    assert p_degraded.estimated_ttf_seconds is not None

