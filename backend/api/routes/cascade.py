"""
NEXUS — Cascading Failure API route.
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
from backend.simulation.cascade import run_cascade_simulation
from backend.simulation.topology import build_topology_from_dict

router = APIRouter(prefix="/simulations", tags=["Simulations"])


class CascadeRequest(BaseModel):
    topology_id: int
    initial_failed_nodes: list[str]
    tolerance: float = 0.2
    max_steps: int = 20


@router.post("/cascade")
async def run_cascade(
    req: CascadeRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Run a Motter-Lai cascading failure simulation on a stored topology."""
    result = await db.execute(
        select(NetworkTopology)
        .where(NetworkTopology.id == req.topology_id)
        .options(
            selectinload(NetworkTopology.nodes),
            selectinload(NetworkTopology.links),
        )
    )
    topology = result.scalar_one_or_none()
    if not topology:
        raise HTTPException(status_code=404, detail="Topology not found.")

    graph_dict = {
        "nodes": [
            {
                "id": n.node_id,
                "risk_weight": n.risk_weight,
                "label": n.label or n.node_id,
                "node_type": n.node_type,
            }
            for n in topology.nodes
        ],
        "links": [
            {
                "source": lnk.source,
                "target": lnk.target,
                "cost": lnk.cost,
                "latency_ms": lnk.latency_ms,
                "bandwidth_mbps": lnk.bandwidth_mbps,
            }
            for lnk in topology.links
        ],
    }
    G = build_topology_from_dict(graph_dict)

    report = run_cascade_simulation(
        G=G,
        initial_failed=req.initial_failed_nodes,
        tolerance=req.tolerance,
        max_steps=req.max_steps,
    )

    return {
        "topology_id": req.topology_id,
        "topology_name": topology.name,
        **report.to_dict(),
    }

