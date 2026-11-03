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


def _annotate_graph(G: nx.Graph, rng: random.Random) -> nx.Graph:
    """Add NEXUS risk_weight / bandwidth / latency / cost attributes."""
    for node in G.nodes:
        if "label" not in G.nodes[node]:
            G.nodes[node]["label"] = f"R{node}"
        if "node_type" not in G.nodes[node]:
            G.nodes[node]["node_type"] = "router"
        G.nodes[node]["risk_weight"] = round(rng.uniform(0.1, 1.0), 3)
    for u, v in G.edges:
        G.edges[u, v]["bandwidth_mbps"] = rng.choice([100, 1000, 10000])
        G.edges[u, v]["latency_ms"] = round(rng.uniform(0.5, 50.0), 2)
        G.edges[u, v]["loss_rate"] = round(rng.uniform(0.0, 0.05), 4)
        G.edges[u, v]["cost"] = round(rng.uniform(1.0, 10.0), 2)
    return G


def build_abilene_topology() -> nx.Graph:
    """
    12-node approximation of the Abilene/Internet2 US backbone network.
    Nodes represent PoPs; edges represent OC-192 10 Gbps links.
    """
    G = nx.Graph()
    pops = [
        ("SEA", "Seattle"), ("SFO", "San Francisco"), ("LAX", "Los Angeles"),
        ("DEN", "Denver"), ("HOU", "Houston"), ("KCI", "Kansas City"),
        ("CHI", "Chicago"), ("ATL", "Atlanta"), ("WDC", "Washington DC"),
        ("NYC", "New York"), ("CLE", "Cleveland"), ("IND", "Indianapolis"),
    ]
    for node_id, label in pops:
        G.add_node(node_id, label=label, node_type="router",
                   risk_weight=round(random.Random(hash(node_id)).uniform(0.1, 0.8), 3))

    links = [
        ("SEA", "SFO"), ("SFO", "LAX"), ("LAX", "DEN"), ("DEN", "HOU"),
        ("DEN", "KCI"), ("KCI", "CHI"), ("KCI", "HOU"), ("HOU", "ATL"),
        ("CHI", "IND"), ("IND", "CLE"), ("CLE", "NYC"), ("CLE", "WDC"),
        ("WDC", "NYC"), ("WDC", "ATL"), ("NYC", "CHI"), ("ATL", "CHI"),
        ("SEA", "DEN"), ("SFO", "DEN"),
    ]
    rng = random.Random(2001)
    for src, tgt in links:
        G.add_edge(src, tgt,
                   bandwidth_mbps=10000,
                   latency_ms=round(rng.uniform(5.0, 80.0), 2),
                   loss_rate=round(rng.uniform(0.0, 0.01), 4),
                   cost=round(rng.uniform(1.0, 5.0), 2))
    return G


def build_fat_tree_topology(k: int = 4) -> nx.Graph:
    """
    Fat-tree data-center topology with k pods.
    k must be even. Produces k^3/4 hosts, k^2/4 core switches,
    k^2/2 aggregation switches, k^2/2 edge switches.
    """
    G = nx.Graph()
    rng = random.Random(k)

    num_core = (k // 2) ** 2
    num_pods = k
    num_agg_per_pod = k // 2
    num_edge_per_pod = k // 2
    num_hosts_per_edge = k // 2

    # Core switches
    core_nodes = [f"core_{i}" for i in range(num_core)]
    for n in core_nodes:
        G.add_node(n, label=n, node_type="switch", risk_weight=round(rng.uniform(0.2, 0.6), 3))

    for pod in range(num_pods):
        agg_nodes = [f"agg_{pod}_{j}" for j in range(num_agg_per_pod)]
        edge_nodes = [f"edge_{pod}_{j}" for j in range(num_edge_per_pod)]

        for n in agg_nodes:
            G.add_node(n, label=n, node_type="switch", risk_weight=round(rng.uniform(0.3, 0.7), 3))
        for n in edge_nodes:
            G.add_node(n, label=n, node_type="switch", risk_weight=round(rng.uniform(0.1, 0.4), 3))

        # Core ↔ Aggregation
        for j, agg in enumerate(agg_nodes):
            for i in range(num_agg_per_pod):
                core_idx = j * num_agg_per_pod + i
                G.add_edge(core_nodes[core_idx], agg,
                           bandwidth_mbps=10000, latency_ms=round(rng.uniform(0.1, 1.0), 2),
                           loss_rate=0.0, cost=1.0)

        # Aggregation ↔ Edge
        for agg in agg_nodes:
            for edge in edge_nodes:
                G.add_edge(agg, edge,
                           bandwidth_mbps=1000, latency_ms=round(rng.uniform(0.1, 0.5), 2),
                           loss_rate=0.0, cost=1.0)

        # Edge → Hosts (hosts as leaf nodes)
        for edge in edge_nodes:
            for h in range(num_hosts_per_edge):
                host = f"host_{pod}_{edge.split('_')[2]}_{h}"
                G.add_node(host, label=host, node_type="host",
                           risk_weight=round(rng.uniform(0.05, 0.2), 3))
                G.add_edge(edge, host,
                           bandwidth_mbps=100, latency_ms=round(rng.uniform(0.01, 0.1), 2),
                           loss_rate=0.0, cost=0.5)

    return G


def build_ring_topology(n: int = 8, seed: int = 42) -> nx.Graph:
    """Simple ring topology with optional chord shortcuts."""
    G = nx.cycle_graph(n)
    rng = random.Random(seed)
    # Add a few chords for redundancy
    num_chords = max(1, n // 4)
    nodes = list(G.nodes)
    added = 0
    attempts = 0
    while added < num_chords and attempts < 100:
        u, v = rng.sample(nodes, 2)
        if not G.has_edge(u, v):
            G.add_edge(u, v)
            added += 1
        attempts += 1
    return _annotate_graph(G, rng)


