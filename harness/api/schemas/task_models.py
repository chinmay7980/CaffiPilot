"""FastAPI Pydantic request and response schemas for task management."""

import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class CreateTaskRequest(BaseModel):
    """Payload for submitting a new autonomous coding task or GitHub issue.

    Supports multiple common field aliases (issue, task, problem_statement, prompt)
    and defaults repo_path to the current workspace if not explicitly specified.
    """

    repo_path: Optional[str] = Field(
        default=None,
        description="Path to the repository workspace (defaults to current directory if omitted)",
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
    git_url: Optional[str] = Field(default=None, description="Optional Git repository URL to clone")
    branch: Optional[str] = Field(default=None, description="Optional Git branch name to checkout")
    model: Optional[str] = Field(
        default=None,
        description="Optional model override (defaults to AI_MODEL env var)",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Optional API key override (defaults to AI_API_KEY env var)",
    )
    github_token: Optional[str] = Field(
        default=None,
        description="Optional GitHub Personal Access Token for git cloning & PR creation",
    )
    token: Optional[str] = Field(
        default=None,
        description="Alias for github_token",
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
    def resolve_aliases(self) -> "CreateTaskRequest":
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
        if not self.model or not str(self.model).strip():
            from harness.config import settings
            self.model = settings.ai_model
        return self


class TaskResponse(BaseModel):
    """Response model representing current task state."""

    task_id: str
    issue_description: Optional[str] = None
    status: str
    repo_path: str
    current_step: int
    max_steps: int
    tool_call_count: int = 0
    max_tool_calls: int = 50
    errors_count: int = 0
    retries_count: int = 0
    execution_plan: List[str] = Field(default_factory=list)
    model: str
    files_modified: List[str] = Field(default_factory=list)
    git_diff: Optional[str] = None
    final_summary: Optional[str] = None
    final_result: Optional[str] = None
    verification_status: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    start_time: Optional[str] = None
    completed_at: Optional[str] = None
    completion_time: Optional[str] = None
    total_tokens_consumed: int = 0


class TaskReportResponse(BaseModel):
    """Detailed evaluation report response."""

    task_id: str
    status: str
    markdown_report: str
    json_report: Dict[str, Any]
