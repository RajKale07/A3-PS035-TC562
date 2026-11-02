"""
NEXUS — Simulation API routes.
Run failure scenarios against stored topologies.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models.network import NetworkTopology, SimulationResult
from backend.simulation.failure import (
    FailureScenario,
    random_node_failure_scenario,
    run_failure_simulation,
    targeted_hub_failure_scenario,
)
from backend.simulation.mininet_bridge import run_mininet_emulation
from backend.simulation.topology import build_topology_from_dict, topology_to_dict

router = APIRouter(prefix="/simulations", tags=["Simulations"])


class RunSimulationRequest(BaseModel):
    topology_id: int
    scenario_type: str = "random"       # "random" | "hub" | "custom"
    failure_fraction: float = 0.2       # used for "random"
    top_k_hubs: int = 3                 # used for "hub"
    custom_failed_nodes: list[str] = []  # used for "custom"
    seed: int = 42


@router.post("/run")
async def run_simulation(
    req: RunSimulationRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Run a failure simulation scenario on a stored topology."""

    # Load topology
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

    # Reconstruct NetworkX graph from DB records
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

    # Build scenario
    if req.scenario_type == "random":
        scenario = random_node_failure_scenario(
            G, failure_fraction=req.failure_fraction, seed=req.seed
        )
    elif req.scenario_type == "hub":
        scenario = targeted_hub_failure_scenario(G, top_k=req.top_k_hubs)
    elif req.scenario_type == "custom":
        scenario = FailureScenario(
            name="custom_failure",
            failed_nodes=req.custom_failed_nodes,
            description="User-defined failure scenario",
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown scenario_type: {req.scenario_type}")

    # Run simulation
    report = run_failure_simulation(G, scenario)

    # Persist result
    import json
    db_result = SimulationResult(
        topology_id=topology.id,
        scenario=report.scenario,
        resilience_score=report.resilience_score,
        connectivity_ratio=report.connectivity_ratio,
        avg_path_length=report.avg_path_length,
        failed_nodes=json.dumps(report.failed_nodes),
        optimizer_output=None,
        duration_ms=report.duration_ms,
    )
    db.add(db_result)
    await db.commit()
    await db.refresh(db_result)

    return {
        "simulation_id": db_result.id,
        "topology_name": topology.name,
        **report.to_dict(),
    }


@router.get("/{topology_id}/history")
async def simulation_history(
    topology_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return all simulation runs for a given topology."""
    result = await db.execute(
        select(SimulationResult)
        .where(SimulationResult.topology_id == topology_id)
        .order_by(SimulationResult.created_at.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "scenario": r.scenario,
            "resilience_score": r.resilience_score,
            "connectivity_ratio": r.connectivity_ratio,
            "duration_ms": r.duration_ms,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


class EmulateWSLRequest(BaseModel):
    topology_id: int
    failed_nodes: list[str] = []


@router.post("/emulate-wsl")
async def emulate_wsl(
    req: EmulateWSLRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Execute live Mininet emulation inside WSL2 Ubuntu for this topology."""
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

    nodes_data = [{"id": n.node_id} for n in topology.nodes]
    links_data = [
        {
            "source": lnk.source,
            "target": lnk.target,
            "bandwidth_mbps": int(lnk.bandwidth_mbps),
            "latency_ms": float(lnk.latency_ms),
        }
        for lnk in topology.links
    ]

    report = run_mininet_emulation(
        topology_name=topology.name,
        nodes=nodes_data,
        links=links_data,
        failed_nodes=req.failed_nodes,
    )

    return report.to_dict()

