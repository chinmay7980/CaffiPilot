"""Unit and integration tests for Prompt 9: Telemetry, Metrics, Secret Redaction, and Task Reports."""

import json
import os
import shutil
import tempfile
import pytest

from harness.engine.state import StepRecord, TaskState, TaskStatus
from harness.telemetry.logger import TelemetryBus, redact_secrets
from harness.telemetry.metrics import TaskMetrics
from harness.telemetry.reporter import (
    generate_json_report,
    generate_markdown_report,
    save_task_reports,
)


def test_secret_redaction_filter():
    """Verify that API keys, tokens, and credentials are redacted from strings and payloads."""
    # 1. String redaction
    raw_str = "Connecting with key AI_API_KEY=sk-1234567890abcdef1234567890 and token ghp_abcdefghijklmnopqrstuvwxyz"
    clean_str = redact_secrets(raw_str)
    assert "sk-1234567890abcdef1234567890" not in clean_str
    assert "ghp_abcdefghijklmnopqrstuvwxyz" not in clean_str
    assert "[REDACTED" in clean_str

    # 2. Dictionary payload redaction
    raw_dict = {
        "task_id": "test_01",
        "api_key": "secret_key_val",
        "nested": {
            "password": "my_password_123",
            "normal_field": "public_data",
        },
    }
    clean_dict = redact_secrets(raw_dict)
    assert clean_dict["api_key"] == "[REDACTED]"
    assert clean_dict["nested"]["password"] == "[REDACTED]"
    assert clean_dict["nested"]["normal_field"] == "public_data"


def test_telemetry_event_recording_and_persistence():
    """Test emitting structured events, secret redaction, and jsonl file persistence."""
    tmp_reports = tempfile.mkdtemp(prefix="telemetry_test_")
    try:
        bus = TelemetryBus(persistence_dir=tmp_reports)
        task_id = "task_telem_01"

        # Emit events
        bus.emit(task_id=task_id, event_type="TASK_CREATED", message="Created task with key=secret_val_123")
        bus.emit(task_id=task_id, event_type="STEP_COMPLETED", step_number=1, data={"tool": "read_file"})

        events = bus.get_events(task_id)
        assert len(events) == 2
        assert "secret_val_123" not in events[0].message
        assert "[REDACTED" in events[0].message

        # Verify JSONL trace file persistence on disk
        trace_path = os.path.join(tmp_reports, f"{task_id}_telemetry.jsonl")
        assert os.path.exists(trace_path)
        with open(trace_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 2
        assert "TASK_CREATED" in lines[0]
        assert "secret_val_123" not in lines[0]
    finally:
        shutil.rmtree(tmp_reports, ignore_errors=True)


def test_task_metrics_accuracy():
    """Test metric extraction, duration, token sums, tool counts, test stats, and failure categorization."""
    state = TaskState(
        task_id="task_metrics_01",
        repo_path="/workspace/test",
        issue_description="Metric calculation test",
        status=TaskStatus.FAILED,
        error_message="Execution stopped: tool 'edit_file' called repeatedly with identical parameters (Infinite loop detected).",
        max_steps=10,
        start_time="2026-09-26T10:00:00+00:00",
        completion_time="2026-09-26T10:00:15+00:00",
        files_modified=["calculator.py"],
    )

    state.add_step(StepRecord(
        step_number=1,
        stage=TaskStatus.EXPLORING,
        tool_name="read_file",
        tool_args={"path": "calculator.py"},
        tokens_used=100,
    ))

    state.add_step(StepRecord(
        step_number=2,
        stage=TaskStatus.EXECUTING,
        tool_name="run_command",
        tool_args={"command": "pytest"},
        is_error=True,
        tokens_used=150,
    ))

    metrics = TaskMetrics.from_task_state(state)

    assert metrics.task_id == "task_metrics_01"
    assert metrics.task_duration_seconds == 15.0
    assert metrics.total_steps == 2
    assert metrics.total_tool_calls == 2
    assert metrics.total_tokens == 250
    assert metrics.errors_encountered == 1
    assert metrics.test_runs_count == 1
    assert metrics.test_failures_count == 1
    assert metrics.failure_category == "INFINITE_LOOP_DETECTED"
    assert metrics.files_modified_count == 1
    assert metrics.tool_usage_counts == {"read_file": 1, "run_command": 1}


def test_task_report_generation_and_disk_persistence():
    """Test generating Markdown and JSON reports and persisting report artifacts to disk."""
    tmp_dir = tempfile.mkdtemp(prefix="report_test_")
    try:
        state = TaskState(
            task_id="task_report_01",
            repo_path="/tmp/workspace",
            issue_description="Generate report test",
            status=TaskStatus.COMPLETED,
            final_summary="Task completed cleanly via pytest verification.",
            verification_status="passed",
            files_modified=["app.py"],
        )
        state.add_step(StepRecord(
            step_number=1,
            stage=TaskStatus.COMPLETED,
            tool_name="finish_task",
            tool_args={"summary": "Done"},
            tokens_used=80,
        ))

        paths = save_task_reports(state, git_diff="--- app.py\n+++ app.py\n@@ -1 +1 @@\n-old\n+new", reports_dir=tmp_dir)

        assert os.path.exists(paths["markdown_report_path"])
        assert os.path.exists(paths["json_report_path"])

        with open(paths["markdown_report_path"], "r", encoding="utf-8") as f:
            md_text = f.read()
        assert "# Autonomous AI Coding Execution Report" in md_text
        assert "task_report_01" in md_text
        assert "Task completed cleanly" in md_text

        with open(paths["json_report_path"], "r", encoding="utf-8") as f:
            json_data = json.load(f)
        assert json_data["task_id"] == "task_report_01"
        assert json_data["status"] == "completed"
        assert json_data["metrics"]["total_steps"] == 1
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
