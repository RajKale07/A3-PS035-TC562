"""Unit tests for Critical-Service Prioritization in the OR-Tools optimizer."""

import networkx as nx
import pytest
from backend.optimizer.resilience import (
    OptimizationConfig,
    find_resilient_paths,
)


def _build_test_network():
    G = nx.Graph()
    # Path 1: 0 -> 1 -> 3 (High bandwidth 10G, low latency 2ms, low risk 0.2, high cost 10)
    # Path 2: 0 -> 2 -> 3 (Low bandwidth 100M, high latency 20ms, higher risk 1.0, low cost 1)
    G.add_node("0", risk_weight=0.1)
    G.add_node("1", risk_weight=0.1)
    G.add_node("2", risk_weight=1.5)
    G.add_node("3", risk_weight=0.1)

    G.add_edge("0", "1", bandwidth_mbps=10000, latency_ms=2.0, loss_rate=0.001, cost=10.0)
    G.add_edge("1", "3", bandwidth_mbps=10000, latency_ms=2.0, loss_rate=0.001, cost=10.0)

    G.add_edge("0", "2", bandwidth_mbps=100, latency_ms=20.0, loss_rate=0.03, cost=1.0)
    G.add_edge("2", "3", bandwidth_mbps=100, latency_ms=20.0, loss_rate=0.03, cost=1.0)
    return G


def test_critical_service_prioritizes_resilience_and_bandwidth():
    G = _build_test_network()

    # 1. Best effort: should choose the cheaper path (via node 2)
    cfg_be = OptimizationConfig(
        source="0",
        target="3",
        max_risk=5.0,
        max_paths=1,
        service_tier="BEST_EFFORT",
    )
    res_be = find_resilient_paths(G, cfg_be)
    assert res_be.feasible is True
    assert res_be.paths[0].nodes == ["0", "2", "3"]

    # 2. Critical tier: should strictly filter out high-loss/high-risk path and choose path via node 1
    cfg_crit = OptimizationConfig(
        source="0",
        target="3",
        max_risk=5.0,
        max_paths=1,
        service_tier="CRITICAL",
        min_bandwidth_mbps=1000.0,  # 1 Gbps min
    )
    res_crit = find_resilient_paths(G, cfg_crit)
    assert res_crit.feasible is True
    assert res_crit.paths[0].nodes == ["0", "1", "3"]
    assert res_crit.paths[0].min_link_bandwidth >= 1000.0

