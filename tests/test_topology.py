"""Unit tests for NEXUS network topology generation and metrics."""

import pytest
import networkx as nx
from backend.simulation.topology import (
    TopologyConfig,
    build_random_topology,
    compute_topology_stats,
    build_topology_from_dict,
    topology_to_dict,
)


def test_build_random_topology_attributes():
    cfg = TopologyConfig(name="test_topo", num_nodes=8, edge_probability=0.5, seed=42)
    G = build_random_topology(cfg)

    assert G.number_of_nodes() == 8
    assert G.number_of_edges() > 0

    # Verify node attributes
    for node, attrs in G.nodes(data=True):
        assert "risk_weight" in attrs
        assert 0.1 <= attrs["risk_weight"] <= 1.0
        assert attrs["node_type"] == "router"
        assert attrs["label"].startswith("R")

    # Verify edge attributes
    for u, v, attrs in G.edges(data=True):
        assert "bandwidth_mbps" in attrs
        assert "latency_ms" in attrs
        assert "cost" in attrs
        assert attrs["bandwidth_mbps"] in [100, 1000, 10000]
        assert attrs["latency_ms"] > 0
        assert attrs["cost"] >= 1.0


def test_compute_topology_stats():
    cfg = TopologyConfig(name="test_stats", num_nodes=6, edge_probability=0.7, seed=123)
    G = build_random_topology(cfg)
    stats = compute_topology_stats(G)

    assert stats.num_nodes == 6
    assert stats.num_edges > 0
    assert stats.avg_degree > 0
    assert 0.0 <= stats.avg_clustering <= 1.0
    assert 0.0 <= stats.density <= 1.0


def test_topology_serialization_roundtrip():
    cfg = TopologyConfig(name="roundtrip", num_nodes=5, edge_probability=0.8, seed=99)
    G1 = build_random_topology(cfg)

    data = topology_to_dict(G1)
    assert "nodes" in data
    assert "links" in data
    assert len(data["nodes"]) == 5

    G2 = build_topology_from_dict(data)
    assert G2.number_of_nodes() == G1.number_of_nodes()
    assert G2.number_of_edges() == G1.number_of_edges()

