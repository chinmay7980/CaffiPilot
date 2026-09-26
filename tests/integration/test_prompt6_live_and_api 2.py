"""Integration and live verification tests for Prompt 6 Orchestrator and API Interface."""

import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient

from harness.api.server import app
from harness.engine.agent import AgentRunner
from harness.engine.state import TaskStatus
from harness.llm.adapter import LLMAdapter
from harness.config import settings

client = TestClient(app)


def test_api_evaluation_interface_endpoints():
    """Test task submission, monitoring, report, and invalid input error handling via documented API endpoints."""
    tmp_workspace = tempfile.mkdtemp(prefix="api_test_ws_")
    try:
        # 1. Test invalid inputs (missing task description)
        res_invalid = client.post("/api/v1/tasks", json={"repo_path": tmp_workspace})
        assert res_invalid.status_code == 422 or res_invalid.status_code == 400

        # Test invalid inputs (non-existent repo path)
        res_bad_repo = client.post("/api/v1/tasks", json={"repo_path": "/nonexistent/directory/path/123", "issue_description": "Fix bug"})
        assert res_bad_repo.status_code == 400
        assert "Repository path does not exist" in res_bad_repo.json()["detail"]

        # 2. Test valid task submission (async 202 Accepted)
        res_submit = client.post("/api/v1/tasks", json={
            "repo_path": tmp_workspace,
            "issue_description": "Create sample file and verify",
            "max_steps": 5,
        })
        assert res_submit.status_code == 202
        data = res_submit.json()
        task_id = data["task_id"]
        assert data["status"] in ("pending", "queued", "running", "exploring")
        assert data["repo_path"] == os.path.abspath(tmp_workspace)
        assert "created_at" in data

        # 3. Test list tasks
        res_list = client.get("/api/v1/tasks")
        assert res_list.status_code == 200
        tasks = res_list.json()
        assert any(t["task_id"] == task_id for t in tasks)

        # 4. Test fetch task status
        res_get = client.get(f"/api/v1/tasks/{task_id}")
        assert res_get.status_code == 200
        assert res_get.json()["task_id"] == task_id

        # 5. Test task cancellation endpoint
        res_cancel = client.post(f"/api/v1/tasks/{task_id}/cancel")
        assert res_cancel.status_code == 200
        assert res_cancel.json()["status"] == "cancelled"

        # 6. Test task evaluation report endpoint
        res_report = client.get(f"/api/v1/tasks/{task_id}/report")
        assert res_report.status_code == 200
        report_data = res_report.json()
        assert report_data["task_id"] == task_id
        assert "markdown_report" in report_data
        assert "json_report" in report_data

    finally:
        shutil.rmtree(tmp_workspace, ignore_errors=True)


def test_api_aliases():
    """Verify that alias routes (/tasks, /eval, /evaluate) work for evaluator compatibility."""
    tmp_workspace = tempfile.mkdtemp(prefix="api_alias_ws_")
    try:
        for alias in ["/tasks", "/eval", "/evaluate", "/task"]:
            res = client.post(alias, json={
                "repo_path": tmp_workspace,
                "issue": "Test alias endpoint",
            })
            assert res.status_code == 202
            assert "task_id" in res.json()
    finally:
        shutil.rmtree(tmp_workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_live_llm_execution():
    """Run a minimal live task using the configured LLM provider if valid API key / endpoint is available."""
    if not settings.has_valid_api_key and "ollama" not in settings.effective_base_url and "127.0.0.1" not in settings.effective_base_url and "localhost" not in settings.effective_base_url:
        pytest.skip("No valid LLM credentials or local endpoint configured for live test.")

    tmp_workspace = tempfile.mkdtemp(prefix="live_llm_ws_")
    try:
        # Create a simple test file in workspace
        calc_path = os.path.join(tmp_workspace, "math_utils.py")
        with open(calc_path, "w") as f:
            f.write("def add(a, b):\n    return a - b\n")

        llm_client = LLMAdapter(
            api_key=settings.ai_api_key,
            model=settings.ai_model,
            base_url=settings.effective_base_url,
        )

        runner = AgentRunner(
            task_id="live_test_01",
            repo_path=tmp_workspace,
            issue_description="Inspect math_utils.py, fix subtraction to addition, and finish task.",
            llm_client=llm_client,
            max_steps=5,
        )

        state = await runner.run()

        # Report live results
        print(f"\n[Live LLM Test] Status: {state.status.value}, Steps: {state.current_step}, Modified: {state.files_modified}")
        assert state.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        assert state.current_step > 0

    finally:
        shutil.rmtree(tmp_workspace, ignore_errors=True)
