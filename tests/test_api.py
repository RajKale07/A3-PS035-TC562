"""Integration tests for NEXUS FastAPI endpoints."""

import uuid
import pytest
import httpx
from httpx import ASGITransport
from backend.main import app


@pytest.mark.anyio
async def test_health_check():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_root():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "NEXUS"
    assert data["status"] == "running"


@pytest.mark.anyio
async def test_topology_lifecycle_and_analysis():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Generate topology
        test_id = uuid.uuid4().hex[:8]
        gen_payload = {
            "name": f"test_api_lifecycle_{test_id}",
            "num_nodes": 6,
            "edge_probability": 0.6,
            "seed": 42,
        }
        create_res = await ac.post("/api/v1/topologies/generate", json=gen_payload)
        assert create_res.status_code == 201, create_res.text
        topo = create_res.json()
        topo_id = topo["id"]
        assert topo["name"] == gen_payload["name"]
        assert topo["stats"]["num_nodes"] == 6

        # 2. Get topology list
        list_res = await ac.get("/api/v1/topologies/")
        assert list_res.status_code == 200
        all_topos = list_res.json()
        assert any(t["id"] == topo_id for t in all_topos)

        # 3. Run failure simulation
        sim_payload = {
            "topology_id": topo_id,
            "scenario_type": "random",
            "failure_fraction": 0.3,
        }
        sim_res = await ac.post("/api/v1/simulations/run", json=sim_payload)
        assert sim_res.status_code == 200, sim_res.text
        sim_data = sim_res.json()
        assert "resilience_score" in sim_data
        assert sim_data["topology_name"] == gen_payload["name"]

        # 4. Run optimization
        opt_payload = {
            "topology_id": topo_id,
            "source": "0",
            "target": "5",
            "max_risk": 5.0,
            "max_paths": 2,
        }
        opt_res = await ac.post("/api/v1/optimizer/paths", json=opt_payload)
        assert opt_res.status_code == 200, opt_res.text
        opt_data = opt_res.json()
        assert "feasible" in opt_data
        assert "paths" in opt_data
