"""
NEXUS — Topology API routes.
CRUD for NetworkTopology, nodes, and links.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models.network import NetworkLink, NetworkNode, NetworkTopology
from backend.simulation.topology import (
    TopologyConfig,
    build_random_topology,
    compute_topology_stats,
    topology_to_dict,
)

router = APIRouter(prefix="/topologies", tags=["Topologies"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class TopologyCreate(BaseModel):
    name: str
    description: str | None = None


class TopologyGenerateRequest(BaseModel):
    name: str
    num_nodes: int = 10
    edge_probability: float = 0.35
    seed: int = 42


class TopologyResponse(BaseModel):
    id: int
    name: str
    description: str | None
    num_nodes: int
    num_links: int

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[TopologyResponse])
async def list_topologies(db: AsyncSession = Depends(get_db)):
    """List all saved topologies."""
    result = await db.execute(
        select(NetworkTopology).options(
            selectinload(NetworkTopology.nodes),
            selectinload(NetworkTopology.links),
        )
    )
    topologies = result.scalars().all()
    return [
        TopologyResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            num_nodes=len(t.nodes),
            num_links=len(t.links),
        )
        for t in topologies
    ]


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_topology(
    req: TopologyGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate a random topology, persist it, and return the graph + stats."""
    # Check name uniqueness
    existing = await db.execute(
        select(NetworkTopology).where(NetworkTopology.name == req.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Topology '{req.name}' already exists.",
        )

    cfg = TopologyConfig(
        name=req.name,
        num_nodes=req.num_nodes,
        edge_probability=req.edge_probability,
        seed=req.seed,
    )
    G = build_random_topology(cfg)
    stats = compute_topology_stats(G)
    graph_dict = topology_to_dict(G)

    # Persist
    topology = NetworkTopology(name=req.name, description=f"Auto-generated, seed={req.seed}")
    db.add(topology)
    await db.flush()  # get topology.id

    for node_data in graph_dict["nodes"]:
        db.add(NetworkNode(
            topology_id=topology.id,
            node_id=node_data["id"],
            node_type=node_data.get("node_type", "router"),
            label=node_data.get("label"),
            risk_weight=node_data.get("risk_weight", 1.0),
        ))

    for link_data in graph_dict["links"]:
        db.add(NetworkLink(
            topology_id=topology.id,
            source=link_data["source"],
            target=link_data["target"],
            bandwidth_mbps=link_data.get("bandwidth_mbps", 1000.0),
            latency_ms=link_data.get("latency_ms", 1.0),
            loss_rate=link_data.get("loss_rate", 0.0),
            cost=link_data.get("cost", 1.0),
        ))

    await db.commit()

    return {
        "id": topology.id,
        "name": topology.name,
        "graph": graph_dict,
        "stats": {
            "num_nodes": stats.num_nodes,
            "num_edges": stats.num_edges,
            "is_connected": stats.is_connected,
            "avg_degree": stats.avg_degree,
            "diameter": stats.diameter,
            "avg_clustering": stats.avg_clustering,
            "density": stats.density,
        },
    }


@router.get("/{topology_id}")
async def get_topology(
    topology_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve a full topology with its nodes and links."""
    result = await db.execute(
        select(NetworkTopology)
        .where(NetworkTopology.id == topology_id)
        .options(
            selectinload(NetworkTopology.nodes),
            selectinload(NetworkTopology.links),
        )
    )
    topology = result.scalar_one_or_none()
    if not topology:
        raise HTTPException(status_code=404, detail="Topology not found.")

    return {
        "id": topology.id,
        "name": topology.name,
        "description": topology.description,
        "nodes": [
            {
                "id": n.node_id,
                "label": n.label,
                "node_type": n.node_type,
                "risk_weight": n.risk_weight,
            }
            for n in topology.nodes
        ],
        "links": [
            {
                "source": lnk.source,
                "target": lnk.target,
                "bandwidth_mbps": lnk.bandwidth_mbps,
                "latency_ms": lnk.latency_ms,
                "cost": lnk.cost,
            }
            for lnk in topology.links
        ],
    }


@router.delete("/{topology_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topology(
    topology_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a topology and all its associated data."""
    result = await db.execute(
        select(NetworkTopology).where(NetworkTopology.id == topology_id)
    )
    topology = result.scalar_one_or_none()
    if not topology:
        raise HTTPException(status_code=404, detail="Topology not found.")
    await db.delete(topology)
    await db.commit()

