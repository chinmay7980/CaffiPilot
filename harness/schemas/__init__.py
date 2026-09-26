"""Central Pydantic schemas for the AI Coding Harness.

Provides typed data models for:
- Task input & configuration
- Agent state & execution step tracking
- Tool calls & tool execution results
- Execution events & telemetry
- Test execution results & deltas
- Final execution reports
"""

from datetime import datetime, timezone
from enum import Enum
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


# ==============================================================================
# 1. Task Input & Submission Schemas
# ==============================================================================

class TaskInput(BaseModel):
    """Payload for submitting a new autonomous coding task or GitHub issue."""

    repo_path: Optional[str] = Field(
        default=None,
        description="Path to the repository workspace (relative or absolute)",
    )
    issue_description: Optional[str] = Field(
        default=None,
        description="Coding task, issue description, or prompt instructions",
    )
    # Common alternative field aliases used by evaluation harnesses
    issue: Optional[str] = Field(default=None, description="Alias for issue_description")
    task: Optional[str] = Field(default=None, description="Alias for issue_description")
    problem_statement: Optional[str] = Field(default=None, description="Alias for issue_description")
    prompt: Optional[str] = Field(default=None, description="Alias for issue_description")
    github_issue: Optional[str] = Field(default=None, description="Alias for issue_description")
    repo: Optional[str] = Field(default=None, description="Alias for repo_path")
    workspace: Optional[str] = Field(default=None, description="Alias for repo_path")

    model: Optional[str] = Field(
        default=None,
        description="Optional model override (defaults to AI_MODEL env var)",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Optional API key override (defaults to AI_API_KEY env var)",
    )
    base_url: Optional[str] = Field(
        default=None,
        description="Optional base URL override (defaults to AI_BASE_URL env var)",
    )
    max_steps: Optional[int] = Field(
        default=None,
        description="Optional maximum steps override (defaults to HARNESS_MAX_STEPS)",
    )
    auto_verify: bool = Field(
        default=True,
        description="Whether to run automated test verification at the end",
    )

    @model_validator(mode="after")
    def resolve_aliases(self) -> "TaskInput":
        resolved_desc = (
            self.issue_description
            or self.issue
            or self.task
            or self.problem_statement
            or self.prompt
            or self.github_issue
        )
        if not resolved_desc or not str(resolved_desc).strip():
            raise ValueError(
                "Must provide task or issue description via 'issue_description', 'issue', 'task', or 'problem_statement'."
            )
        self.issue_description = str(resolved_desc).strip()

        resolved_repo = self.repo_path or self.repo or self.workspace or os.getcwd()
        self.repo_path = os.path.abspath(resolved_repo)
        return self


# Alias for API compatibility
CreateTaskRequest = TaskInput


# ==============================================================================
# 2. Agent State & Step Records Schemas
# ==============================================================================

class TaskStatus(str, Enum):
    """Lifecycle states of an autonomous coding task."""

    PENDING = "PENDING"
    EXPLORING = "EXPLORING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StepRecord(BaseModel):
    """Detailed record of a single step in the agent execution loop."""

    step_number: int = Field(description="1-indexed sequence number of the step")
    stage: TaskStatus = Field(description="Logical state machine stage during step execution")
    thought: Optional[str] = Field(default=None, description="LLM reasoning or explanation")
    tool_name: Optional[str] = Field(default=None, description="Name of invoked tool")
    tool_args: Optional[Dict[str, Any]] = Field(default=None, description="Arguments passed to tool")
    tool_output: Optional[str] = Field(default=None, description="Output returned by tool execution")
    is_error: bool = Field(default=False, description="True if tool execution failed")
    tokens_used: int = Field(default=0, description="Tokens consumed during this step")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of step completion",
    )


