"""Integration tests for FastAPI REST API endpoints and evaluation aliases."""

import pytest
from httpx import ASGITransport, AsyncClient
from harness.api.server import app


@pytest.mark.asyncio
async def test_health_and_readiness_endpoints():
    """Verify /health and /ready endpoints return valid status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test /health
        h_response = await client.get("/health")
        assert h_response.status_code == 200
        h_data = h_response.json()
        assert h_data["status"] == "ok"
        assert "version" in h_data
        assert "configured_model" in h_data

        # Test /ready
        r_response = await client.get("/ready")
        assert r_response.status_code == 200
        r_data = r_response.json()
        assert r_data["status"] == "ready"
        assert r_data["ready"] is True


@pytest.mark.asyncio
async def test_task_api_lifecycle(mock_workspace):
    """Verify task submission, retrieval, cancellation, logs, and report endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create task
        payload = {
            "repo_path": mock_workspace,
            "issue_description": "Fix the calculator bug",
            "max_steps": 5,
        }
        create_res = await client.post("/api/v1/tasks", json=payload)
        assert create_res.status_code == 202
        task_data = create_res.json()
        task_id = task_data["task_id"]
        assert task_id.startswith("task_")

        # 2. Get task status
        get_res = await client.get(f"/api/v1/tasks/{task_id}")
        assert get_res.status_code == 200
        assert get_res.json()["task_id"] == task_id

        # 3. List tasks
        list_res = await client.get("/api/v1/tasks")
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1

        # 4. Get task logs
        logs_res = await client.get(f"/api/v1/tasks/{task_id}/logs")
        assert logs_res.status_code == 200
        assert "events" in logs_res.json()

        # 5. Get task report
        report_res = await client.get(f"/api/v1/tasks/{task_id}/report")
        assert report_res.status_code == 200
        report_data = report_res.json()
        assert "markdown_report" in report_data
        assert "json_report" in report_data

        # 6. Cancel task
        cancel_res = await client.post(f"/api/v1/tasks/{task_id}/cancel")
        assert cancel_res.status_code == 200


@pytest.mark.asyncio
async def test_evaluation_aliases_and_field_flexibility(mock_workspace):
    """Verify evaluation aliases (/eval, /tasks, /evaluate) and flexible payload keys."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. POST /eval with 'issue' and 'repo'
        res1 = await client.post("/eval", json={"issue": "Fix arithmetic bug", "repo": mock_workspace})
        assert res1.status_code == 202
        assert res1.json()["task_id"].startswith("task_")

        # 2. POST /tasks with 'task'
        res2 = await client.post("/tasks", json={"task": "Fix parser bug", "workspace": mock_workspace})
        assert res2.status_code == 202

        # 3. POST /evaluate with 'problem_statement'
        res3 = await client.post("/evaluate", json={"problem_statement": "Fix indexing bug", "repo_path": mock_workspace})
        assert res3.status_code == 202

        # 4. POST /api/v1/tasks with synchronous wait=true
        res_sync = await client.post(
            "/api/v1/tasks?wait=true",
            json={"issue": "Quick test task", "repo": mock_workspace, "max_steps": 1},
        )
        assert res_sync.status_code == 200
        assert res_sync.json()["current_step"] >= 0
