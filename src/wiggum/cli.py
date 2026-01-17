"""CLI interface for wiggum."""

import time
from pathlib import Path
from typing import Optional

import typer

from wiggum.agents import (
    AgentConfig,
    get_agent,
    get_available_agents,
)
from wiggum.config import (
    CONFIG_FILE,
    resolve_run_config,
    resolve_templates_dir,
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
    get_all_tasks,
    get_current_task,
    get_existing_task_descriptions,
    get_existing_tasks_context,
    tasks_remaining,
)

app = typer.Typer(help="Run iterative agent loops with task tracking")


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
    git_workflow: bool = typer.Option(
        False,
        "--git",
        help="Enable git workflow: fetch/merge main, create branch, create PR at end",
    ),
    no_git_workflow: bool = typer.Option(
        False,
        "--no-git",
        help="Disable git workflow (default behavior)",
    ),
    branch_prefix: Optional[str] = typer.Option(
        None,
        "--branch-prefix",
        help="Prefix for auto-generated branch names (default: 'wiggum')",
    ),
) -> None:
    """Run the agent loop. Stops when all tasks in TASKS.md are complete."""
    # Resolve configuration (CLI flags override config file)
    try:
        cfg = resolve_run_config(
            yolo=yolo,
            allow_paths=allow_paths,
            max_iterations=max_iterations,
            tasks_file=tasks_file,
            prompt_file=prompt_file,
            agent=agent,
            log_file=log_file,
            show_progress=show_progress,
            continue_session=continue_session,
            reset_session=reset_session,
            keep_running=keep_running,
            stop_when_done=stop_when_done,
            git_workflow=git_workflow,
            no_git_workflow=no_git_workflow,
            branch_prefix=branch_prefix,
        )
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    # Handle --identify-tasks: analyze codebase and populate TASKS.md
    if identify_tasks:
        _run_identify_tasks(cfg.tasks_file)
        return

    # Determine prompt source - always from file
    resolved_prompt_file = cfg.prompt_file
    if resolved_prompt_file is None:
        resolved_prompt_file = Path("LOOP-PROMPT.md")
    if not resolved_prompt_file.exists():
        typer.echo(f"Error: Prompt file '{resolved_prompt_file}' not found", err=True)
        raise typer.Exit(1)
    prompt = resolved_prompt_file.read_text()

    # Determine agent name for display (None means default which is "claude")
    agent_name = cfg.agent if cfg.agent else "claude"

    # Validate agent name if specified
    if cfg.agent is not None:
        available = get_available_agents()
        if cfg.agent not in available:
            typer.echo(
                f"Error: Unknown agent '{cfg.agent}'. "
                f"Available agents: {', '.join(available)}",
                err=True,
            )
            raise typer.Exit(1)

    if dry_run:
        cmd = ["claude", "--print", "-p", "<prompt>"]
        if cfg.yolo:
            cmd.append("--dangerously-skip-permissions")
        if cfg.allow_paths:
            for path in cfg.allow_paths.split(","):
                cmd.extend(["--allowedTools", f"Edit:{path.strip()}*"])
                cmd.extend(["--allowedTools", f"Write:{path.strip()}*"])
        typer.echo(f"Would run {cfg.max_iterations} iterations")
        typer.echo(f"Agent: {agent_name}")
        typer.echo(f"Command: {' '.join(cmd)}")
        typer.echo(f"Stop condition: tasks (check {cfg.tasks_file})")
        if cfg.keep_running:
            typer.echo(
                "Task completion mode: keep running (continue for all iterations)"
            )
        else:
            typer.echo(
                "Task completion mode: stop when done (exit when tasks complete)"
            )
        if cfg.continue_session:
            typer.echo(
                "Session mode: continue (will pass -c to claude after first iteration)"
            )
        else:
            typer.echo("Session mode: reset (fresh session each iteration)")
        if cfg.log_file:
            typer.echo(f"Log file: {cfg.log_file}")
        if cfg.show_progress:
            typer.echo(
                "Progress tracking: enabled (will show file changes via git status)"
            )
        if cfg.git_workflow:
            typer.echo(
                "Git workflow: enabled (will fetch/merge main, create branch, create PR)"
            )
            typer.echo(f"Branch prefix: {cfg.branch_prefix}")
        typer.echo(f"Prompt:\n---\n{prompt}\n---")
        return

    # Validate agent CLI is available before running
    from wiggum.agents import check_cli_available, get_cli_error_message

    if not check_cli_available(agent_name):
        typer.echo(get_cli_error_message(agent_name), err=True)
        raise typer.Exit(1)

    # Git workflow setup: fetch/merge main and create a new branch
    created_branch = None
    if cfg.git_workflow:
        from wiggum.git import (
            GitError,
            create_branch,
            fetch_and_merge_main,
            generate_branch_name,
            is_git_repo,
        )

        if not is_git_repo():
            typer.echo("Error: --git requires a git repository", err=True)
            raise typer.Exit(1)

        # Validate gh CLI is available for PR creation
        if not check_cli_available("gh"):
            typer.echo(get_cli_error_message("gh"), err=True)
            raise typer.Exit(1)

        typer.echo("\n--- Git Workflow Setup ---")

        # Fetch and merge main
        try:
            if fetch_and_merge_main():
                typer.echo("Fetched and merged latest from main branch")
            else:
                typer.echo("No remote configured - skipping fetch/merge")
        except GitError as e:
            typer.echo(f"Warning: Could not fetch/merge main: {e}", err=True)

        # Create a new branch
        created_branch = generate_branch_name(cfg.branch_prefix)
        try:
            create_branch(created_branch)
            typer.echo(f"Created and switched to branch: {created_branch}")
        except GitError as e:
            typer.echo(f"Error creating branch: {e}", err=True)
            raise typer.Exit(1)

    def check_stop_conditions() -> Optional[str]:
        """Check stop conditions and return exit message if should stop."""
        if not cfg.keep_running and not tasks_remaining(cfg.tasks_file):
            return f"All tasks in {cfg.tasks_file} are complete. Exiting."
        return None

    for i in range(1, cfg.max_iterations + 1):
        # Check stop conditions before running
        exit_message = check_stop_conditions()
        if exit_message:
            typer.echo(f"\n{exit_message}")
            break

        typer.echo(f"\n{'=' * 60}")
        typer.echo(f"Iteration {i}/{cfg.max_iterations}")
        current_task = get_current_task(cfg.tasks_file)
        if current_task:
            typer.echo(f"Current task: {current_task}")
        typer.echo(f"{'=' * 60}\n")

        # Run the agent
        agent_instance = get_agent(cfg.agent)
        agent_config = AgentConfig(
            prompt=prompt,
            yolo=cfg.yolo,
            allow_paths=cfg.allow_paths,
            # After first iteration, continue session if requested
            continue_session=cfg.continue_session and i > 1,
        )

        start_time = time.time()
        result = agent_instance.run(agent_config)
        elapsed = time.time() - start_time
        # Print output to console
        if result.stdout:
            typer.echo(result.stdout)
        if result.stderr:
            typer.echo(result.stderr, err=True)
        # Exit on agent error (e.g., command not found)
        if result.return_code != 0 and "not found" in result.stderr.lower():
            raise typer.Exit(1)
        # Log output to file if requested
        if cfg.log_file:
            write_log_entry(cfg.log_file, i, result.stdout or "")
        # Show progress info if requested
        if cfg.show_progress:
            typer.echo("\n--- Iteration Summary ---")
            # Show elapsed time
            if elapsed >= 60:
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                typer.echo(f"Duration: {minutes}m {seconds}s")
            else:
                typer.echo(f"Duration: {elapsed:.1f}s")
            # Show task status
            task_list = get_all_tasks(cfg.tasks_file)
            if task_list:
                todo_count = len(task_list.todo)
                done_count = len(task_list.done)
                typer.echo(f"Tasks: {done_count} done, {todo_count} remaining")
            # Show file changes
            success, changes = get_file_changes()
            typer.echo(f"Files: {changes}")

        # Check stop conditions after running
        exit_message = check_stop_conditions()
        if exit_message:
            typer.echo(f"\n{exit_message}")
            break

    typer.echo(f"\n{'=' * 60}")
    typer.echo("Loop completed")
    typer.echo(f"{'=' * 60}")

    # Git workflow teardown: push branch and create PR
    if cfg.git_workflow and created_branch:
        from wiggum.git import (
            GitError,
            create_pr,
            get_main_branch_name,
            push_branch,
        )

        typer.echo("\n--- Git Workflow Finalization ---")

        # Push the branch
        try:
            push_branch()
            typer.echo(f"Pushed branch: {created_branch}")
        except GitError as e:
            typer.echo(f"Error pushing branch: {e}", err=True)
            typer.echo("You may need to push manually and create the PR.")
            raise typer.Exit(1)

        # Create a PR
        try:
            base_branch = get_main_branch_name()
            pr_title = f"wiggum: automated changes from {created_branch}"
            pr_body = (
                "## Summary\n\n"
                "Automated changes made by wiggum loop.\n\n"
                f"See TASKS.md for completed tasks.\n\n"
                f"Branch: `{created_branch}`"
            )
            pr_url = create_pr(title=pr_title, body=pr_body, base=base_branch)
            typer.echo(f"Created PR: {pr_url}")
        except GitError as e:
            typer.echo(f"Error creating PR: {e}", err=True)
            typer.echo(f"Branch '{created_branch}' was pushed. Create PR manually.")


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
    templates_dir = resolve_templates_dir(templates_dir)
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

    typer.echo("Setting up wiggum...\n")

    # Read README for context if available
    readme_path = Path("README.md")
    readme_content = ""
    if readme_path.exists():
        readme_content = readme_path.read_text()
        typer.echo("Found README.md - using it for context.")

    # Agent-assisted planning (always)
    typer.echo("\nAnalyzing codebase and planning tasks...")
    meta_prompt = meta_prompt_path.read_text()
    if readme_content:
        meta_prompt = meta_prompt.replace(
            "{{goal}}", f"(Infer from README below)\n\n## README.md\n\n{readme_content}"
        )
    else:
        meta_prompt = meta_prompt.replace(
            "{{goal}}", "(No README found - analyze codebase)"
        )

    # Include existing tasks context if TASKS.md exists
    existing_tasks_context = get_existing_tasks_context(tasks_path)
    meta_prompt = meta_prompt.replace("{{existing_tasks}}", existing_tasks_context)

    output, error = run_claude_for_planning(meta_prompt)

    use_suggestions = False
    doc_files = "README.md, CLAUDE.md"
    tasks = []
    suggested_constraints = {}

    if error:
        typer.echo(error, err=True)
    elif output:
        config = parse_markdown_from_output(output)
        if config:
            suggested_tasks = config.get("tasks", [])
            suggested_constraints = config.get("constraints", {})

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
        typer.echo("Claude returned no output.")

    # Manual entry if suggestions not used
    if not use_suggestions:
        typer.echo("\nManual configuration:")
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
            security_yolo = True
        elif security_mode == "path_restricted":
            security_allow_paths = suggested_constraints.get("allow_paths", "")
        # else: conservative mode - no special permissions needed

    # Manual security selection if no constraints
    if not use_suggestions or not suggested_constraints:
        typer.echo("\nSecurity configuration:")
        typer.echo("  1) Conservative - ask permission for each action")
        typer.echo("  2) Path-restricted - allow writes to specific paths only")
        typer.echo("  3) YOLO - skip all permission prompts")

        security_choice = typer.prompt("Choose security mode [1/2/3]", default="3")

        if security_choice == "2":
            security_allow_paths = typer.prompt(
                "Enter paths to allow (comma-separated, e.g., 'src/,tests/')"
            )
        elif security_choice == "3":
            security_yolo = True

    # Git workflow configuration
    typer.echo("\nGit workflow configuration:")
    typer.echo("  When enabled, wiggum will:")
    typer.echo("    - Fetch and merge latest from main branch")
    typer.echo("    - Create a new branch for the loop")
    typer.echo("    - Create a PR when the loop completes")
    git_enabled = typer.confirm("Enable git workflow?", default=False)

    # Write config with security, loop, and git settings
    write_config(
        {
            "security": {
                "yolo": security_yolo,
                "allow_paths": security_allow_paths,
            },
            "loop": {
                "max_iterations": 10,
            },
            "git": {
                "enabled": git_enabled,
            },
        }
    )

    # Generate files from templates
    prompt_template = prompt_template_path.read_text()
    prompt_content = prompt_template.replace("{{doc_files}}", doc_files)

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
    typer.echo("\nRun the loop with: wiggum run")


