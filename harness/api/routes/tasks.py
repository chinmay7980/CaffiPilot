"""Task lifecycle and evaluation endpoints: creation, monitoring, cancellation, and reporting."""

import asyncio
import os
import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Response
from harness.api.schemas.task_models import (
    CreateTaskRequest,
    TaskReportResponse,
    TaskResponse,
)
from harness.engine.agent import AgentRunner
from harness.llm.adapter import LLMAdapter
from harness.telemetry.logger import telemetry_bus
from harness.telemetry.metrics import TaskMetrics
from harness.telemetry.reporter import generate_json_report, generate_markdown_report, save_task_reports
from harness.tools.git_tools import GitDiffTool
from harness.verification.runner import VerificationRunner

router = APIRouter(tags=["Tasks & Evaluation"])

# In-memory storage of running and finished agent runners
active_runners: Dict[str, AgentRunner] = {}


def _to_response(runner: AgentRunner) -> TaskResponse:
    state = runner.state
    status_val = state.status.value if hasattr(state.status, "value") else str(state.status)
    return TaskResponse(
        task_id=state.task_id,
        issue_description=state.issue_description,
        status=status_val,
        repo_path=state.repo_path,
        current_step=state.current_step,
        max_steps=state.max_steps,
        tool_call_count=state.tool_call_count,
        max_tool_calls=state.max_tool_calls,
        errors_count=state.errors_count,
        retries_count=state.retries_count,
        execution_plan=state.execution_plan,
        model=state.model,
        files_modified=state.files_modified,
        final_summary=state.final_summary,
        final_result=state.final_result,
        verification_status=state.verification_status,
        error_message=state.error_message,
        created_at=state.created_at,
        start_time=state.start_time,
        completed_at=state.completed_at,
        completion_time=state.completion_time,
        total_tokens_consumed=state.total_tokens_consumed,
    )


async def _execute_task_background(runner: AgentRunner, auto_verify: bool = True) -> None:
    task_id = runner.state.task_id
    telemetry_bus.emit(
        task_id=task_id,
        event_type="TASK_STARTED",
        message=f"Starting autonomous task execution on {runner.state.repo_path}",
    )
    
    def on_step(step_rec):
        telemetry_bus.emit(
            task_id=task_id,
            event_type="STEP_COMPLETED",
            stage=step_rec.stage.value if hasattr(step_rec.stage, "value") else str(step_rec.stage),
            step_number=step_rec.step_number,
            data={
                "tool": step_rec.tool_name,
                "is_error": step_rec.is_error,
                "tokens": step_rec.tokens_used,
            },
            message=step_rec.thought or f"Executed tool: {step_rec.tool_name}",
        )

    runner.on_step_callback = on_step

    try:
        final_state = await runner.run()
        
        # Run independent verification if requested and if not already verified
        if auto_verify and final_state.status.value == "COMPLETED" and not final_state.verification_status:
            verifier = VerificationRunner(runner.state.repo_path)
            verif_res = await verifier.run()
            final_state.verification_status = "passed" if verif_res.passed else "failed"

        # Obtain git diff & save evaluation reports to disk
        diff_tool = GitDiffTool(final_state.repo_path)
        diff_res = await diff_tool.execute()
        git_diff = diff_res.output if diff_res.success else ""
        save_task_reports(final_state, git_diff=git_diff)

        telemetry_bus.emit(
            task_id=task_id,
            event_type="TASK_COMPLETED" if final_state.status.value == "COMPLETED" else "TASK_FAILED",
            message=final_state.final_summary or final_state.error_message or "Task finished.",
        )
    except Exception as e:
        runner.state.mark_failed(f"Unexpected execution error: {str(e)}")
        save_task_reports(runner.state)
        telemetry_bus.emit(
            task_id=task_id,
            event_type="TASK_FAILED",
            message=str(e),
        )


# ==============================================================================
# Task Creation & Evaluation Ingestion Endpoints (Multiple URL Aliases)
# ==============================================================================

