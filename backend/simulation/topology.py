"""
NEXUS — Adaptive Network Resilience Intelligence
NetworkX-based topology builder and graph analysis engine.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

import networkx as nx


@dataclass
class TopologyConfig:
    """Configuration for generating or loading a network topology."""

    name: str = "default"
    num_nodes: int = 10
    edge_probability: float = 0.35      # for random graphs
    seed: int = 42


@dataclass
class TopologyStats:
    """Graph-level metrics computed after topology is built."""

    num_nodes: int
    num_edges: int
    is_connected: bool
    avg_degree: float
    diameter: int | None                # None if disconnected
    avg_clustering: float
    avg_shortest_path: float | None     # None if disconnected
    density: float


def build_random_topology(cfg: TopologyConfig) -> nx.Graph:
    """
    Generate a random Erdős–Rényi network graph with NEXUS metadata.

    Each node gets a random 'risk_weight' [0.1, 1.0].
    Each edge gets 'bandwidth_mbps', 'latency_ms', 'cost' attributes.
    """
    G = nx.erdos_renyi_graph(n=cfg.num_nodes, p=cfg.edge_probability, seed=cfg.seed)

    rng = random.Random(cfg.seed)

    # Node attributes
    for node in G.nodes:
        G.nodes[node]["label"] = f"R{node}"
        G.nodes[node]["node_type"] = "router"
        G.nodes[node]["risk_weight"] = round(rng.uniform(0.1, 1.0), 3)

    # Edge attributes
    for u, v in G.edges:
        G.edges[u, v]["bandwidth_mbps"] = rng.choice([100, 1000, 10000])
        G.edges[u, v]["latency_ms"] = round(rng.uniform(0.5, 50.0), 2)
        G.edges[u, v]["loss_rate"] = round(rng.uniform(0.0, 0.05), 4)
        G.edges[u, v]["cost"] = round(rng.uniform(1.0, 10.0), 2)

    return G


def build_topology_from_dict(data: dict[str, Any]) -> nx.Graph:
    """
    Build a NetworkX graph from a JSON-serialisable topology dict.

    Expected format:
        {
          "nodes": [{"id": "R0", "risk_weight": 0.5, ...}, ...],
          "links": [{"source": "R0", "target": "R1", "cost": 2.0, ...}, ...]
        }
    """
    G = nx.Graph()

    for node in data.get("nodes", []):
        node_id = node.pop("id")
        G.add_node(node_id, **node)

    for link in data.get("links", []):
        src = link.pop("source")
        tgt = link.pop("target")
        G.add_edge(src, tgt, **link)

    return G


def compute_topology_stats(G: nx.Graph) -> TopologyStats:
    """Compute graph-level resilience metrics."""
    connected = nx.is_connected(G)
    degrees = [d for _, d in G.degree()]

    diameter: int | None = None
    avg_path: float | None = None
    if connected and len(G) > 0:
        try:
            diameter = nx.diameter(G)
            avg_path = round(nx.average_shortest_path_length(G), 4)
        except nx.NetworkXError:
            pass

    return TopologyStats(
        num_nodes=G.number_of_nodes(),
        num_edges=G.number_of_edges(),
        is_connected=connected,
        avg_degree=round(sum(degrees) / len(degrees), 3) if degrees else 0.0,
        diameter=diameter,
        avg_clustering=round(nx.average_clustering(G), 4),
        avg_shortest_path=avg_path,
        density=round(nx.density(G), 4),
    )


def topology_to_dict(G: nx.Graph) -> dict[str, Any]:
    """Serialise a NetworkX graph to a JSON-safe dict."""
    return {
        "nodes": [
            {"id": str(n), **attrs} for n, attrs in G.nodes(data=True)
        ],
        "links": [
            {"source": str(u), "target": str(v), **attrs}
            for u, v, attrs in G.edges(data=True)
        ],
    }

