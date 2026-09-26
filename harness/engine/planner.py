"""Planning, stage progression, and goal management for the agent."""

from harness.engine.state import TaskState, TaskStatus


class TaskPlanner:
    """Evaluates task execution progress and manages high-level stage transitions."""

    def __init__(self, max_steps: int = 35):
        self.max_steps = max_steps

    def evaluate_stage(self, state: TaskState) -> TaskStatus:
        """Determines the current logical stage based on step history and actions taken."""
        if state.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return state.status

        step_num = state.current_step
        
        # Check tools used recently
        recent_tools = [s.tool_name for s in state.steps[-3:] if s.tool_name]

        if "finish_task" in recent_tools:
            return TaskStatus.COMPLETED

        if any(t in ("run_command", "run_tests") for t in recent_tools):
            return TaskStatus.VERIFYING

        if any(t in ("write_file", "edit_file", "git_checkpoint") for t in recent_tools):
            return TaskStatus.EXECUTING

        if step_num <= 3:
            return TaskStatus.EXPLORING

        return TaskStatus.PLANNING

    def get_stage_guidance(self, stage: TaskStatus, remaining_steps: int) -> str:
        """Returns targeted advice when steps are running low."""
        if remaining_steps <= 5:
            return (
                f"[URGENT: Only {remaining_steps} steps remaining! "
                "Wrap up your changes, run test verification, and call `finish_task` now.]"
            )
        return ""