@router.post("/api/v1/tasks", response_model=TaskResponse, status_code=202)
@router.post("/api/v1/task", response_model=TaskResponse, status_code=202)
@router.post("/api/v1/eval", response_model=TaskResponse, status_code=202)
@router.post("/api/v1/evaluate", response_model=TaskResponse, status_code=202)
@router.post("/tasks", response_model=TaskResponse, status_code=202)
@router.post("/task", response_model=TaskResponse, status_code=202)
@router.post("/eval", response_model=TaskResponse, status_code=202)
@router.post("/evaluate", response_model=TaskResponse, status_code=202)
async def create_task(
    req: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    wait: bool = Query(
        default=False,
        description="If True, blocks until task completion and returns the final result directly.",
    ),
):
    """Submits a new autonomous coding task or GitHub issue for execution.

    Supports both asynchronous execution (default, status 202) and synchronous evaluation mode (wait=true, status 200).
    """
    repo_input = (req.git_url or req.repo_path or "").strip()
    if repo_input.startswith("http://") or repo_input.startswith("https://") or repo_input.startswith("git@"):
        repo_name = repo_input.split("/")[-1].replace(".git", "") or "cloned_repo"
        target_dir = os.path.abspath(os.path.join(os.getcwd(), "cloned_repos", repo_name))
        os.makedirs(os.path.dirname(target_dir), exist_ok=True)
        
        # Inject token into HTTPS git URL if token is available
        auth_git_url = repo_input
        auth_token = req.api_key if (req.api_key and req.api_key.startswith("ghp_")) else os.getenv("GITHUB_TOKEN")
        if auth_token and repo_input.startswith("https://github.com/"):
            auth_git_url = repo_input.replace("https://github.com/", f"https://x-access-token:{auth_token}@github.com/")

        if not os.path.exists(target_dir):
            clone_cmd = ["git", "clone"]
            if req.branch and req.branch.strip():
                clone_cmd.extend(["-b", req.branch.strip()])
            clone_cmd.extend([auth_git_url, target_dir])
            proc = await asyncio.create_subprocess_exec(
                *clone_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                err_msg = stderr.decode().strip() or stdout.decode().strip()
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to clone GitHub repository '{repo_input}': {err_msg}",
                )
        else:
            # If target dir exists, fetch origin to ensure latest code
            fetch_cmd = ["git", "-C", target_dir, "fetch", "origin"]
            proc = await asyncio.create_subprocess_exec(
                *fetch_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            if req.branch and req.branch.strip():
                co_cmd = ["git", "-C", target_dir, "checkout", req.branch.strip()]
                proc = await asyncio.create_subprocess_exec(
                    *co_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await proc.communicate()
        repo_abs_path = target_dir
    else:
        repo_abs_path = os.path.abspath(req.repo_path or os.getcwd())
        if not os.path.exists(repo_abs_path):
            raise HTTPException(
                status_code=400,
                detail=f"Repository path does not exist on server: {req.repo_path}",
            )

    task_id = f"task_{uuid.uuid4().hex[:8]}"

    llm_client = LLMAdapter(
        api_key=req.api_key,
        model=req.model,
        base_url=req.base_url,
    )

    runner = AgentRunner(
        task_id=task_id,
        repo_path=repo_abs_path,
        issue_description=req.issue_description,
        llm_client=llm_client,
        max_steps=req.max_steps,
    )

    active_runners[task_id] = runner

    if wait:
        # Synchronous execution mode: wait for completion and return 200 OK
        response.status_code = 200
        await _execute_task_background(runner, req.auto_verify)
        return _to_response(runner)
    else:
        # Asynchronous background execution mode (202 Accepted)
        background_tasks.add_task(_execute_task_background, runner, req.auto_verify)
        return _to_response(runner)


# ==============================================================================
# Task Monitoring, Reports & Lifecycle Management
# ==============================================================================

@router.get("/api/v1/tasks", response_model=List[TaskResponse])
@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks():
    """Lists all submitted tasks and their current statuses."""
    return [_to_response(runner) for runner in active_runners.values()]


@router.get("/api/v1/tasks/{task_id}", response_model=TaskResponse)
@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Fetches details and progress for a specific task."""
    runner = active_runners.get(task_id)
    if not runner:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    resp = _to_response(runner)
    try:
        diff_tool = GitDiffTool(runner.state.repo_path)
        diff_res = await diff_tool.execute()
        resp.git_diff = diff_res.output if diff_res.success else ""
    except Exception:
        pass
    return resp


@router.post("/api/v1/tasks/{task_id}/cancel", response_model=TaskResponse)
@router.post("/tasks/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(task_id: str):
    """Cancels a running task."""
    runner = active_runners.get(task_id)
    if not runner:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    runner.cancel()
    return _to_response(runner)


@router.get("/api/v1/tasks/{task_id}/report", response_model=TaskReportResponse)
@router.get("/tasks/{task_id}/report", response_model=TaskReportResponse)
async def get_task_report(task_id: str):
    """Generates and returns the complete evaluation report (Markdown & JSON) for a task."""
    runner = active_runners.get(task_id)
    if not runner:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    state = runner.state
    
    # Obtain git diff
    diff_tool = GitDiffTool(state.repo_path)
    diff_res = await diff_tool.execute()
    git_diff = diff_res.output if diff_res.success else ""

    metrics = TaskMetrics.from_task_state(state)
    md_report = generate_markdown_report(state, git_diff=git_diff)
    json_report = generate_json_report(state, metrics, git_diff=git_diff)

    return TaskReportResponse(
        task_id=task_id,
        status=state.status.value,
        markdown_report=md_report,
        json_report=json_report,
    )
