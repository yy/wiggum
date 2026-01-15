"""CLI interface for ralph-loop."""

from pathlib import Path
from typing import Optional

import typer

from wiggum.agents import AgentConfig, get_agent, get_available_agents
from wiggum.config import (
    CONFIG_FILE,
    get_templates_dir,
    read_config,
    write_config,
)
from wiggum.parsing import parse_markdown_from_output
from wiggum.runner import (
    get_file_changes,
    run_claude_for_planning,
    write_log_entry,
)
from wiggum.tasks import (
    add_task_to_file,
    get_current_task,
    get_existing_task_descriptions,
    get_existing_tasks_context,
    tasks_remaining,
)

app = typer.Typer(help="Ralph Wiggum loop for agents")


@app.command()
def run(
    prompt_file: Optional[Path] = typer.Option(
        None, "-f", "--file", help="Prompt file (default: LOOP-PROMPT.md)"
    ),
    tasks_file: Optional[Path] = typer.Option(
        None,
        "--tasks",
        help="Tasks file for stop condition (stop when all tasks complete)",
    ),
    max_iterations: Optional[int] = typer.Option(
        None, "-n", "--max-iterations", help="Max iterations"
    ),
    agent: Optional[str] = typer.Option(
        None,
        "--agent",
        help="Agent to use (e.g., 'claude', 'codex', 'gemini')",
    ),
    yolo: bool = typer.Option(
        True,
        "--yolo/--no-yolo",
        help="Skip all permission prompts (default: enabled)",
    ),
    allow_paths: Optional[str] = typer.Option(
        None,
        "--allow-paths",
        help="Comma-separated paths to allow writing (e.g., 'src/,tests/')",
    ),
    continue_session: bool = typer.Option(
        False,
        "--continue",
        help="Maintain conversation context between iterations (pass -c to claude after first iteration)",
    ),
    reset_session: bool = typer.Option(
        False,
        "--reset",
        help="Start fresh each iteration (default behavior)",
    ),
    keep_running: bool = typer.Option(
        False,
        "--keep-running",
        help="Continue running even when all tasks are complete (agent can add new tasks)",
    ),
    stop_when_done: bool = typer.Option(
        False,
        "--stop-when-done",
        help="Stop loop when all tasks are complete (default behavior)",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would run"),
    log_file: Optional[Path] = typer.Option(
        None, "--log-file", help="Log each iteration's output to this file"
    ),
    show_progress: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        "--show-progress",
        help="Show file changes (via git status) after each iteration",
    ),
    identify_tasks: bool = typer.Option(
        False,
        "--identify-tasks",
        help="Analyze codebase and populate TASKS.md with refactoring/cleanup tasks, then exit",
    ),
) -> None:
    """Run the agent loop. Stops when all tasks in TASKS.md are complete."""
    # Read config file and apply settings (CLI flags override config)
    config = read_config()
    security_config = config.get("security", {})
    loop_config = config.get("loop", {})

    # Apply security config values if CLI flags not explicitly set
    if not yolo and security_config.get("yolo", False):
        yolo = True
    if allow_paths is None and security_config.get("allow_paths"):
        allow_paths = security_config.get("allow_paths")

    # Apply loop config values with defaults
    if max_iterations is None:
        max_iterations = loop_config.get("max_iterations", 10)
    if tasks_file is None:
        tasks_file = Path(loop_config.get("tasks_file", "TASKS.md"))
    if prompt_file is None:
        config_prompt_file = loop_config.get("prompt_file")
        if config_prompt_file:
            prompt_file = Path(config_prompt_file)
    if agent is None:
        agent = loop_config.get("agent")  # None means use default (claude)

    # Apply output config values if CLI flags not explicitly set
    output_config = config.get("output", {})
    if log_file is None and output_config.get("log_file"):
        log_file = Path(output_config.get("log_file"))
    if not show_progress and output_config.get("verbose", False):
        show_progress = True

    # Apply session config values if CLI flags not explicitly set
    session_config = config.get("session", {})
    if not continue_session and not reset_session:
        # Neither flag set - use config if available
        if session_config.get("continue_session", False):
            continue_session = True

    # Check for mutually exclusive flags
    if continue_session and reset_session:
        typer.echo(
            "Error: --continue and --reset are mutually exclusive. Cannot use both.",
            err=True,
        )
        raise typer.Exit(1)

    if keep_running and stop_when_done:
        typer.echo(
            "Error: --keep-running and --stop-when-done are mutually exclusive. Cannot use both.",
            err=True,
        )
        raise typer.Exit(1)

    # Apply loop config for keep_running if CLI flags not explicitly set
    if not keep_running and not stop_when_done:
        # Neither flag set - use config if available
        if loop_config.get("keep_running", False):
            keep_running = True

    # Handle --identify-tasks: analyze codebase and populate TASKS.md
    if identify_tasks:
        _run_identify_tasks(tasks_file)
        return

    # Determine prompt source - always from file
    if prompt_file is None:
        prompt_file = Path("LOOP-PROMPT.md")
    if not prompt_file.exists():
        typer.echo(f"Error: Prompt file '{prompt_file}' not found", err=True)
        raise typer.Exit(1)
    prompt = prompt_file.read_text()

    # Determine agent name for display (None means default which is "claude")
    agent_name = agent if agent else "claude"

    # Validate agent name if specified
    if agent is not None:
        available = get_available_agents()
        if agent not in available:
            typer.echo(
                f"Error: Unknown agent '{agent}'. "
                f"Available agents: {', '.join(available)}",
                err=True,
            )
            raise typer.Exit(1)

    if dry_run:
        cmd = ["claude", "--print", "-p", "<prompt>"]
        if yolo:
            cmd.append("--dangerously-skip-permissions")
        if allow_paths:
            for path in allow_paths.split(","):
                cmd.extend(["--allowedTools", f"Edit:{path.strip()}*"])
                cmd.extend(["--allowedTools", f"Write:{path.strip()}*"])
        typer.echo(f"Would run {max_iterations} iterations")
        typer.echo(f"Agent: {agent_name}")
        typer.echo(f"Command: {' '.join(cmd)}")
        typer.echo(f"Stop condition: tasks (check {tasks_file})")
        if keep_running:
            typer.echo(
                "Task completion mode: keep running (continue for all iterations)"
            )
        else:
            typer.echo(
                "Task completion mode: stop when done (exit when tasks complete)"
            )
        if continue_session:
            typer.echo(
                "Session mode: continue (will pass -c to claude after first iteration)"
            )
        else:
            typer.echo("Session mode: reset (fresh session each iteration)")
        if log_file:
            typer.echo(f"Log file: {log_file}")
        if show_progress:
            typer.echo(
                "Progress tracking: enabled (will show file changes via git status)"
            )
        typer.echo(f"Prompt:\n---\n{prompt}\n---")
        return

    def check_stop_conditions() -> Optional[str]:
        """Check stop conditions and return exit message if should stop."""
        if not keep_running and not tasks_remaining(tasks_file):
            return f"All tasks in {tasks_file} are complete. Exiting."
        return None

    for i in range(1, max_iterations + 1):
        # Check stop conditions before running
        exit_message = check_stop_conditions()
        if exit_message:
            typer.echo(f"\n{exit_message}")
            break

        typer.echo(f"\n{'=' * 60}")
        typer.echo(f"Iteration {i}/{max_iterations}")
        current_task = get_current_task(tasks_file)
        if current_task:
            typer.echo(f"Current task: {current_task}")
        typer.echo(f"{'=' * 60}\n")

        # Run the agent
        agent_instance = get_agent(agent)
        agent_config = AgentConfig(
            prompt=prompt,
            yolo=yolo,
            allow_paths=allow_paths,
            # After first iteration, continue session if requested
            continue_session=continue_session and i > 1,
        )
        result = agent_instance.run(agent_config)
        # Print output to console
        if result.stdout:
            typer.echo(result.stdout)
        if result.stderr:
            typer.echo(result.stderr, err=True)
        # Exit on agent error (e.g., command not found)
        if result.return_code != 0 and "not found" in result.stderr.lower():
            raise typer.Exit(1)
        # Log output to file if requested
        if log_file:
            write_log_entry(log_file, i, result.stdout or "")
        # Show file changes if requested
        if show_progress:
            success, changes = get_file_changes()
            typer.echo("\n--- File Changes ---")
            typer.echo(changes)

        # Check stop conditions after running
        exit_message = check_stop_conditions()
        if exit_message:
            typer.echo(f"\n{exit_message}")
            break

    typer.echo(f"\n{'=' * 60}")
    typer.echo("Loop completed")
    typer.echo(f"{'=' * 60}")


