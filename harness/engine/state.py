"""Agent state models, step records, and task status enums."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Lifecycle states of an autonomous coding task."""

    QUEUED = "queued"
    RUNNING = "running"
    PENDING = "pending"
    EXPLORING = "exploring"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepRecord(BaseModel):
    """Detailed record of a single step in the agent execution loop."""

    step_number: int
    stage: TaskStatus
    thought: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_output: Optional[str] = None
    is_error: bool = False
    tokens_used: int = 0
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TaskState(BaseModel):
    """Complete in-memory state of an autonomous coding task."""

    task_id: str
    repo_path: str
    issue_description: str
    status: TaskStatus = TaskStatus.PENDING
    current_step: int = 0
    max_steps: int = 35
    max_tool_calls: int = 50
    tool_call_count: int = 0
    errors_count: int = 0
    retries_count: int = 0
    execution_plan: List[str] = Field(default_factory=list)
    model: str = "gpt-4o"
    steps: List[StepRecord] = Field(default_factory=list)
    files_modified: List[str] = Field(default_factory=list)
    final_summary: Optional[str] = None
    final_result: Optional[str] = None
    verification_status: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    start_time: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None
    completion_time: Optional[str] = None
    total_tokens_consumed: int = 0

    def mark_running(self) -> None:
        """Marks the task as running."""
        self.status = TaskStatus.RUNNING

    def add_step(self, step: StepRecord) -> None:
        """Appends an execution step and increments counters."""
        self.steps.append(step)
        self.current_step = len(self.steps)
        self.total_tokens_consumed += step.tokens_used
        if step.tool_name:
            self.tool_call_count += 1
        if step.is_error:
            self.errors_count += 1

    def mark_completed(
        self, summary: str, verification: str = "passed", files: Optional[List[str]] = None
    ) -> None:
        """Marks the task successfully completed."""
        self.status = TaskStatus.COMPLETED
        self.final_summary = summary
        self.final_result = summary
        self.verification_status = verification
        if files:
            self.files_modified = list(set(self.files_modified + files))
        now = datetime.now(timezone.utc).isoformat()
        self.completed_at = now
        self.completion_time = now

    def mark_failed(self, error: str) -> None:
        """Marks the task as failed."""
        self.status = TaskStatus.FAILED
        self.error_message = error
        self.final_result = f"Failed: {error}"
        now = datetime.now(timezone.utc).isoformat()
        self.completed_at = now
        self.completion_time = now

    def mark_cancelled(self) -> None:
        """Marks the task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.final_result = "Cancelled"
        now = datetime.now(timezone.utc).isoformat()
        self.completed_at = now
        self.completion_time = now
