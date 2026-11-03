"""
NEXUS — Recovery Plan API routes.
Human-in-the-loop approval workflow for network recovery actions.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models.network import NetworkTopology, RecoveryPlan, SimulationResult
from backend.optimizer.resilience import OptimizationConfig, find_resilient_paths
from backend.simulation.failure import random_node_failure_scenario, run_failure_simulation
from backend.simulation.topology import build_topology_from_dict

router = APIRouter(prefix="/recovery", tags=["Recovery"])


class GenerateRecoveryRequest(BaseModel):
    topology_id: int
    simulation_id: int | None = None
    source: str = "0"
    target: str = "1"
    max_risk: float = 10.0
    max_paths: int = 3


class ApproveRejectRequest(BaseModel):
    notes: str = ""


def _build_graph_dict(topology: NetworkTopology) -> dict:
    return {
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


@router.post("/generate", status_code=201)
async def generate_recovery_plan(
    req: GenerateRecoveryRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate a recovery plan (optimizer paths) and store it as PENDING."""
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

    G = build_topology_from_dict(_build_graph_dict(topology))

    # Run optimizer to find resilient paths
    cfg = OptimizationConfig(
        source=req.source,
        target=req.target,
        max_risk=req.max_risk,
        max_paths=req.max_paths,
    )
    opt_result = find_resilient_paths(G, cfg)

    # Compute baseline resilience before failure
    scenario = random_node_failure_scenario(G, failure_fraction=0.2, seed=42)
    report_before = run_failure_simulation(G, scenario)

    actions = [
        {
            "action": "reroute",
            "path": p.nodes,
            "total_cost": p.total_cost,
            "total_risk": p.total_risk,
            "total_latency_ms": p.total_latency_ms,
        }
        for p in opt_result.paths
    ]

    total_risk_val = sum(p.total_risk for p in opt_result.paths) if opt_result.paths else 0.0

    plan = RecoveryPlan(
        topology_id=req.topology_id,
        simulation_id=req.simulation_id,
        actions_json=json.dumps(actions),
        status="PENDING",
        resilience_before=report_before.resilience_score,
        risk_delta=total_risk_val,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return {
        "plan_id": plan.id,
        "status": plan.status,
        "topology_id": plan.topology_id,
        "actions": actions,
        "optimizer_result": opt_result.to_dict(),
        "resilience_before": plan.resilience_before,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
    }


@router.post("/{plan_id}/approve")
async def approve_recovery_plan(
    plan_id: int,
    req: ApproveRejectRequest = ApproveRejectRequest(),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Approve and execute a recovery plan."""
    result = await db.execute(select(RecoveryPlan).where(RecoveryPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Recovery plan not found.")
    if plan.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Plan is already {plan.status}.")

    # Load topology to simulate post-recovery resilience
    topo_result = await db.execute(
        select(NetworkTopology)
        .where(NetworkTopology.id == plan.topology_id)
        .options(selectinload(NetworkTopology.nodes), selectinload(NetworkTopology.links))
    )
    topology = topo_result.scalar_one_or_none()

    resilience_after = None
    replanning = False
    if topology:
        G = build_topology_from_dict(_build_graph_dict(topology))
        # Simulate lighter failure after recovery
        scenario = random_node_failure_scenario(G, failure_fraction=0.1, seed=99)
        report_after = run_failure_simulation(G, scenario)
        resilience_after = report_after.resilience_score
        replanning = resilience_after < 0.8

    plan.status = "EXECUTED"
    plan.approved_at = datetime.now(timezone.utc)
    plan.executed_at = datetime.now(timezone.utc)
    plan.resilience_after = resilience_after
    plan.replanning_triggered = 1 if replanning else 0
    plan.outcome_json = json.dumps({
        "notes": req.notes,
        "execution_simulated": True,
        "resilience_after": resilience_after,
    })

    # Auto-replan if resilience still low
    new_plan_id = None
    if replanning and topology:
        new_plan = RecoveryPlan(
            topology_id=plan.topology_id,
            actions_json=plan.actions_json,
            status="PENDING",
            resilience_before=resilience_after,
        )
        db.add(new_plan)
        await db.flush()
        new_plan_id = new_plan.id

    await db.commit()

    return {
        "plan_id": plan.id,
        "status": plan.status,
        "resilience_before": plan.resilience_before,
        "resilience_after": resilience_after,
        "replanning_triggered": replanning,
        "new_plan_id": new_plan_id,
        "executed_at": plan.executed_at.isoformat() if plan.executed_at else None,
    }


@router.post("/{plan_id}/reject")
async def reject_recovery_plan(
    plan_id: int,
    req: ApproveRejectRequest = ApproveRejectRequest(),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Reject a pending recovery plan."""
    result = await db.execute(select(RecoveryPlan).where(RecoveryPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Recovery plan not found.")
    if plan.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Plan is already {plan.status}.")

    plan.status = "REJECTED"
    plan.outcome_json = json.dumps({"notes": req.notes})
    await db.commit()

    return {"plan_id": plan.id, "status": plan.status}


@router.get("/")
async def list_recovery_plans(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all recovery plans."""
    result = await db.execute(
        select(RecoveryPlan).order_by(RecoveryPlan.created_at.desc())
    )
    plans = result.scalars().all()
    return [
        {
            "plan_id": p.id,
            "topology_id": p.topology_id,
            "status": p.status,
            "resilience_before": p.resilience_before,
            "resilience_after": p.resilience_after,
            "replanning_triggered": bool(p.replanning_triggered),
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in plans
    ]


@router.get("/{plan_id}")
async def get_recovery_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get details of a specific recovery plan."""
    result = await db.execute(select(RecoveryPlan).where(RecoveryPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Recovery plan not found.")
    actions = json.loads(plan.actions_json) if plan.actions_json else []
    outcome = json.loads(plan.outcome_json) if plan.outcome_json else {}
    return {
        "plan_id": plan.id,
        "topology_id": plan.topology_id,
        "simulation_id": plan.simulation_id,
        "status": plan.status,
        "actions": actions,
        "resilience_before": plan.resilience_before,
        "resilience_after": plan.resilience_after,
        "risk_delta": plan.risk_delta,
        "replanning_triggered": bool(plan.replanning_triggered),
        "outcome": outcome,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "approved_at": plan.approved_at.isoformat() if plan.approved_at else None,
        "executed_at": plan.executed_at.isoformat() if plan.executed_at else None,
    }

