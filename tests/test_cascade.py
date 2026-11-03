"""Unit tests for Motter-Lai cascading failure engine."""

import pytest
from backend.simulation.topology import TopologyConfig, build_random_topology
from backend.simulation.cascade import run_cascade_simulation, CascadeReport


def test_cascade_simulation_basic():
    cfg = TopologyConfig(name="cascade_test", num_nodes=12, edge_probability=0.4, seed=42)
    G = build_random_topology(cfg)

    # Initial failure of a high-load node
    report = run_cascade_simulation(G, initial_failed=["0"], tolerance=0.1, max_steps=10)

    assert isinstance(report, CascadeReport)
    assert report.total_steps >= 1
    assert "0" in report.initial_failed
    assert "0" in report.all_failed
    assert 0.0 <= report.final_resilience_score <= 1.0
    assert 0.0 <= report.final_connectivity_ratio <= 1.0
    assert report.cascade_amplification >= 1.0
    assert report.duration_ms > 0

    # Test serialization
    data = report.to_dict()
    assert "steps" in data
    assert "final_resilience_score" in data


def test_cascade_high_tolerance_stabilizes():
    cfg = TopologyConfig(name="cascade_resilient", num_nodes=10, edge_probability=0.5, seed=123)
    G = build_random_topology(cfg)

    # With very high tolerance (10x capacity), cascading should quickly stabilize
    report = run_cascade_simulation(G, initial_failed=["1"], tolerance=10.0, max_steps=5)

    assert len(report.all_failed) == 1  # Only initial node failed
    assert report.cascade_amplification == 1.0

