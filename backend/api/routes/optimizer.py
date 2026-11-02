"""
NEXUS — Optimizer API routes.
Run OR-Tools resilient path optimization on stored topologies.
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
from backend.optimizer.resilience import OptimizationConfig, find_resilient_paths
from backend.simulation.topology import build_topology_from_dict

router = APIRouter(prefix="/optimizer", tags=["Optimizer"])


class OptimizeRequest(BaseModel):
    topology_id: int
    source: str
    target: str
    max_risk: float = 5.0
    max_paths: int = 3
    time_limit_sec: float = 10.0


@router.post("/paths")
async def optimize_paths(
    req: OptimizeRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Find the K best risk-constrained resilient paths between two nodes
    using OR-Tools CP-SAT optimizer.
    """
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
            {"id": n.node_id, "risk_weight": n.risk_weight}
            for n in topology.nodes
        ],
        "links": [
            {
                "source": lnk.source,
                "target": lnk.target,
                "cost": lnk.cost,
                "latency_ms": lnk.latency_ms,
            }
            for lnk in topology.links
        ],
    }
    G = build_topology_from_dict(graph_dict)

    cfg = OptimizationConfig(
        source=req.source,
        target=req.target,
        max_risk=req.max_risk,
        max_paths=req.max_paths,
        time_limit_sec=req.time_limit_sec,
    )

    opt_result = find_resilient_paths(G, cfg)

    return {
        "topology_name": topology.name,
        **opt_result.to_dict(),
    }

