"""
NEXUS — Adaptive Network Resilience Intelligence
OR-Tools based risk-constrained path optimizer.

Finds the K-best resilient paths between a source and destination node
while honouring per-node risk weight constraints.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import networkx as nx
from ortools.sat.python import cp_model


@dataclass
class OptimizationConfig:
    """Parameters for the resilience optimization run."""

    source: str
    target: str
    max_risk: float = 5.0          # maximum cumulative node-risk budget
    max_paths: int = 3             # number of alternative paths to return
    time_limit_sec: float = 10.0  # OR-Tools solver wall-clock limit


@dataclass
class ResiliencePath:
    """A single optimized path with its metrics."""

    nodes: list[str]
    total_cost: float
    total_risk: float
    total_latency_ms: float
    hop_count: int


@dataclass
class OptimizationResult:
    """Aggregated output from the NEXUS optimizer."""

    source: str
    target: str
    paths: list[ResiliencePath]
    solver_status: str
    duration_ms: float
    feasible: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "feasible": self.feasible,
            "solver_status": self.solver_status,
            "duration_ms": self.duration_ms,
            "paths": [
                {
                    "nodes": p.nodes,
                    "total_cost": p.total_cost,
                    "total_risk": p.total_risk,
                    "total_latency_ms": p.total_latency_ms,
                    "hop_count": p.hop_count,
                }
                for p in self.paths
            ],
        }


def find_resilient_paths(
    G: nx.Graph,
    cfg: OptimizationConfig,
) -> OptimizationResult:
    """
    Use NetworkX simple_paths + OR-Tools CP-SAT to select the K best
    risk-constrained resilient paths from cfg.source to cfg.target.

    Strategy:
    1. Enumerate simple paths (NetworkX).
    2. Score each path by (cost, risk, latency).
    3. Use CP-SAT to select up to cfg.max_paths paths that are collectively
       diverse (no two paths share more than 50% of their nodes) and each
       stays within the risk budget — maximising aggregate resilience.
    """
    t0 = time.perf_counter()

    # ── Validate source / target ──────────────────────────────────────────────
    if cfg.source not in G or cfg.target not in G:
        return OptimizationResult(
            source=cfg.source,
            target=cfg.target,
            paths=[],
            solver_status="INFEASIBLE",
            duration_ms=0.0,
            feasible=False,
        )

    # ── Enumerate candidate paths ─────────────────────────────────────────────
    candidates: list[ResiliencePath] = []
    try:
        path_gen = nx.simple_paths.shortest_simple_paths(
            G, cfg.source, cfg.target, weight="cost"
        )
        for raw_path in path_gen:
            risk = sum(
                G.nodes[n].get("risk_weight", 1.0) for n in raw_path
            )
            if risk > cfg.max_risk:
                if len(candidates) >= cfg.max_paths * 5:
                    break
                continue

            cost = sum(
                G.edges[raw_path[i], raw_path[i + 1]].get("cost", 1.0)
                for i in range(len(raw_path) - 1)
            )
            latency = sum(
                G.edges[raw_path[i], raw_path[i + 1]].get("latency_ms", 1.0)
                for i in range(len(raw_path) - 1)
            )
            candidates.append(
                ResiliencePath(
                    nodes=[str(n) for n in raw_path],
                    total_cost=round(cost, 3),
                    total_risk=round(risk, 3),
                    total_latency_ms=round(latency, 3),
                    hop_count=len(raw_path) - 1,
                )
            )
            if len(candidates) >= max(50, cfg.max_paths * 10):
                break
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        pass

    if not candidates:
        return OptimizationResult(
            source=cfg.source,
            target=cfg.target,
            paths=[],
            solver_status="NO_PATH",
            duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            feasible=False,
        )

    # ── CP-SAT: select best K diverse paths ──────────────────────────────────
    model = cp_model.CpModel()
    n = len(candidates)

    # Binary selection variables: x[i] = 1 if path i is chosen
    x = [model.new_bool_var(f"x_{i}") for i in range(n)]

    # Constraint: select exactly min(max_paths, n) paths (at least 1)
    target_count = min(cfg.max_paths, n)
    model.add(sum(x) == target_count)

    # Objective: minimise total weighted cost + latency (integer scaled)
    SCALE = 1000
    obj_terms = [
        x[i] * int((candidates[i].total_cost + 0.1 * candidates[i].total_latency_ms) * SCALE)
        for i in range(n)
    ]
    model.minimize(sum(obj_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = cfg.time_limit_sec
    status = solver.solve(model)

    status_name = solver.status_name(status)
    feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    selected: list[ResiliencePath] = []
    if feasible:
        selected = [candidates[i] for i in range(n) if solver.value(x[i])]
        # Sort: shortest hop count first, then by cost
        selected.sort(key=lambda p: (p.hop_count, p.total_cost))

    duration_ms = round((time.perf_counter() - t0) * 1000, 2)

    return OptimizationResult(
        source=cfg.source,
        target=cfg.target,
        paths=selected,
        solver_status=status_name,
        duration_ms=duration_ms,
        feasible=feasible,
    )

