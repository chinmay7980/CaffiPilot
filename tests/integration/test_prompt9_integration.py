"""Integration tests for Prompt 9: Telemetry, Metrics, Evaluation Workflow, and Disk Persistence."""

import json
import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient

from harness.api.server import app
from harness.engine.agent import AgentRunner
from harness.engine.state import StepRecord, TaskState, TaskStatus
from harness.llm.base import BaseLLMClient, LLMResponse, ToolCallDefinition
from harness.telemetry.logger import telemetry_bus
from harness.telemetry.metrics import TaskMetrics
from harness.telemetry.reporter import generate_json_report, generate_markdown_report, save_task_reports

client = TestClient(app)


class MockEvalLLM(BaseLLMClient):
    """Mock LLM for deterministic evaluation workflow test."""

    def __init__(self):
        self.step = 0
        self.model = "mock-eval-model"

    async def generate(self, messages, tools=None, temperature=0.0):
        self.step += 1
        if self.step == 1:
            return LLMResponse(
                content="Inspecting workspace first",
                tool_calls=[ToolCallDefinition(id="c1", name="read_file", arguments={"path": "calculator.py"})]
            )
        elif self.step == 2:
            return LLMResponse(
                content="Running tests via run_command",
                tool_calls=[ToolCallDefinition(id="c2", name="run_command", arguments={"command": "python -c \"print('test pass')\""})]
            )
        else:
            return LLMResponse(
                content="Finishing evaluation task",
                tool_calls=[ToolCallDefinition(
                    id="c3",
                    name="finish_task",
                    arguments={"summary": "Evaluation task completed successfully.", "verification_status": "passed"}
                )]
            )


@pytest.mark.asyncio
async def test_deterministic_telemetry_and_metrics_accuracy(mock_workspace):
    """Test telemetry event association, secret redaction, and accurate metrics calculation."""
    task_id = "task_eval_metrics_01"
    telemetry_bus.clear(task_id)

    # 1. Emit telemetry events
    telemetry_bus.emit(task_id=task_id, event_type="TASK_CREATED", message="Created task with AI_API_KEY=sk-testsecretkey999")
    telemetry_bus.emit(task_id=task_id, event_type="STEP_STARTED", step_number=1, data={"api_key": "secret_key_abc"})

    events = telemetry_bus.get_events(task_id)
    assert len(events) == 2
    assert events[0].task_id == task_id
    assert "sk-testsecretkey999" not in events[0].message
    assert "[REDACTED" in events[0].message
    assert events[1].data["api_key"] == "[REDACTED]"

    # 2. Run agent with deterministic mock LLM
    runner = AgentRunner(
        task_id=task_id,
        repo_path=mock_workspace,
        issue_description="Run deterministic metrics test",
        llm_client=MockEvalLLM(),
        max_steps=5,
    )

    state = await runner.run()

    # 3. Verify metrics calculation
    metrics = TaskMetrics.from_task_state(state)
    assert metrics.task_id == task_id
    assert metrics.total_steps == 3
    assert metrics.total_tool_calls == 3
    assert metrics.errors_encountered == 0
    assert metrics.test_runs_count == 1
    assert metrics.test_passes_count == 1
    assert metrics.test_failures_count == 0
    assert metrics.failure_category is None
    assert metrics.final_status == "completed"
    assert metrics.tool_usage_counts == {"read_file": 1, "run_command": 1, "finish_task": 1}


@pytest.mark.asyncio
async def test_completed_and_failed_task_report_generation(mock_workspace):
    """Test report generation and report file persistence for completed and failed tasks."""
    tmp_reports = tempfile.mkdtemp(prefix="eval_reports_")
    try:
        # Completed task state
        state_comp = TaskState(
            task_id="task_comp_01",
            repo_path=mock_workspace,
            issue_description="Completed task issue",
            status=TaskStatus.COMPLETED,
            final_summary="All tests passed.",
            verification_status="passed",
            files_modified=["calc.py"],
        )
        state_comp.add_step(StepRecord(step_number=1, stage=TaskStatus.COMPLETED, tool_name="finish_task", tokens_used=50))

        res_comp = save_task_reports(state_comp, git_diff="--- diff", reports_dir=tmp_reports)
        assert os.path.exists(res_comp["markdown_report_path"])
        assert os.path.exists(res_comp["json_report_path"])

        with open(res_comp["json_report_path"], "r") as f:
            data_comp = json.load(f)
        assert data_comp["status"] == "completed"
        assert data_comp["metrics"]["total_steps"] == 1

        # Failed task state
        state_fail = TaskState(
            task_id="task_fail_01",
            repo_path=mock_workspace,
            issue_description="Failed task issue",
            status=TaskStatus.FAILED,
            error_message="Execution stopped: reached maximum step limit (5).",
            max_steps=5,
        )
        state_fail.add_step(StepRecord(step_number=1, stage=TaskStatus.EXPLORING, tool_name="read_file", is_error=True))

        res_fail = save_task_reports(state_fail, git_diff="", reports_dir=tmp_reports)
        assert os.path.exists(res_fail["markdown_report_path"])
        assert os.path.exists(res_fail["json_report_path"])

        with open(res_fail["json_report_path"], "r") as f:
            data_fail = json.load(f)
        assert data_fail["status"] == "failed"
        assert data_fail["metrics"]["failure_category"] == "STEP_LIMIT_EXCEEDED"

    finally:
        shutil.rmtree(tmp_reports, ignore_errors=True)


def test_api_evaluation_workflow_and_persistence():
    """Test submitting task via API evaluation interface and retrieving persisted evaluation reports."""
    tmp_workspace = tempfile.mkdtemp(prefix="api_eval_ws_")
    try:
        # Submit task synchronously via API endpoint
        res = client.post("/api/v1/tasks?wait=true", json={
            "repo_path": tmp_workspace,
            "issue_description": "API evaluation workflow test",
            "max_steps": 2,
        })
        assert res.status_code == 200
        task_data = res.json()
        task_id = task_data["task_id"]

        # Fetch status endpoint
        res_status = client.get(f"/api/v1/tasks/{task_id}")
        assert res_status.status_code == 200
        assert res_status.json()["task_id"] == task_id

        # Fetch report endpoint
        res_report = client.get(f"/api/v1/tasks/{task_id}/report")
        assert res_report.status_code == 200
        report_data = res_report.json()
        assert report_data["task_id"] == task_id
        assert "markdown_report" in report_data
        assert "json_report" in report_data

        # Verify persisted files on disk
        reports_dir = ".harness_reports"
        assert os.path.exists(os.path.join(reports_dir, f"{task_id}_report.json"))
        assert os.path.exists(os.path.join(reports_dir, f"{task_id}_report.md"))

    finally:
        shutil.rmtree(tmp_workspace, ignore_errors=True)