def _run_identify_tasks(tasks_file: Path) -> None:
    """Analyze codebase and populate TASKS.md with identified tasks.

    Args:
        tasks_file: Path to the tasks file to populate.
    """
    templates_dir = resolve_templates_dir()
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
    output, error = run_claude_for_planning(meta_prompt)

    if error:
        typer.echo(error, err=True)
        return

    if not output:
        typer.echo("Claude returned no output.")
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


@app.command(name="list")
def list_tasks(
    tasks_file: Path = typer.Option(
        Path("TASKS.md"),
        "-f",
        "--tasks-file",
        help="Tasks file to read (default: TASKS.md)",
    ),
) -> None:
    """List tasks from TASKS.md."""
    task_list = get_all_tasks(tasks_file)

    if task_list is None:
        typer.echo(f"No tasks file found at {tasks_file}")
        raise typer.Exit(1)

    # Show todo tasks
    if task_list.todo:
        typer.echo("Todo:")
        for task in task_list.todo:
            typer.echo(f"  - [ ] {task}")
    else:
        typer.echo("Todo: (none)")

    # Show done tasks
    if task_list.done:
        typer.echo("\nDone:")
        for task in task_list.done:
            typer.echo(f"  - [x] {task}")


@app.command()
def suggest(
    tasks_file: Path = typer.Option(
        Path("TASKS.md"),
        "-f",
        "--tasks-file",
        help="Tasks file to add tasks to (default: TASKS.md)",
    ),
    accept_all: bool = typer.Option(
        False,
        "-y",
        "--yes",
        help="Accept all suggested tasks without prompting",
    ),
) -> None:
    """Interactively discover and add tasks using Claude's planning mode."""
    templates_dir = resolve_templates_dir()
    meta_prompt_path = templates_dir / "META-PROMPT.md"

    if not meta_prompt_path.exists():
        typer.echo(f"Error: Meta prompt not found: {meta_prompt_path}", err=True)
        raise typer.Exit(1)

    typer.echo("Analyzing codebase to suggest tasks...")

    # Build the meta-prompt
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
    output, error = run_claude_for_planning(meta_prompt)

    if error:
        typer.echo(error, err=True)
        raise typer.Exit(1)

    if not output:
        typer.echo("Claude returned no output.")
        raise typer.Exit(1)

    config = parse_markdown_from_output(output)
    if not config or not config.get("tasks"):
        typer.echo("No tasks suggested.")
        return

    suggested_tasks = config.get("tasks", [])

    # Get existing task descriptions to avoid duplicates
    existing_task_descs = get_existing_task_descriptions(tasks_file)

    # Filter out tasks that already exist
    new_tasks = [
        task for task in suggested_tasks if task.lower() not in existing_task_descs
    ]

    if not new_tasks:
        typer.echo("All suggested tasks already exist in TASKS.md.")
        return

    typer.echo(f"\nFound {len(new_tasks)} new task suggestion(s):\n")

    added_count = 0

    if accept_all:
        # Add all tasks without prompting
        for task in new_tasks:
            add_task_to_file(tasks_file, task)
            typer.echo(f"  + {task}")
            added_count += 1
    else:
        # Interactive mode: prompt for each task
        for task in new_tasks:
            typer.echo(f"  - {task}")
            if typer.confirm("    Add this task?", default=True):
                add_task_to_file(tasks_file, task)
                added_count += 1
                typer.echo("    Added.")
            else:
                typer.echo("    Skipped.")
            typer.echo()

    typer.echo(f"\nAdded {added_count} task(s) to {tasks_file}")


if __name__ == "__main__":
    app()
