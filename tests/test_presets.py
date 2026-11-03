"""Unit tests for real-world topology presets (Abilene, Fat-Tree, Ring)."""

import networkx as nx
import pytest
from backend.simulation.topology import (
    build_abilene_topology,
    build_fat_tree_topology,
    build_ring_topology,
    compute_topology_stats,
)


def test_abilene_topology():
    G = build_abilene_topology()
    assert G.number_of_nodes() == 12
    assert G.number_of_edges() == 18
    assert nx.is_connected(G)
    stats = compute_topology_stats(G)
    assert stats.is_connected is True
    assert stats.diameter is not None
    assert stats.avg_shortest_path is not None


def test_fat_tree_topology():
    # k=4 pod fat-tree
    G = build_fat_tree_topology(k=4)
    # k=4 fat-tree: 4 core switches, 8 agg switches, 8 edge switches, 8 hosts = 28 nodes
    assert G.number_of_nodes() > 10
    assert G.number_of_edges() > 10
    assert nx.is_connected(G)
    # Verify switch types
    types = {G.nodes[n].get("node_type") for n in G.nodes}
    assert "switch" in types
    assert "host" in types


def test_ring_topology():
    G = build_ring_topology(n=8, seed=42)
    assert G.number_of_nodes() == 8
    assert G.number_of_edges() >= 8  # Ring + chords
    assert nx.is_connected(G)