class AgentState(BaseModel):
    """Complete in-memory state of an autonomous coding task."""

    task_id: str = Field(description="Unique task identifier")
    repo_path: str = Field(description="Filesystem path to target workspace")
    issue_description: str = Field(description="Task specification or problem prompt")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current lifecycle status")
    current_step: int = Field(default=0, description="Number of completed steps")
    max_steps: int = Field(default=35, description="Upper bound on autonomous steps")
    model: str = Field(default="gpt-4o", description="LLM model identifier used for this task")
    steps: List[StepRecord] = Field(default_factory=list, description="Ordered step history")
    files_modified: List[str] = Field(default_factory=list, description="Relative paths of modified files")
    final_summary: Optional[str] = Field(default=None, description="Executive conclusion summary")
    verification_status: Optional[str] = Field(default=None, description="Verification outcome: passed, failed, unverified")
    error_message: Optional[str] = Field(default=None, description="Fatal error message if failed")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Task creation timestamp",
    )
    completed_at: Optional[str] = Field(default=None, description="Task completion timestamp")
    total_tokens_consumed: int = Field(default=0, description="Cumulative tokens used across all steps")


# ==============================================================================
# 3. Tool Calls & Tool Results Schemas
# ==============================================================================

class ToolCallRequest(BaseModel):
    """Model-generated request to invoke a workspace tool."""

    id: str = Field(description="Unique tool call identifier")
    name: str = Field(description="Name of the tool to invoke")
    arguments: Dict[str, Any] = Field(
        default_factory=dict, description="Parsed JSON arguments for the tool"
    )


# Alias
ToolCallDefinition = ToolCallRequest


class ToolResult(BaseModel):
    """Standardized result returned by any tool execution."""

    success: bool = Field(description="True if tool executed without fatal errors")
    output: str = Field(default="", description="Textual output of tool execution")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    data: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional structured metadata"
    )

    def to_message_content(self) -> str:
        """Formats the result as clean string content for the LLM context."""
        if self.success:
            return self.output if self.output else "Tool executed successfully (empty output)."
        return f"Error executing tool: {self.error or self.output}"


# ==============================================================================
# 4. Execution Events & Telemetry Schemas
# ==============================================================================

class ExecutionEvent(BaseModel):
    """Structured telemetry event emitted during task lifecycle."""

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Event UTC timestamp",
    )
    task_id: str = Field(description="Associated task identifier")
    event_type: str = Field(
        description="Event category: TASK_STARTED, STEP_COMPLETED, TOOL_RESULT, TASK_COMPLETED, etc."
    )
    stage: str = Field(default="UNKNOWN", description="Agent state machine stage")
    step_number: Optional[int] = Field(default=None, description="Active step number")
    data: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary event payload")
    message: str = Field(default="", description="Human-readable event summary")


# Alias
TelemetryEvent = ExecutionEvent


# ==============================================================================
# 5. Test Execution Results Schemas
# ==============================================================================

class TestResult(BaseModel):
    """Structured outcome of an automated test or verification run."""

    __test__ = False  # Instruct pytest not to treat this model as a test case

    passed: bool = Field(description="True if all tests passed without failure")
    exit_code: int = Field(default=0, description="Process return code from test runner")
    total_tests: int = Field(default=0, description="Total tests discovered and run")
    passed_tests: int = Field(default=0, description="Count of passed tests")
    failed_tests: int = Field(default=0, description="Count of failed tests")
    skipped_tests: int = Field(default=0, description="Count of skipped/ignored tests")
    summary: str = Field(default="", description="High-level test summary message")
    raw_output: str = Field(default="", description="Raw stdout/stderr test output")
    command_used: str = Field(default="", description="Test command that was executed")


# Alias
VerificationResult = TestResult


# ==============================================================================
# 6. Final Execution Report Schemas
# ==============================================================================

class ExecutionReport(BaseModel):
    """Complete evaluation report for a finished task."""

    task_id: str = Field(description="Task identifier")
    status: str = Field(description="Final lifecycle status: COMPLETED, FAILED, CANCELLED")
    markdown_report: str = Field(description="Human-readable GitHub-flavored markdown report")
    json_report: Dict[str, Any] = Field(description="Machine-readable structured evaluation payload")


# Alias
TaskReportResponse = ExecutionReport
