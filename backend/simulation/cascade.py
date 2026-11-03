"""
NEXUS — Cascading Failure Engine (Motter-Lai model).
Each node has capacity = initial_load * (1 + tolerance).
When a node fails, its load redistributes via shortest paths.
Nodes exceeding capacity fail in the next step (cascade).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import networkx as nx


@dataclass
class CascadeStep:
    step: int
    newly_failed: list[str]
    overloaded: list[str]
    surviving_nodes: int
    surviving_edges: int
    load_distribution: dict[str, float]  # node_id -> current_load


@dataclass
class CascadeReport:
    total_steps: int
    initial_failed: list[str]
    all_failed: list[str]
    steps: list[CascadeStep]
    final_resilience_score: float
    final_connectivity_ratio: float
    cascade_amplification: float  # all_failed / initial_failed ratio
    duration_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_steps": self.total_steps,
            "initial_failed": self.initial_failed,
            "all_failed": self.all_failed,
            "steps": [
                {
                    "step": s.step,
                    "newly_failed": s.newly_failed,
                    "overloaded": s.overloaded,
                    "surviving_nodes": s.surviving_nodes,
                    "surviving_edges": s.surviving_edges,
                    "load_distribution": s.load_distribution,
                }
                for s in self.steps
            ],
            "final_resilience_score": self.final_resilience_score,
            "final_connectivity_ratio": self.final_connectivity_ratio,
            "cascade_amplification": self.cascade_amplification,
            "duration_ms": self.duration_ms,
        }


def _compute_loads(G: nx.Graph) -> dict:
    """Betweenness centrality as proxy for load, scaled to [1, 100]."""
    if G.number_of_nodes() < 2:
        return {n: 1.0 for n in G.nodes()}
    bc = nx.betweenness_centrality(G, normalized=True)
    max_bc = max(bc.values()) if bc else 1.0
    if max_bc == 0:
        max_bc = 1.0
    return {n: max(1.0, bc[n] / max_bc * 100.0) for n in G.nodes()}


def _resolve_nodes(node_ids: list[str], node_set: set) -> list:
    """Resolve string node IDs to whatever type is in the graph."""
    resolved = []
    for n in node_ids:
        if n in node_set:
            resolved.append(n)
        else:
            try:
                n_int = int(n)
                if n_int in node_set:
                    resolved.append(n_int)
            except (ValueError, TypeError):
                pass
    return resolved


def run_cascade_simulation(
    G: nx.Graph,
    initial_failed: list[str],
    tolerance: float = 0.2,
    max_steps: int = 20,
) -> CascadeReport:
    """
    Run Motter-Lai cascading failure model.

    tolerance: capacity = initial_load * (1 + tolerance)
    initial_failed: node IDs (str) to remove at step 0
    """
    t0 = time.perf_counter()

    H = G.copy()
    node_set = set(H.nodes())

    resolved_initial = _resolve_nodes(initial_failed, node_set)

    # Compute initial loads and capacities on the FULL graph
    initial_loads = _compute_loads(H)
    capacities = {n: initial_loads[n] * (1.0 + tolerance) for n in H.nodes()}

    # Step 0: remove initial failures
    H.remove_nodes_from(resolved_initial)
    all_failed: list = list(resolved_initial)
    steps: list[CascadeStep] = []

    for step in range(1, max_steps + 1):
        if H.number_of_nodes() == 0:
            break

        # Recompute loads after failures
        current_loads = _compute_loads(H)

        # Find overloaded nodes (load exceeds original capacity)
        overloaded = [
            n for n in H.nodes()
            if current_loads.get(n, 0.0) > capacities.get(n, float("inf"))
        ]

        load_dist = {str(n): round(current_loads.get(n, 0.0), 4) for n in H.nodes()}

        steps.append(CascadeStep(
            step=step,
            newly_failed=[str(n) for n in overloaded],
            overloaded=[str(n) for n in overloaded],
            surviving_nodes=H.number_of_nodes(),
            surviving_edges=H.number_of_edges(),
            load_distribution=load_dist,
        ))

        if not overloaded:
            break  # cascade stabilized

        H.remove_nodes_from(overloaded)
        all_failed.extend(overloaded)

    n_total = G.number_of_nodes()
    n_surviving = H.number_of_nodes()

    if n_surviving >= 2:
        largest_cc = max(nx.connected_components(H), key=len)
        lcc_size = len(largest_cc)
        max_pairs = n_total * (n_total - 1)
        reachable = lcc_size * (lcc_size - 1)
        connectivity_ratio = reachable / max_pairs if max_pairs > 0 else 0.0
    else:
        connectivity_ratio = 0.0

    size_ratio = n_surviving / n_total if n_total > 0 else 0.0
    resilience_score = round(0.6 * connectivity_ratio + 0.4 * size_ratio, 4)
    cascade_amp = round(len(all_failed) / max(1, len(resolved_initial)), 3)

    duration_ms = round((time.perf_counter() - t0) * 1000, 3)

    return CascadeReport(
        total_steps=len(steps),
        initial_failed=[str(n) for n in resolved_initial],
        all_failed=[str(n) for n in all_failed],
        steps=steps,
        final_resilience_score=resilience_score,
        final_connectivity_ratio=round(connectivity_ratio, 4),
        cascade_amplification=cascade_amp,
        duration_ms=duration_ms,
    )