@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files"),
    templates_dir: Optional[Path] = typer.Option(
        None,
        "--templates",
        "-t",
        help="Templates directory (default: package templates)",
    ),
) -> None:
    """Initialize a loop with LOOP-PROMPT.md and TASKS.md using agent-assisted planning."""
    # Find templates
    if templates_dir is None:
        if Path("templates").is_dir():
            templates_dir = Path("templates")
        else:
            templates_dir = get_templates_dir()

    prompt_template_path = templates_dir / "LOOP-PROMPT.md"
    tasks_template_path = templates_dir / "TASKS.md"
    meta_prompt_path = templates_dir / "META-PROMPT.md"

    if not prompt_template_path.exists():
        typer.echo(f"Error: Template not found: {prompt_template_path}", err=True)
        raise typer.Exit(1)

    if not meta_prompt_path.exists():
        typer.echo(f"Error: Meta prompt not found: {meta_prompt_path}", err=True)
        raise typer.Exit(1)

    prompt_path = Path("LOOP-PROMPT.md")
    tasks_path = Path("TASKS.md")

    # Track if we're updating existing TASKS.md (for merge behavior)
    tasks_file_exists = tasks_path.exists()

    # Check for existing files
    if not force:
        if prompt_path.exists():
            typer.echo(
                f"Error: {prompt_path} already exists. Use --force to overwrite.",
                err=True,
            )
            raise typer.Exit(1)
        # Note: TASKS.md existence is OK - we'll merge tasks instead of failing

    # Get goal - infer from README if available
    typer.echo("Setting up ralph-loop...\n")

    readme_path = Path("README.md")
    readme_content = ""
    if readme_path.exists():
        readme_content = readme_path.read_text()
        typer.echo("Found README.md - inferring goal from it.")
        goal = ""  # Will be inferred by Claude
    else:
        goal = typer.prompt("What is the goal of this project?")

    # Agent-assisted planning (always)
    typer.echo("\nAnalyzing codebase and planning tasks...")
    meta_prompt = meta_prompt_path.read_text()
    if readme_content:
        meta_prompt = meta_prompt.replace(
            "{{goal}}", f"(Infer from README below)\n\n## README.md\n\n{readme_content}"
        )
    else:
        meta_prompt = meta_prompt.replace("{{goal}}", goal)

    # Include existing tasks context if TASKS.md exists
    existing_tasks_context = get_existing_tasks_context(tasks_path)
    meta_prompt = meta_prompt.replace("{{existing_tasks}}", existing_tasks_context)

    output = run_claude_for_planning(meta_prompt)

    use_suggestions = False
    doc_files = "README.md, CLAUDE.md"
    tasks = []
    suggested_constraints = {}

    if output:
        config = parse_markdown_from_output(output)
        if config:
            # Get goal from Claude if we inferred from README
            if not goal:
                goal = config.get("goal", "")
            suggested_tasks = config.get("tasks", [])
            suggested_constraints = config.get("constraints", {})

            typer.echo("\nSuggested configuration:")
            typer.echo(f"  Goal: {goal}")
            typer.echo(f"  Doc files: {doc_files}")
            typer.echo("\nSuggested tasks:")
            for task_desc in suggested_tasks:
                typer.echo(f"  - {task_desc}")

            # Show suggested constraints if present
            if suggested_constraints:
                typer.echo("\nSuggested security constraints:")
                security_mode = suggested_constraints.get(
                    "security_mode", "conservative"
                )
                typer.echo(f"  Security mode: {security_mode}")
                if security_mode == "path_restricted":
                    allow_paths = suggested_constraints.get("allow_paths", "")
                    typer.echo(f"  Allowed paths: {allow_paths}")
                if "internet_access" in suggested_constraints:
                    typer.echo(
                        f"  Internet access: {suggested_constraints['internet_access']}"
                    )

            if typer.confirm("\nUse these suggestions?", default=True):
                tasks = [f"- [ ] {task_desc}" for task_desc in suggested_tasks]
                use_suggestions = True
        else:
            typer.echo("Could not parse Claude's suggestions.")
    else:
        typer.echo("Could not run Claude.")

    # Manual entry if suggestions not used
    if not use_suggestions:
        typer.echo("\nManual configuration:")
        if not goal:
            goal = typer.prompt("What is the goal of this project?")
        doc_files = typer.prompt(
            "Which doc files should be updated?", default=doc_files
        )

        typer.echo("\nEnter tasks (one per line, empty line to finish):")
        tasks = []
        while True:
            task = typer.prompt("Task", default="", show_default=False)
            if not task:
                break
            tasks.append(f"- [ ] {task}")

    # Handle security constraints
    security_yolo = False
    security_allow_paths = ""

    # Use suggested constraints if accepted
    if use_suggestions and suggested_constraints:
        security_mode = suggested_constraints.get("security_mode", "conservative")

        if security_mode == "yolo":
            typer.echo(
                "\nWARNING: YOLO mode skips ALL permission prompts. "
                "Claude will be able to modify any file without asking."
            )
            typer.echo(
                "This is dangerous and should only be used for trusted projects."
            )
            if typer.confirm(
                "Are you sure you want to enable YOLO mode?", default=False
            ):
                security_yolo = True
            else:
                # User cancelled suggested yolo, fall back to manual
                suggested_constraints = {}
        elif security_mode == "path_restricted":
            security_allow_paths = suggested_constraints.get("allow_paths", "")
        # else: conservative mode - no special permissions needed

    # Manual security selection if no constraints or user cancelled
    if not use_suggestions or not suggested_constraints:
        typer.echo("\nSecurity configuration:")
        typer.echo("  1) Conservative - Claude will ask permission for each action")
        typer.echo("  2) Path-restricted - Allow writes to specific paths only")
        typer.echo("  3) YOLO mode - Skip all permission prompts (dangerous!)")

        security_choice = typer.prompt("Choose security mode [1/2/3]", default="1")

        if security_choice == "2":
            security_allow_paths = typer.prompt(
                "Enter paths to allow (comma-separated, e.g., 'src/,tests/')"
            )
        elif security_choice == "3":
            typer.echo(
                "\nWARNING: YOLO mode skips ALL permission prompts. "
                "Claude will be able to modify any file without asking."
            )
            typer.echo(
                "This is dangerous and should only be used for trusted projects."
            )
            if typer.confirm(
                "Are you sure you want to enable YOLO mode?", default=False
            ):
                security_yolo = True
            else:
                # User cancelled, ask again
                typer.echo("\nYOLO mode cancelled. Choosing a different mode:")
                security_choice = typer.prompt(
                    "Choose security mode [1/2]", default="1"
                )
                if security_choice == "2":
                    security_allow_paths = typer.prompt(
                        "Enter paths to allow (comma-separated, e.g., 'src/,tests/')"
                    )

    # Write config with security and default loop settings
    write_config(
        {
            "security": {
                "yolo": security_yolo,
                "allow_paths": security_allow_paths,
            },
            "loop": {
                "max_iterations": 10,
            },
        }
    )

    # Generate files from templates
    prompt_template = prompt_template_path.read_text()
    tasks_str = "\n".join(tasks) if tasks else "- [ ] (add your first task here)"
    prompt_content = (
        prompt_template.replace("{{goal}}", goal)
        .replace("{{doc_files}}", doc_files)
        .replace("{{tasks}}", tasks_str)
    )

    # Handle TASKS.md: merge if exists (unless --force), otherwise create new
    if tasks_file_exists and not force:
        # Merge: add only tasks that don't already exist
        existing_tasks = get_existing_task_descriptions(tasks_path)
        new_tasks_added = 0

        # Extract task descriptions from the formatted tasks list
        for task_line in tasks:
            # task_line is like "- [ ] Description"
            task_desc = task_line.replace("- [ ] ", "").strip()
            if task_desc and task_desc.lower() not in existing_tasks:
                add_task_to_file(tasks_path, task_desc)
                new_tasks_added += 1

        typer.echo(f"\nUpdated {tasks_path}: added {new_tasks_added} new task(s)")
    else:
        # Create new or overwrite with --force
        tasks_template = (
            tasks_template_path.read_text()
            if tasks_template_path.exists()
            else "# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n{{tasks}}\n"
        )
        tasks_content = tasks_template.replace(
            "{{tasks}}",
            "\n".join(tasks) if tasks else "- [ ] (add your first task here)",
        )
        tasks_path.write_text(tasks_content)
        typer.echo(f"\nCreated {tasks_path}")

    prompt_path.write_text(prompt_content)
    typer.echo(f"Created {prompt_path} and {CONFIG_FILE}")
    typer.echo("\nRun the loop with: ralph-loop run")


