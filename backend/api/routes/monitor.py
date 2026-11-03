"""
NEXUS — Network Monitoring API routes.
Synthetic telemetry, threshold alerts, and failure prediction.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models.network import NetworkTopology
from backend.simulation.monitor import detect_alerts, generate_link_telemetry
from backend.simulation.prediction import predict_link_failures

router = APIRouter(prefix="/monitor", tags=["Monitoring"])


class TelemetryRequest(BaseModel):
    degraded_links: list[str] = []
    seed: int | None = None


@router.post("/{topology_id}/telemetry")
async def get_telemetry(
    topology_id: int,
    req: TelemetryRequest = TelemetryRequest(),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate a snapshot of synthetic link telemetry for a topology."""
    result = await db.execute(
        select(NetworkTopology)
        .where(NetworkTopology.id == topology_id)
        .options(selectinload(NetworkTopology.links))
    )
    topology = result.scalar_one_or_none()
    if not topology:
        raise HTTPException(status_code=404, detail="Topology not found.")

    links_data = [
        {
            "source": lnk.source,
            "target": lnk.target,
            "bandwidth_mbps": lnk.bandwidth_mbps,
            "latency_ms": lnk.latency_ms,
        }
        for lnk in topology.links
    ]

    telemetry = generate_link_telemetry(
        links=links_data,
        seed=req.seed,
        degraded_links=req.degraded_links,
    )
    alerts = detect_alerts(telemetry)

    return {
        "topology_id": topology_id,
        "topology_name": topology.name,
        "link_count": len(telemetry),
        "telemetry": [t.to_dict() for t in telemetry],
        "alerts": [a.to_dict() for a in alerts],
        "alert_count": len(alerts),
    }


@router.get("/{topology_id}/alerts")
async def get_alerts(
    topology_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get current alerts for a topology."""
    result = await db.execute(
        select(NetworkTopology)
        .where(NetworkTopology.id == topology_id)
        .options(selectinload(NetworkTopology.links))
    )
    topology = result.scalar_one_or_none()
    if not topology:
        raise HTTPException(status_code=404, detail="Topology not found.")

    links_data = [
        {
            "source": lnk.source,
            "target": lnk.target,
            "bandwidth_mbps": lnk.bandwidth_mbps,
            "latency_ms": lnk.latency_ms,
        }
        for lnk in topology.links
    ]
    telemetry = generate_link_telemetry(links=links_data)
    alerts = detect_alerts(telemetry)

    return {
        "topology_id": topology_id,
        "alert_count": len(alerts),
        "alerts": [a.to_dict() for a in alerts],
    }


class PredictRequest(BaseModel):
    snapshots: list[list[dict]]  # list of telemetry snapshots, oldest first


@router.post("/{topology_id}/predict")
async def predict_failures(
    topology_id: int,
    req: PredictRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Predict link failure probabilities from historical telemetry snapshots."""
    result = await db.execute(
        select(NetworkTopology).where(NetworkTopology.id == topology_id)
    )
    topology = result.scalar_one_or_none()
    if not topology:
        raise HTTPException(status_code=404, detail="Topology not found.")

    predictions = predict_link_failures(req.snapshots)
    high_risk = [p for p in predictions if p.failure_probability > 0.6]

    return {
        "topology_id": topology_id,
        "predictions": [p.to_dict() for p in predictions],
        "high_risk_links": [p.link_id for p in high_risk],
        "high_risk_count": len(high_risk),
    }

