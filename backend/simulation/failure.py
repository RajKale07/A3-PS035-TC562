"""
NEXUS — Adaptive Network Resilience Intelligence
Failure scenario simulation engine: node/link failures, cascade analysis.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from typing import Any

import networkx as nx


@dataclass
class FailureScenario:
    """Defines a failure injection scenario."""

    name: str
    failed_nodes: list[str] = field(default_factory=list)
    failed_links: list[tuple[str, str]] = field(default_factory=list)
    description: str = ""


@dataclass
class SimulationReport:
    """Result of running a failure scenario on a topology."""

    scenario: str
    resilience_score: float           # 0.0 (total failure) → 1.0 (fully resilient)
    connectivity_ratio: float         # fraction of node pairs still reachable
    avg_path_length: float | None     # None if disconnected
    failed_nodes: list[str]
    surviving_nodes: int
    surviving_edges: int
    components: int                   # number of connected components after failure
    duration_ms: float
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "resilience_score": self.resilience_score,
            "connectivity_ratio": self.connectivity_ratio,
            "avg_path_length": self.avg_path_length,
            "failed_nodes": self.failed_nodes,
            "surviving_nodes": self.surviving_nodes,
            "surviving_edges": self.surviving_edges,
            "components": self.components,
            "duration_ms": self.duration_ms,
            "details": self.details,
        }


def run_failure_simulation(
    G: nx.Graph,
    scenario: FailureScenario,
) -> SimulationReport:
    """
    Inject node/link failures into graph G and compute resilience metrics.

    The original graph G is NOT mutated — a copy is used.
    """
    t0 = time.perf_counter()

    H: nx.Graph = G.copy()

    # Remove failed nodes (and their incident edges automatically).
    # Node IDs may be stored as int or str; try both forms.
    node_set = set(H.nodes())
    actual_failed = []
    for n in scenario.failed_nodes:
        if n in node_set:
            actual_failed.append(n)
        else:
            # Try numeric conversion (graph uses int nodes, scenario uses str)
            try:
                n_int = int(n)
                if n_int in node_set:
                    actual_failed.append(n_int)
            except (ValueError, TypeError):
                pass
    H.remove_nodes_from(actual_failed)

    # Remove failed links
    for src, tgt in scenario.failed_links:
        if H.has_edge(src, tgt):
            H.remove_edge(src, tgt)

    # --- Metrics ---
    n_total = G.number_of_nodes()
    n_surviving = H.number_of_nodes()
    components = nx.number_connected_components(H)

    # Connectivity ratio: fraction of original node pairs still reachable
    if n_surviving < 2:
        connectivity_ratio = 0.0
        avg_path: float | None = None
    else:
        largest_cc = max(nx.connected_components(H), key=len)
        largest_cc_size = len(largest_cc)
        max_pairs = n_total * (n_total - 1)
        reachable_pairs = largest_cc_size * (largest_cc_size - 1)
        connectivity_ratio = reachable_pairs / max_pairs if max_pairs > 0 else 0.0

        try:
            subgraph = H.subgraph(largest_cc)
            avg_path = round(nx.average_shortest_path_length(subgraph), 4)
        except nx.NetworkXError:
            avg_path = None

    # Resilience score: weighted combination of connectivity and size preservation
    size_ratio = n_surviving / n_total if n_total > 0 else 0.0
    resilience_score = round(0.6 * connectivity_ratio + 0.4 * size_ratio, 4)

    duration_ms = round((time.perf_counter() - t0) * 1000, 3)

    return SimulationReport(
        scenario=scenario.name,
        resilience_score=resilience_score,
        connectivity_ratio=round(connectivity_ratio, 4),
        avg_path_length=avg_path,
        failed_nodes=[str(n) for n in actual_failed],
        surviving_nodes=n_surviving,
        surviving_edges=H.number_of_edges(),
        components=components,
        duration_ms=duration_ms,
        details={
            "original_nodes": n_total,
            "original_edges": G.number_of_edges(),
            "failed_links": [list(lnk) for lnk in scenario.failed_links],
        },
    )


def random_node_failure_scenario(
    G: nx.Graph,
    failure_fraction: float = 0.2,
    seed: int = 0,
) -> FailureScenario:
    """Create a scenario that randomly removes `failure_fraction` of nodes."""
    rng = random.Random(seed)
    nodes = list(G.nodes)
    k = max(1, int(len(nodes) * failure_fraction))
    failed = rng.sample(nodes, k)
    return FailureScenario(
        name=f"random_{int(failure_fraction * 100)}pct_failure",
        failed_nodes=[str(n) for n in failed],
        description=f"Random {failure_fraction:.0%} node failure",
    )


def targeted_hub_failure_scenario(G: nx.Graph, top_k: int = 3) -> FailureScenario:
    """Create a scenario that removes the `top_k` highest-degree nodes (hubs)."""
    hubs = sorted(G.degree, key=lambda x: x[1], reverse=True)[:top_k]
    return FailureScenario(
        name=f"hub_failure_top{top_k}",
        failed_nodes=[str(n) for n, _ in hubs],
        description=f"Targeted removal of top-{top_k} hub nodes",
    )

