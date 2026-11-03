"""Unit tests for OR-Tools CP-SAT resilient path optimization."""

import pytest
from backend.simulation.topology import TopologyConfig, build_random_topology
from backend.optimizer.resilience import OptimizationConfig, find_resilient_paths


def test_ortools_find_resilient_paths_success():
    cfg = TopologyConfig(name="opt_test", num_nodes=8, edge_probability=0.7, seed=42)
    G = build_random_topology(cfg)

    nodes = list(G.nodes)
    src, tgt = nodes[0], nodes[-1]

    opt_cfg = OptimizationConfig(
        source=src,
        target=tgt,
        max_risk=6.0,
        max_paths=2,
        time_limit_sec=5.0,
    )

    result = find_resilient_paths(G, opt_cfg)

    assert result.feasible is True
    assert result.solver_status in ["OPTIMAL", "FEASIBLE"]
    assert len(result.paths) > 0
    assert len(result.paths) <= 2

    for path in result.paths:
        assert path.nodes[0] == str(src)
        assert path.nodes[-1] == str(tgt)
        assert path.total_risk <= 6.0
        assert path.total_cost > 0
        assert path.hop_count == len(path.nodes) - 1


def test_ortools_nonexistent_node():
    cfg = TopologyConfig(name="opt_test_none", num_nodes=5, edge_probability=0.5, seed=1)
    G = build_random_topology(cfg)

    opt_cfg = OptimizationConfig(
        source="nonexistent_src",
        target="nonexistent_tgt",
        max_risk=5.0,
    )

    result = find_resilient_paths(G, opt_cfg)
    assert result.feasible is False
    assert len(result.paths) == 0

