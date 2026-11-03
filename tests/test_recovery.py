"""Integration tests for Recovery Plans and End-to-End Advanced API Endpoints."""

import uuid
import pytest
import httpx
from httpx import ASGITransport
from backend.main import app


@pytest.mark.anyio
async def test_recovery_lifecycle_and_advanced_endpoints():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create a topology
        uid = uuid.uuid4().hex[:6]
        create_res = await ac.post("/api/v1/topologies/generate", json={
            "name": f"recovery_test_{uid}",
            "num_nodes": 7,
            "edge_probability": 0.5,
            "seed": 99,
        })
        assert create_res.status_code == 201, create_res.text
        topo_id = create_res.json()["id"]

        # 2. Test Cascade Simulation endpoint
        cascade_res = await ac.post("/api/v1/simulations/cascade", json={
            "topology_id": topo_id,
            "initial_failed_nodes": ["0"],
            "tolerance": 0.2,
            "max_steps": 10,
        })
        assert cascade_res.status_code == 200, cascade_res.text
        cascade_data = cascade_res.json()
        assert cascade_data["topology_id"] == topo_id
        assert "final_resilience_score" in cascade_data
        assert "steps" in cascade_data

        # 3. Test Monitoring Telemetry & Alerts endpoint
        telem_res = await ac.post(f"/api/v1/monitor/{topo_id}/telemetry", json={
            "degraded_links": ["0->1"],
        })
        assert telem_res.status_code == 200, telem_res.text
        telem_data = telem_res.json()
        assert telem_data["link_count"] > 0
        assert "telemetry" in telem_data
        assert "alerts" in telem_data

        alerts_res = await ac.get(f"/api/v1/monitor/{topo_id}/alerts")
        assert alerts_res.status_code == 200

        # 4. Generate Recovery Plan
        rec_gen = await ac.post("/api/v1/recovery/generate", json={
            "topology_id": topo_id,
            "source": "0",
            "target": "2",
            "max_risk": 8.0,
            "max_paths": 2,
        })
        assert rec_gen.status_code == 201, rec_gen.text
        plan = rec_gen.json()
        plan_id = plan["plan_id"]
        assert plan["status"] == "PENDING"
        assert len(plan["actions"]) > 0

        # 5. Get plan by ID
        get_plan = await ac.get(f"/api/v1/recovery/{plan_id}")
        assert get_plan.status_code == 200
        assert get_plan.json()["plan_id"] == plan_id

        # 6. List plans
        list_plans = await ac.get("/api/v1/recovery/")
        assert list_plans.status_code == 200
        assert any(p["plan_id"] == plan_id for p in list_plans.json())

        # 7. Approve and execute plan
        approve_res = await ac.post(f"/api/v1/recovery/{plan_id}/approve", json={
            "notes": "Approved by automated resilience policy",
        })
        assert approve_res.status_code == 200, approve_res.text
        exec_data = approve_res.json()
        assert exec_data["status"] == "EXECUTED"
        assert exec_data["executed_at"] is not None