def _run_identify_tasks(tasks_file: Path) -> None:
    """Analyze codebase and populate TASKS.md with identified tasks.

    Args:
        tasks_file: Path to the tasks file to populate.
    """
    # Find meta-prompt template
    if Path("templates").is_dir():
        templates_dir = Path("templates")
    else:
        templates_dir = get_templates_dir()

    meta_prompt_path = templates_dir / "META-PROMPT.md"

    if not meta_prompt_path.exists():
        typer.echo(f"Error: Meta prompt not found: {meta_prompt_path}", err=True)
        raise typer.Exit(1)

    typer.echo("Analyzing codebase to identify tasks...")

    # Build the meta-prompt with goal from README if available
    meta_prompt = meta_prompt_path.read_text()

    readme_path = Path("README.md")
    if readme_path.exists():
        readme_content = readme_path.read_text()
        meta_prompt = meta_prompt.replace(
            "{{goal}}",
            f"(Infer from README below)\n\n## README.md\n\n{readme_content}",
        )
    else:
        meta_prompt = meta_prompt.replace(
            "{{goal}}", "Analyze codebase for refactoring and improvement opportunities"
        )

    # Include existing tasks context
    existing_tasks_context = get_existing_tasks_context(tasks_file)
    meta_prompt = meta_prompt.replace("{{existing_tasks}}", existing_tasks_context)

    # Run Claude for planning
    output = run_claude_for_planning(meta_prompt)

    if not output:
        typer.echo("Could not identify tasks (Claude returned no output).")
        return

    config = parse_markdown_from_output(output)
    if not config or not config.get("tasks"):
        typer.echo("Could not identify any new tasks.")
        return

    suggested_tasks = config.get("tasks", [])

    # Display identified tasks
    typer.echo("\nIdentified tasks:")
    for task_desc in suggested_tasks:
        typer.echo(f"  - {task_desc}")

    # Merge tasks with existing ones (no duplicates)
    existing_task_descs = get_existing_task_descriptions(tasks_file)
    new_tasks_added = 0

    for task_desc in suggested_tasks:
        if task_desc.lower() not in existing_task_descs:
            add_task_to_file(tasks_file, task_desc)
            new_tasks_added += 1

    typer.echo(f"\nAdded {new_tasks_added} new task(s) to {tasks_file}")


@app.command()
def add(
    description: str = typer.Argument(..., help="Task description to add"),
    tasks_file: Path = typer.Option(
        Path("TASKS.md"),
        "-f",
        "--tasks-file",
        help="Tasks file to add to (default: TASKS.md)",
    ),
) -> None:
    """Add a new task to TASKS.md."""
    # Validate description
    if not description or not description.strip():
        typer.echo("Error: Task description cannot be empty.", err=True)
        raise typer.Exit(1)

    description = description.strip()

    add_task_to_file(tasks_file, description)
    typer.echo(f"Added task: {description}")


if __name__ == "__main__":
    app()
