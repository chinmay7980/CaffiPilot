"""Command-line interface for the AI Coding Harness."""

import argparse
import asyncio
import os
import sys
import uuid
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from harness import __version__
from harness.config import settings
from harness.engine.agent import AgentRunner
from harness.llm.adapter import LLMAdapter
from harness.telemetry.metrics import TaskMetrics
from harness.telemetry.reporter import generate_json_report, generate_markdown_report
from harness.tools.git_tools import GitDiffTool

console = Console()


async def run_task_cli(
    task_desc: str,
    repo_path: str,
    model: str = None,
    max_steps: int = None,
    output_report: str = None,
) -> int:
    """Executes a coding task directly from CLI with live terminal progress."""
    repo_abs = os.path.abspath(repo_path)
    if not os.path.exists(repo_abs):
        console.print(f"[bold red]Error:[/bold red] Workspace directory '{repo_abs}' does not exist.")
        return 1

    task_id = f"cli_{uuid.uuid4().hex[:6]}"
    chosen_model = model or settings.ai_model

    console.print(
        Panel.fit(
            f"[bold cyan]AI Coding Harness v{__version__}[/bold cyan]\n"
            f"[bold]Task ID:[/bold] {task_id}\n"
            f"[bold]Repository:[/bold] {repo_abs}\n"
            f"[bold]Model:[/bold] [green]{chosen_model}[/green]\n"
            f"[bold]API Key Configured:[/bold] {'[green]Yes[/green]' if settings.has_valid_api_key else '[yellow]No (Running simulated)[/yellow]'}\n"
            f"[bold]Max Steps:[/bold] {max_steps or settings.harness_max_steps}",
            title="🎯 Autonomous Execution Starting",
            border_style="cyan",
        )
    )

    console.print(f"\n[bold yellow]Issue / Task:[/bold yellow] {task_desc}\n")

    llm = LLMAdapter(model=chosen_model)

    def on_step(step_rec):
        status_color = "red" if step_rec.is_error else "green"
        tool_label = f"[bold magenta]{step_rec.tool_name}[/bold magenta]" if step_rec.tool_name else "[italic]Reasoning[/italic]"
        console.print(
            f"  Step [cyan]{step_rec.step_number:02d}[/cyan] "
            f"[[bold {status_color}]{step_rec.stage.value if hasattr(step_rec.stage, 'value') else step_rec.stage}[/bold {status_color}]] "
            f"-> {tool_label} "
            f"([dim]{step_rec.tokens_used} tokens[/dim])"
        )
        if step_rec.thought and len(step_rec.thought.strip()) > 0:
            console.print(f"    [dim italic]Thought: {step_rec.thought[:140]}...[/dim italic]")

    runner = AgentRunner(
        task_id=task_id,
        repo_path=repo_abs,
        issue_description=task_desc,
        llm_client=llm,
        max_steps=max_steps,
        on_step_callback=on_step,
    )

    with console.status("[bold green]Agent working autonomously...[/bold green]", spinner="dots"):
        final_state = await runner.run()

    # Get Git diff
    diff_tool = GitDiffTool(repo_abs)
    diff_res = await diff_tool.execute()
    git_diff = diff_res.output if diff_res.success else ""

    # Generate reports
    metrics = TaskMetrics.from_task_state(final_state)
    md_report = generate_markdown_report(final_state, git_diff=git_diff)

    console.print("\n" + "=" * 70 + "\n")
    if final_state.status.value == "COMPLETED":
        console.print(
            Panel(
                f"[bold green]TASK COMPLETED SUCCESSFULLY[/bold green]\n\n"
                f"[bold]Verification:[/bold] {final_state.verification_status}\n"
                f"[bold]Files Modified:[/bold] {final_state.files_modified}\n\n"
                f"[bold]Final Summary:[/bold]\n{final_state.final_summary}",
                border_style="green",
                title="✨ Result",
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]TASK FINISHED WITH STATUS: {final_state.status.value}[/bold red]\n\n"
                f"[bold]Error Message:[/bold] {final_state.error_message or 'No specific error details'}",
                border_style="red",
                title="⚠️ Outcome",
            )
        )

    if git_diff and git_diff != "[No diff - working tree clean or no changes detected]":
        console.print("\n[bold cyan]Git Diff of Modifications:[/bold cyan]")
        console.print(Syntax(git_diff, "diff", theme="monokai", line_numbers=True))

    if output_report:
        with open(output_report, "w", encoding="utf-8") as f:
            f.write(md_report)
        console.print(f"\n[green]Saved markdown report to:[/green] {output_report}")

    return 0 if final_state.status.value == "COMPLETED" else 1


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Autonomous AI Coding Harness for LCC × DevClub Hackathon 2026",
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # 'run' command
    run_parser = subparsers.add_parser("run", help="Run agent autonomously on a coding task")
    run_parser.add_argument(
        "--task", "-t", type=str, help="Coding task or GitHub issue description"
    )
    run_parser.add_argument(
        "--task-file", "-f", type=str, help="Path to file containing task/issue description"
    )
    run_parser.add_argument(
        "--repo", "-r", type=str, default=".", help="Path to target repository workspace (default: current dir)"
    )
    run_parser.add_argument(
        "--model", "-m", type=str, default=None, help="Prescribed LLM model name override (e.g., gpt-4o, gemini-2.0-flash)"
    )
    run_parser.add_argument(
        "--max-steps", type=int, default=None, help="Maximum autonomous steps (default: 35)"
    )
    run_parser.add_argument(
        "--output-report", "-o", type=str, default=None, help="Path to write final Markdown evaluation report"
    )

    # 'serve' command
    serve_parser = subparsers.add_parser("serve", help="Start the FastAPI backend server")
    serve_parser.add_argument(
        "--host", type=str, default=settings.harness_host, help="Host to bind server"
    )
    serve_parser.add_argument(
        "--port", type=int, default=settings.harness_port, help="Port to bind server"
    )
    serve_parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload on code changes"
    )

    # 'health' command
    subparsers.add_parser("health", help="Check harness configuration and credentials")

    args = parser.parse_args()

    if args.command == "run":
        task_desc = args.task
        if args.task_file and os.path.exists(args.task_file):
            with open(args.task_file, "r", encoding="utf-8") as f:
                task_desc = f.read()

        if not task_desc:
            console.print("[bold red]Error:[/bold red] You must provide either --task or --task-file.")
            sys.exit(1)

        exit_code = asyncio.run(
            run_task_cli(
                task_desc=task_desc,
                repo_path=args.repo,
                model=args.model,
                max_steps=args.max_steps,
                output_report=args.output_report,
            )
        )
        sys.exit(exit_code)

    elif args.command == "serve":
        import uvicorn
        console.print(f"[bold cyan]Starting FastAPI server on http://{args.host}:{args.port}...[/bold cyan]")
        uvicorn.run(
            "harness.api.server:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )

    elif args.command == "health":
        table = Table(title="AI Coding Harness Status")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Version", __version__)
        table.add_row("Configured Model", settings.ai_model)
        table.add_row("Base URL", settings.ai_base_url)
        table.add_row("API Key Present", "Yes" if settings.has_valid_api_key else "No (Set AI_API_KEY)")
        table.add_row("Max Steps", str(settings.harness_max_steps))
        table.add_row("Command Timeout", f"{settings.harness_command_timeout}s")
        table.add_row("Context Token Limit", str(settings.harness_max_context_tokens))
        console.print(table)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
