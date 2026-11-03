"""Unit tests for failure simulation scenarios."""

import pytest
from backend.simulation.topology import TopologyConfig, build_random_topology
from backend.simulation.failure import (
    FailureScenario,
    run_failure_simulation,
    random_node_failure_scenario,
    targeted_hub_failure_scenario,
)


def test_random_node_failure():
    cfg = TopologyConfig(name="sim_test", num_nodes=10, edge_probability=0.6, seed=42)
    G = build_random_topology(cfg)

    scenario = random_node_failure_scenario(G, failure_fraction=0.3, seed=1)
    report = run_failure_simulation(G, scenario)

    assert report.scenario.startswith("random_30pct_failure")
    assert len(report.failed_nodes) == 3
    assert report.surviving_nodes == 7
    assert 0.0 <= report.resilience_score <= 1.0
    assert 0.0 <= report.connectivity_ratio <= 1.0
    # Ensure original graph G was not mutated
    assert G.number_of_nodes() == 10


def test_targeted_hub_failure():
    cfg = TopologyConfig(name="hub_test", num_nodes=10, edge_probability=0.5, seed=7)
    G = build_random_topology(cfg)

    scenario = targeted_hub_failure_scenario(G, top_k=2)
    report = run_failure_simulation(G, scenario)

    assert len(report.failed_nodes) == 2
    assert report.surviving_nodes == 8
    assert report.components >= 1

