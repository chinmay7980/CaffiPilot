"""Core autonomous agent execution loop with ReAct orchestration."""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from harness.config import settings
from harness.engine.context import ContextManager
from harness.engine.planner import TaskPlanner
from harness.engine.recovery import ErrorRecoveryManager
from harness.engine.state import StepRecord, TaskState, TaskStatus
from harness.llm.base import BaseLLMClient
from harness.llm.prompts import SYSTEM_PROMPT, TASK_TEMPLATE
from harness.tools.registry import ToolRegistry, create_default_registry

logger = logging.getLogger(__name__)


class AgentRunner:
    """Orchestrates the autonomous agent execution cycle on a target repository."""

    def __init__(
        self,
        task_id: str,
        repo_path: str,
        issue_description: str,
        llm_client: BaseLLMClient,
        max_steps: Optional[int] = None,
        max_tool_calls: Optional[int] = None,
        tool_registry: Optional[ToolRegistry] = None,
        on_step_callback: Optional[Callable[[StepRecord], Any]] = None,
    ):
        self.state = TaskState(
            task_id=task_id,
            repo_path=repo_path,
            issue_description=issue_description,
            max_steps=max_steps or settings.harness_max_steps,
            max_tool_calls=max_tool_calls or 50,
            model=getattr(llm_client, "model", "gpt-4o"),
        )
        self.llm = llm_client
        self.tools = tool_registry or create_default_registry(repo_path)
        self.context = ContextManager(
            task_id=task_id, max_tokens=settings.harness_max_context_tokens
        )
        self.recovery = ErrorRecoveryManager(max_consecutive_failures=4)
        self.planner = TaskPlanner(max_steps=self.state.max_steps)
        self.on_step_callback = on_step_callback
        self._is_cancelled = False
        self._recent_tool_call_history: List[str] = []

    def cancel(self) -> None:
        """Requests graceful cancellation of the agent run."""
        self._is_cancelled = True
        self.state.mark_cancelled()

    def _has_inspected_repository(self) -> bool:
        """Returns True if any inspection or search tool has been called in step history."""
        inspection_tools = {
            "read_file",
            "list_files",
            "find_files",
            "grep_search",
            "inspect_project",
            "get_file_metadata",
            "git_status",
            "git_diff",
            "git_log",
        }
        for step in self.state.steps:
            if step.tool_name in inspection_tools:
                return True
        return False

    async def run(self) -> TaskState:
        """Executes the full autonomous problem-solving loop."""
        logger.info(f"Starting agent task [{self.state.task_id}] on {self.state.repo_path}")
        self.state.mark_running()
        self.state.status = TaskStatus.EXPLORING

        # Initialize context history with system prompt & formatted task description
        self.context.add_system_message(SYSTEM_PROMPT)
        initial_user_prompt = TASK_TEMPLATE.format(
            task_description=self.state.issue_description,
            workspace_path=self.state.repo_path,
        )
        self.context.add_user_message(initial_user_prompt)

        tool_schemas = self.tools.get_openai_schemas()

        while self.state.current_step < self.state.max_steps:
            # Check cancellation
            if self._is_cancelled:
                logger.info(f"Task [{self.state.task_id}] was cancelled.")
                self.state.mark_cancelled()
                break

            # Check max tool call limit
            if self.state.tool_call_count >= self.state.max_tool_calls:
                logger.warning(f"Task [{self.state.task_id}] reached max tool call limit ({self.state.max_tool_calls}).")
                self.state.mark_failed(
                    f"Execution stopped: reached maximum tool call limit ({self.state.max_tool_calls})."
                )
                break

            # Check bounded retry / stuck limit
            if self.recovery.is_stuck:
                logger.warning(f"Task [{self.state.task_id}] encountered consecutive failure threshold.")
                self.state.mark_failed(
                    f"Execution stopped: exceeded maximum consecutive failure threshold ({self.recovery.max_consecutive_failures} failures in a row)."
                )
                break

            remaining_steps = self.state.max_steps - self.state.current_step
            guidance = self.planner.get_stage_guidance(self.state.status, remaining_steps)
            if guidance:
                self.context.add_user_message(guidance)

            # 1. Prepare messages within token budget
            messages = self.context.get_messages_for_llm()

            # 2. Invoke LLM
            try:
                response = await self.llm.generate(
                    messages=messages,
                    tools=tool_schemas,
                    temperature=0.0,
                )
            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
                self.state.mark_failed(f"LLM API failure: {str(e)}")
                break

            # 3. Handle model textual thought / answer
            thought_text = response.content or ""
            
            # Extract execution plan lines if thought contains plan keywords
            if not self.state.execution_plan and ("1." in thought_text or "- [ ]" in thought_text or "Plan:" in thought_text):
                plan_lines = []
                for line in thought_text.splitlines():
                    line_s = line.strip()
                    if any(line_s.startswith(prefix) for prefix in ("1.", "2.", "3.", "4.", "5.", "-", "*")):
                        plan_lines.append(line_s)
                    elif "1." in line_s:
                        idx = line_s.find("1.")
                        plan_lines.append(line_s[idx:].strip())
                if plan_lines:
                    self.state.execution_plan = plan_lines[:10]

            # If no tool calls were made
            if not response.tool_calls:
                step_rec = StepRecord(
                    step_number=self.state.current_step + 1,
                    stage=self.state.status,
                    thought=thought_text,
                    tokens_used=response.total_tokens,
                )
                self.state.add_step(step_rec)
                self.context.add_assistant_message(content=thought_text)
                
                if self.on_step_callback:
                    try:
                        self.on_step_callback(step_rec)
                    except Exception:
                        pass

                # Prompt model to take action if active
                if self.state.current_step < self.state.max_steps:
                    self.context.add_user_message(
                        "Please proceed by calling an appropriate workspace tool or use `finish_task` if done."
                    )
                continue

            # 4. Handle tool execution calls
            assistant_tool_calls_dict = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": str(tc.arguments)},
                }
                for tc in response.tool_calls
            ]
            self.context.add_assistant_message(
                content=thought_text, tool_calls=assistant_tool_calls_dict
            )

            for tool_call in response.tool_calls:
                tool_name = tool_call.name
                tool_args = tool_call.arguments
                tool_id = tool_call.id

                logger.debug(f"Step {self.state.current_step + 1}: Executing {tool_name} with {tool_args}")

                # Loop prevention: check duplicate consecutive tool calls
                call_sig = f"{tool_name}:{str(tool_args)}"
                self._recent_tool_call_history.append(call_sig)
                if len(self._recent_tool_call_history) >= 3 and self._recent_tool_call_history[-3:] == [call_sig] * 3:
                    logger.warning(f"Infinite loop detected: tool '{tool_name}' called 3 times with identical arguments.")
                    self.state.mark_failed(
                        f"Infinite loop protection triggered: tool '{tool_name}' called repeatedly with identical parameters."
                    )
                    return self.state

                # Pre-inspection requirement check
                modification_tools = {"write_file", "edit_file", "apply_patch", "delete_file"}
                if tool_name in modification_tools and not self._has_inspected_repository():
                    warning_msg = (
                        f"Safety Violation: Cannot invoke modification tool '{tool_name}' before inspecting the workspace. "
                        "Please run `read_file`, `list_files`, or `inspect_project` first."
                    )
                    self.context.add_tool_message(
                        tool_call_id=tool_id,
                        name=tool_name,
                        content=warning_msg,
                    )
                    step_rec = StepRecord(
                        step_number=self.state.current_step + 1,
                        stage=self.state.status,
                        thought=thought_text,
                        tool_name=tool_name,
                        tool_args=tool_args,
                        tool_output=warning_msg,
                        is_error=True,
                        tokens_used=response.total_tokens,
                    )
                    self.state.add_step(step_rec)
                    self.recovery.record_failure(warning_msg)
                    if self.on_step_callback:
                        try:
                            self.on_step_callback(step_rec)
                        except Exception:
                            pass
                    continue

                # Execute tool
                tool_result = await self.tools.execute(tool_name, tool_args)

                # Track modified files
                if tool_name in ("write_file", "edit_file", "apply_patch") and tool_result.success:
                    file_path = tool_args.get("path")
                    if file_path and file_path not in self.state.files_modified:
                        self.state.files_modified.append(file_path)

                # Check for completion tool
                if tool_name == "finish_task" and tool_result.success:
                    summary = tool_args.get("summary", "Task concluded.")
                    verification = tool_args.get("verification_status", "passed")
                    files = tool_args.get("files_modified", self.state.files_modified)
                    
                    self.context.add_tool_message(
                        tool_call_id=tool_id,
                        name=tool_name,
                        content=tool_result.to_message_content(),
                    )
                    step_rec = StepRecord(
                        step_number=self.state.current_step + 1,
                        stage=TaskStatus.COMPLETED,
                        thought=thought_text,
                        tool_name=tool_name,
                        tool_args=tool_args,
                        tool_output=tool_result.output,
                        is_error=False,
                        tokens_used=response.total_tokens,
                    )
                    self.state.add_step(step_rec)
                    self.state.mark_completed(
                        summary=summary,
                        verification=verification,
                        files=files,
                    )
                    if self.on_step_callback:
                        try:
                            self.on_step_callback(step_rec)
                        except Exception:
                            pass
                    logger.info(f"Task [{self.state.task_id}] completed successfully.")
                    return self.state

                # Normal tool execution result handling
                result_content = tool_result.to_message_content()
                is_error = not tool_result.success

                if is_error:
                    recovery_hint = self.recovery.format_recovery_hint(
                        tool_name, tool_result.error or tool_result.output
                    )
                    result_content += f"\n\n{recovery_hint}"
                    if tool_name in ("delete_file", "git_rollback"):
                        result_content += (
                            f"\n[Recovery Safety Note: Automatic retries of destructive operation '{tool_name}' "
                            "are prohibited to prevent state corruption. Please inspect task state manually.]"
                        )
                else:
                    self.recovery.record_success()

                self.context.add_tool_message(
                    tool_call_id=tool_id,
                    name=tool_name,
                    content=result_content,
                )

                step_rec = StepRecord(
                    step_number=self.state.current_step + 1,
                    stage=self.state.status,
                    thought=thought_text,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    tool_output=tool_result.output or tool_result.error,
                    is_error=is_error,
                    tokens_used=response.total_tokens,
                )
                self.state.add_step(step_rec)

                # Update stage
                self.state.status = self.planner.evaluate_stage(self.state)

                if self.on_step_callback:
                    try:
                        self.on_step_callback(step_rec)
                    except Exception:
                        pass

        # If loop exited without explicit completion
        if self.state.status not in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ):
            self.state.mark_failed(
                f"Task reached maximum step limit ({self.state.max_steps}) without calling finish_task."
            )

        return self.state
