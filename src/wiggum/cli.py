"""CLI interface for wiggum."""

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import typer


def _timestamp() -> str:
    """Return current time formatted as [HH:MM:SS]."""
    return datetime.now().strftime("[%H:%M:%S]")


from wiggum.agents import (
    AgentConfig,
    get_agent,
    get_available_agents,
)
from wiggum.config import (
    CONFIG_FILE,
    read_config,
    resolve_run_config,
    resolve_templates_dir,
    validate_config,
    write_config,
)
from wiggum.runner import (
    get_file_changes,
    run_claude_with_retry,
    write_log_entry,
)
from wiggum.changelog import (
    clear_done_tasks,
    format_changelog,
    merge_changelog,
    tasks_to_changelog_entries,
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


def tasks_file_option(
    short_flag: bool = True,
    help_text: str = "Tasks file (default: TASKS.md)",
    allow_none: bool = False,
) -> Any:
    """Factory for the tasks file option used across multiple commands.

    Args:
        short_flag: Whether to include -f as a short option.
        help_text: Custom help text for the option.
        allow_none: If True, default is None (for config fallback in run command).
                    If False, default is Path("TASKS.md").

    Returns:
        A typer.Option configured for tasks file selection.
    """
    flags = ["-f", "--tasks-file"] if short_flag else ["--tasks"]
    default = None if allow_none else Path("TASKS.md")
    return typer.Option(
        default,
        *flags,
        help=help_text,
    )


def _run_learning_consolidation(
    agent_name: Optional[str], yolo: bool, keep_diary: bool
) -> None:
    """Consolidate learning diary into CLAUDE.md if content exists."""
    from wiggum.learning import (
        clear_diary,
        consolidate_learnings,
        get_diary_line_count,
        has_diary_content,
    )

    if not has_diary_content():
        return

    # Confirm before consolidation (unless yolo mode)
    if not yolo:
        line_count = get_diary_line_count()
        typer.echo(f"\nDiary has {line_count} line(s) to consolidate into CLAUDE.md")
        if not typer.confirm("Proceed with consolidation?", default=True):
            typer.echo("Skipped consolidation. Diary preserved.")
            return

    typer.echo("\nConsolidating learnings...")
    success, reason = consolidate_learnings(agent_name, yolo)
    if success:
        typer.echo("Learnings added to CLAUDE.md")
        if not keep_diary:
            clear_diary()
    else:
        typer.echo(f"Warning: Failed to consolidate learnings: {reason}", err=True)


def _ensure_learning_diary_dir() -> None:
    """Ensure the learning diary directory exists (lazy import)."""
    from wiggum.learning import ensure_diary_dir

    ensure_diary_dir()


@app.command()
def run(
    prompt_file: Optional[Path] = typer.Option(
        None, "-f", "--file", help="Prompt file (default: LOOP-PROMPT.md)"
    ),
    tasks_file: Optional[Path] = tasks_file_option(
        short_flag=False,
        help_text="Tasks file for stop condition (stop when all tasks complete)",
        allow_none=True,
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
    create_pr: bool = typer.Option(
        False,
        "--pr",
        help="Create a PR after the loop completes",
    ),
    no_branch: bool = typer.Option(
        False,
        "--no-branch",
        help="Skip automatic branch creation (run on current branch)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Skip all git safety checks",
    ),
    branch_prefix: Optional[str] = typer.Option(
        None,
        "--branch-prefix",
        help="Prefix for auto-generated branch names (default: 'wiggum')",
    ),
    diary: bool = typer.Option(
        False,
        "--diary",
        help="Enable learning diary for this run (overrides config)",
    ),
    no_diary: bool = typer.Option(
        False,
        "--no-diary",
        help="Disable learning diary for this run",
    ),
    no_consolidate: bool = typer.Option(
        False,
        "--no-consolidate",
        help="Skip diary consolidation after run",
    ),
    keep_diary: bool = typer.Option(
        False,
        "--keep-diary",
        help="Keep diary file after consolidation (overrides config)",
    ),
    no_keep_diary: bool = typer.Option(
        False,
        "--no-keep-diary",
        help="Delete diary file after consolidation",
    ),
) -> None:
    """Run the agent loop. Stops when all tasks in TASKS.md are complete."""
    # Validate config file before resolving
    config = read_config()
    if config:
        validation = validate_config(config)
        # Show warnings
        for warning in validation.warnings:
            typer.echo(f"Warning: {warning}", err=True)
        # Show errors and exit
        if not validation.is_valid:
            for error in validation.errors:
                typer.echo(f"Error: {error}", err=True)
            raise typer.Exit(1)

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
            create_pr=create_pr,
            no_branch=no_branch,
            force=force,
            branch_prefix=branch_prefix,
            diary=diary,
            no_diary=no_diary,
            no_consolidate=no_consolidate,
            keep_diary_flag=keep_diary,
            no_keep_diary=no_keep_diary,
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
        if cfg.no_branch:
            typer.echo("Git safety: disabled (--no-branch)")
        elif cfg.force:
            typer.echo("Git safety: disabled (--force)")
        else:
            typer.echo("Git safety: enabled (will create branch in git repos)")
        if cfg.create_pr:
            typer.echo("PR creation: enabled (will create PR after loop)")
        typer.echo(f"Branch prefix: {cfg.branch_prefix}")
        typer.echo(f"Prompt:\n---\n{prompt}\n---")
        return

    # Validate agent CLI is available before running
    from wiggum.agents import check_cli_available, get_cli_error_message

    if not check_cli_available(agent_name):
        typer.echo(get_cli_error_message(agent_name), err=True)
        raise typer.Exit(1)

    # Git safety: check repo status and create branch
    created_branch = None
    from wiggum.git import (
        GitError,
        commit_all,
        create_branch,
        generate_branch_name,
        is_git_repo,
        is_on_wiggum_branch,
        is_working_directory_clean,
        stash_changes,
    )

    in_git_repo = is_git_repo()

    # Handle non-git-repo case
    if not in_git_repo:
        if not cfg.force:
            typer.echo("Warning: Not a git repository. Changes cannot be undone.")
            if not typer.confirm("Continue without git safety?", default=False):
                raise typer.Exit(0)
    else:
        # In a git repo - apply safety checks unless --force or --no-branch
        if not cfg.force and not cfg.no_branch:
            # Check for uncommitted changes
            if not is_working_directory_clean():
                typer.echo("\nYou have uncommitted changes.")
                typer.echo("What would you like to do?")
                typer.echo("  [S]tash - Stash changes and continue")
                typer.echo("  [C]ommit - Commit changes with a message")
                typer.echo("  [A]bort - Exit without running")

                choice = typer.prompt("Choice [S/C/A]", default="A").upper()

                if choice == "S":
                    try:
                        stash_changes("wiggum: auto-stash before loop")
                        typer.echo("Changes stashed. Run `git stash pop` to restore.")
                    except GitError as e:
                        typer.echo(f"Error stashing changes: {e}", err=True)
                        raise typer.Exit(1)
                elif choice == "C":
                    message = typer.prompt(
                        "Commit message", default="WIP: checkpoint before wiggum loop"
                    )
                    try:
                        commit_all(message)
                        typer.echo(f"Changes committed: {message}")
                    except GitError as e:
                        typer.echo(f"Error committing changes: {e}", err=True)
                        raise typer.Exit(1)
                else:
                    typer.echo("Aborted.")
                    raise typer.Exit(0)

            # Create branch (unless already on a wiggum branch)
            if is_on_wiggum_branch(cfg.branch_prefix):
                typer.echo("Already on a wiggum branch, continuing...")
            else:
                created_branch = generate_branch_name(cfg.branch_prefix)
                try:
                    create_branch(created_branch)
                    typer.echo(f"Created branch: {created_branch}")
                except GitError as e:
                    typer.echo(f"Error creating branch: {e}", err=True)
                    raise typer.Exit(1)

    # Validate gh CLI if PR creation is requested
    if cfg.create_pr:
        if not in_git_repo:
            typer.echo("Error: --pr requires a git repository", err=True)
            raise typer.Exit(1)
        if not check_cli_available("gh"):
            typer.echo(get_cli_error_message("gh"), err=True)
            raise typer.Exit(1)

    # Ensure diary directory exists if learning is enabled
    if cfg.learning_enabled:
        _ensure_learning_diary_dir()

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

        # Debug output before agent starts
        if cfg.show_progress:
            typer.echo(f"{_timestamp()} Running {agent_name} agent...")

        start_time = time.time()
        result = agent_instance.run(agent_config)
        elapsed = time.time() - start_time

        # Debug output after agent completes
        if cfg.show_progress:
            if elapsed >= 60:
                elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
            else:
                elapsed_str = f"{elapsed:.1f}s"
            typer.echo(f"{_timestamp()} Agent completed ({elapsed_str})")
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
            _, changes = get_file_changes()
            typer.echo(f"Files: {changes}")

        # Check stop conditions after running
        exit_message = check_stop_conditions()
        if exit_message:
            typer.echo(f"\n{exit_message}")
            break

    typer.echo(f"\n{'=' * 60}")
    typer.echo("Loop completed")
    typer.echo(f"{'=' * 60}")

    # Learning consolidation
    if cfg.learning_enabled and cfg.auto_consolidate:
        _run_learning_consolidation(cfg.agent, cfg.yolo, cfg.keep_diary)

    # Show git summary and handle PR creation
    if in_git_repo and created_branch:
        from wiggum.git import (
            commit_all,
            create_pr as git_create_pr,
            get_current_branch,
            get_main_branch_name,
            has_remote,
            is_working_directory_clean,
            push_branch,
        )

        current = get_current_branch()
        typer.echo(f"\nChanges are on branch: {current}")

        if cfg.create_pr:
            # Commit, push, and create PR
            typer.echo("\n--- Creating PR ---")
            try:
                # Commit any changes made during the loop
                if not is_working_directory_clean():
                    commit_all(f"wiggum: automated changes from {current}")
                    typer.echo("Committed changes")

                if has_remote():
                    push_branch()
                    typer.echo(f"Pushed branch: {current}")

                    base_branch = get_main_branch_name()
                    pr_title = f"wiggum: automated changes from {current}"
                    pr_body = (
                        "## Summary\n\n"
                        "Automated changes made by wiggum loop.\n\n"
                        f"See TASKS.md for completed tasks.\n\n"
                        f"Branch: `{current}`"
                    )
                    pr_url = git_create_pr(
                        title=pr_title, body=pr_body, base=base_branch
                    )
                    typer.echo(f"Created PR: {pr_url}")
                else:
                    typer.echo("No remote configured. Cannot create PR.")
            except GitError as e:
                typer.echo(f"Error: {e}", err=True)
                typer.echo("You may need to push and create PR manually.")
        else:
            # Show next steps
            typer.echo("\nNext steps:")
            typer.echo("  Create PR:  gh pr create")
            typer.echo(f"  Merge:      git checkout main && git merge {current}")
            typer.echo(f"  Discard:    git checkout main && git branch -D {current}")


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

    config, error = run_claude_with_retry(meta_prompt)

    use_suggestions = False
    doc_files = "README.md, CLAUDE.md"
    tasks = []
    suggested_constraints = {}

    if error:
        typer.echo(error, err=True)
    elif config:
        suggested_tasks = config.get("tasks", [])
        suggested_constraints = config.get("constraints", {})

        typer.echo("\nSuggested tasks:")
        for task_desc in suggested_tasks:
            typer.echo(f"  - {task_desc}")

        # Show suggested constraints if present
        if suggested_constraints:
            typer.echo("\nSuggested security constraints:")
            security_mode = suggested_constraints.get("security_mode", "conservative")
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

    # Add wiggum files to .gitignore
    gitignore_path = Path(".gitignore")
    wiggum_entries = [".wiggum/", "LOOP-PROMPT.md", "TASKS.md", ".wiggum.toml"]
    gitignore_content = gitignore_path.read_text() if gitignore_path.exists() else ""
    missing = [e for e in wiggum_entries if e not in gitignore_content]
    if missing:
        section = "\n# wiggum\n" + "\n".join(missing) + "\n"
        gitignore_path.write_text(gitignore_content.rstrip() + section)
        typer.echo("Updated .gitignore with wiggum files")

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

    # Run Claude for planning with retry
    config, error = run_claude_with_retry(meta_prompt)

    if error:
        typer.echo(error, err=True)
        return

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
    tasks_file: Path = tasks_file_option(
        help_text="Tasks file to add to (default: TASKS.md)"
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
    tasks_file: Path = tasks_file_option(
        help_text="Tasks file to read (default: TASKS.md)"
    ),
) -> None:
    """List tasks from TASKS.md."""
    task_list = get_all_tasks(tasks_file)

    if task_list is None:
        typer.echo(f"No tasks file found at {tasks_file}", err=True)
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
    tasks_file: Path = tasks_file_option(
        help_text="Tasks file to add tasks to (default: TASKS.md)"
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

    # Run Claude for planning with retry
    config, error = run_claude_with_retry(meta_prompt)

    if error:
        typer.echo(error, err=True)
        raise typer.Exit(1)

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


@app.command()
def spec(
    name: str = typer.Argument(..., help="Name of the spec (e.g., 'user-auth')"),
    specs_dir: Path = typer.Option(
        Path("specs"),
        "-d",
        "--dir",
        help="Directory for spec files (default: specs/)",
    ),
    force: bool = typer.Option(
        False, "-f", "--force", help="Overwrite existing spec file"
    ),
    templates_dir: Optional[Path] = typer.Option(
        None,
        "--templates",
        "-t",
        help="Templates directory (default: package templates)",
    ),
) -> None:
    """Create a new spec file from template.

    Spec files are detailed design documents for complex features or changes.
    Tasks in TASKS.md can reference specs like: `- [ ] Implement feature (see specs/feature.md)`

    The spec template includes sections for overview, requirements, implementation details,
    and test plan. Edit the generated file to fill in the specifics of your feature.
    """
    templates_dir = resolve_templates_dir(templates_dir)
    spec_template_path = templates_dir / "SPEC.md"

    if not spec_template_path.exists():
        typer.echo(f"Error: Spec template not found: {spec_template_path}", err=True)
        raise typer.Exit(1)

    # Create specs directory if it doesn't exist
    specs_dir.mkdir(parents=True, exist_ok=True)

    # Generate spec filename
    spec_file = specs_dir / f"{name}.md"

    if spec_file.exists() and not force:
        typer.echo(
            f"Error: {spec_file} already exists. Use --force to overwrite.", err=True
        )
        raise typer.Exit(1)

    # Read template and replace placeholders
    template_content = spec_template_path.read_text()
    # Convert name to title case for display (user-auth -> User Auth)
    display_name = name.replace("-", " ").replace("_", " ").title()
    spec_content = template_content.replace("{{name}}", display_name)

    spec_file.write_text(spec_content)
    typer.echo(f"Created {spec_file}")
    typer.echo("\nTo link this spec to a task, add to TASKS.md:")
    typer.echo(f"  - [ ] Implement {display_name} (see {spec_file})")


@app.command()
def upgrade(
    target: Optional[str] = typer.Argument(
        None,
        help="File to upgrade: 'prompt', 'config', 'tasks', or omit for all",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would change without modifying files",
    ),
    force: bool = typer.Option(
        False,
        "-f",
        "--force",
        help="Skip confirmation prompt",
    ),
    no_backup: bool = typer.Option(
        False,
        "--no-backup",
        help="Don't create .bak file for LOOP-PROMPT.md",
    ),
    templates_dir: Optional[Path] = typer.Option(
        None,
        "--templates",
        "-t",
        help="Templates directory (default: package templates)",
    ),
) -> None:
    """Upgrade wiggum-managed files to the latest version.

    Upgrades LOOP-PROMPT.md, .wiggum.toml, and TASKS.md structure.

    Examples:
        wiggum upgrade           # Check and upgrade all files
        wiggum upgrade prompt    # Only upgrade LOOP-PROMPT.md
        wiggum upgrade config    # Only upgrade .wiggum.toml
        wiggum upgrade tasks     # Only upgrade TASKS.md structure
    """
    import tomli_w

    from wiggum import __version__ as current_version
    from wiggum.upgrade import (
        add_missing_task_sections,
        extract_template_version,
        get_missing_config_options,
        get_next_backup_path,
        is_version_outdated,
        merge_config_with_defaults,
        tasks_file_needs_upgrade,
    )

    # Validate target
    valid_targets = {"prompt", "config", "tasks", None}
    if target not in valid_targets:
        typer.echo(
            f"Unknown target: '{target}'. Use 'prompt', 'config', or 'tasks'.",
            err=True,
        )
        raise typer.Exit(1)

    templates_dir = resolve_templates_dir(templates_dir)
    prompt_template_path = templates_dir / "LOOP-PROMPT.md"

    prompt_path = Path("LOOP-PROMPT.md")
    config_path = Path(CONFIG_FILE)
    tasks_path = Path("TASKS.md")

    # Determine which files to upgrade
    upgrade_prompt = target is None or target == "prompt"
    upgrade_config = target is None or target == "config"
    upgrade_tasks = target is None or target == "tasks"

    # Check if any managed files exist
    any_exists = prompt_path.exists() or config_path.exists() or tasks_path.exists()
    if not any_exists:
        typer.echo("No wiggum files found. Run 'wiggum init' first.", err=True)
        raise typer.Exit(1)

    # Read files once
    prompt_content = prompt_path.read_text() if prompt_path.exists() else None
    tasks_content = tasks_path.read_text() if tasks_path.exists() else None
    existing_config = read_config() if config_path.exists() else {}

    # Collect changes
    changes = []

    # Check LOOP-PROMPT.md
    prompt_outdated = False
    if upgrade_prompt and prompt_content is not None:
        prompt_current_version = extract_template_version(prompt_content)
        prompt_outdated = is_version_outdated(prompt_current_version, current_version)
        if prompt_outdated:
            version_info = prompt_current_version or "no version tag"
            changes.append(f"LOOP-PROMPT.md: {version_info} → {current_version}")

    # Check .wiggum.toml
    missing_options = []
    if upgrade_config and existing_config:
        missing_options = get_missing_config_options(existing_config)
        if missing_options:
            changes.append(
                f".wiggum.toml: {len(missing_options)} new option(s) available"
            )
            for section, key, default in missing_options:
                changes.append(f"  - [{section}] {key} = {repr(default)}")

    # Check TASKS.md
    tasks_outdated = False
    if upgrade_tasks and tasks_content is not None:
        tasks_outdated = tasks_file_needs_upgrade(tasks_content)
        if tasks_outdated:
            changes.append("TASKS.md: missing required sections")

    # Show status
    typer.echo("Checking wiggum files...\n")

    if not changes:
        typer.echo("All files are up to date.")
        return

    for change in changes:
        typer.echo(change)
    typer.echo()

    # Handle dry-run
    if dry_run:
        return

    # Confirm upgrade
    if not force:
        if not typer.confirm("Upgrade?", default=False):
            typer.echo("Aborted.")
            return

    # Apply upgrades
    if upgrade_prompt and prompt_outdated and prompt_content is not None:
        # Backup current file
        if not no_backup:
            backup_path = get_next_backup_path(prompt_path)
            backup_path.write_text(prompt_content)
            typer.echo(f"✓ Backed up LOOP-PROMPT.md → {backup_path.name}")

        # Write new template
        template_content = prompt_template_path.read_text()
        prompt_path.write_text(template_content)
        typer.echo(f"✓ LOOP-PROMPT.md upgraded to {current_version}")

    if upgrade_config and missing_options:
        merged = merge_config_with_defaults(existing_config)
        config_path.write_text(tomli_w.dumps(merged))
        typer.echo("✓ .wiggum.toml updated with new options")

    if upgrade_tasks and tasks_outdated and tasks_content is not None:
        upgraded_content = add_missing_task_sections(tasks_content)
        tasks_path.write_text(upgraded_content)
        typer.echo("✓ TASKS.md structure updated")


# Files managed by wiggum that can be cleaned
MANAGED_CONFIG_FILES = ["LOOP-PROMPT.md", ".wiggum.toml"]
TASKS_FILE = "TASKS.md"


@app.command()
def clean(
    all_files: bool = typer.Option(
        False,
        "--all",
        help="Also remove TASKS.md",
    ),
    keep_tasks: bool = typer.Option(
        False,
        "--keep-tasks",
        help="Explicitly keep TASKS.md (no prompt)",
    ),
    force: bool = typer.Option(
        False,
        "-f",
        "--force",
        help="Skip confirmation prompts",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be removed without deleting",
    ),
) -> None:
    """Remove wiggum-managed files from the current directory.

    By default, removes LOOP-PROMPT.md and .wiggum.toml.
    TASKS.md is kept by default (prompts unless --keep-tasks or --all).

    Examples:
        wiggum clean              # Interactive removal
        wiggum clean --keep-tasks # Remove config, keep tasks
        wiggum clean --all        # Remove everything including TASKS.md
        wiggum clean --dry-run    # Preview what would be removed
    """
    # Check for conflicting flags
    if all_files and keep_tasks:
        typer.echo("Error: Cannot use --all and --keep-tasks together.", err=True)
        raise typer.Exit(1)

    # Find existing config files
    config_files_to_remove = [f for f in MANAGED_CONFIG_FILES if Path(f).exists()]
    tasks_exists = Path(TASKS_FILE).exists()

    # Determine what to remove
    files_to_remove = config_files_to_remove.copy()
    remove_tasks = False

    if tasks_exists:
        if all_files:
            # --all: remove tasks without asking
            files_to_remove.append(TASKS_FILE)
            remove_tasks = True
        elif keep_tasks:
            # --keep-tasks: explicitly keep tasks
            remove_tasks = False
        elif not force and not dry_run:
            # Interactive: ask about TASKS.md
            typer.echo(
                "TASKS.md contains your task list. Remove it too? [y/N] ", nl=False
            )
            response = typer.prompt("", default="n", show_default=False).lower()
            if response == "y":
                files_to_remove.append(TASKS_FILE)
                remove_tasks = True

    # Check if there's anything to clean
    if not files_to_remove and (not tasks_exists or keep_tasks or not all_files):
        typer.echo("No wiggum files found in current directory.")
        return

    # Handle dry-run
    if dry_run:
        if files_to_remove:
            typer.echo("Would remove:")
            for f in files_to_remove:
                typer.echo(f"  - {f}")
        if tasks_exists and not remove_tasks:
            typer.echo("Would keep:")
            typer.echo(f"  - {TASKS_FILE} (use --all to remove)")
        return

    # If only tasks exist and we're not removing them
    if not config_files_to_remove and tasks_exists and not remove_tasks:
        typer.echo("No wiggum files found in current directory.")
        return

    # Confirm removal
    if not force:
        typer.echo("This will remove wiggum configuration files:")
        for f in files_to_remove:
            typer.echo(f"  - {f}")
        typer.echo()
        if not typer.confirm("Remove these files?", default=False):
            typer.echo("Aborted.")
            return

    # Remove files
    for f in files_to_remove:
        try:
            Path(f).unlink()
            typer.echo(f"✓ Removed {f}")
        except OSError as e:
            typer.echo(f"Error removing {f}: {e}", err=True)

    # Show status of tasks file
    if tasks_exists and not remove_tasks:
        if force:
            typer.echo(f"  Kept {TASKS_FILE} (use --all to include)")
        else:
            typer.echo(f"  Kept {TASKS_FILE}")


@app.command()
def prune(
    tasks_file: Path = tasks_file_option(
        help_text="Tasks file to prune (default: TASKS.md)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview without removing",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Skip confirmation",
    ),
) -> None:
    """Remove completed tasks from TASKS.md."""
    task_list = get_all_tasks(tasks_file)

    if task_list is None:
        typer.echo(f"No tasks file found at {tasks_file}", err=True)
        raise typer.Exit(1)

    if not task_list.done:
        typer.echo("No completed tasks to remove.")
        return

    count = len(task_list.done)

    if dry_run:
        typer.echo(f"Would remove {count} completed task(s):")
        for task in task_list.done:
            typer.echo(f"  - [x] {task}")
        return

    if not force:
        if not typer.confirm(f"Remove {count} completed task(s)?", default=False):
            typer.echo("Aborted.")
            return

    clear_done_tasks(tasks_file)
    typer.echo(f"Removed {count} completed task(s)")


@app.command()
def changelog(
    version: Optional[str] = typer.Option(
        None,
        "-v",
        "--version",
        help="Version string (default: 'Unreleased')",
    ),
    output: Path = typer.Option(
        Path("CHANGELOG.md"),
        "-o",
        "--output",
        help="Output file (default: CHANGELOG.md)",
    ),
    tasks_file: Path = tasks_file_option(
        help_text="Tasks file to read (default: TASKS.md)"
    ),
    append: bool = typer.Option(
        False,
        "--append",
        help="Append to existing changelog instead of overwriting",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview output without writing file",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Skip confirmation prompt",
    ),
    clear_done: bool = typer.Option(
        False,
        "--clear-done",
        help="Clear Done section in TASKS.md after generating changelog",
    ),
) -> None:
    """Generate CHANGELOG.md from completed tasks in TASKS.md.

    Reads completed tasks from TASKS.md, categorizes them based on their
    description prefixes (Add/Fix/Update/Remove), and generates a changelog
    following the Keep a Changelog format.

    Examples:
        wiggum changelog                    # All done tasks as "Unreleased"
        wiggum changelog --version 0.8.0    # Create versioned release section
        wiggum changelog --dry-run          # Preview output
        wiggum changelog --append           # Add to existing changelog
        wiggum changelog --clear-done       # Clear Done section after generating
    """
    # Get completed tasks
    task_list = get_all_tasks(tasks_file)

    if task_list is None:
        typer.echo(f"No tasks file found at {tasks_file}", err=True)
        raise typer.Exit(1)

    if not task_list.done:
        typer.echo("No completed tasks found in Done section.")
        raise typer.Exit(0)

    # Categorize tasks
    entries = tasks_to_changelog_entries(task_list.done)

    # Determine version string
    version_str = version or "Unreleased"

    # Generate or merge changelog
    if append and output.exists():
        existing_content = output.read_text()
        changelog_content = merge_changelog(
            existing_content, entries, version=version_str
        )
    else:
        changelog_content = format_changelog(entries, version=version_str)

    # Handle dry-run
    if dry_run:
        typer.echo("Preview:\n")
        typer.echo(changelog_content)
        return

    # Confirm unless --force
    if not force and output.exists() and not append:
        typer.echo(f"This will overwrite {output}.")
        if not typer.confirm("Continue?", default=False):
            typer.echo("Aborted.")
            return

    # Write changelog
    output.write_text(changelog_content)
    typer.echo(f"✓ Generated {output}")

    # Show summary
    task_count = len(task_list.done)
    category_counts = ", ".join(
        f"{len(v)} {k.lower()}" for k, v in entries.items() if v
    )
    typer.echo(f"  {task_count} task(s): {category_counts}")

    # Clear done tasks if requested
    if clear_done:
        clear_done_tasks(tasks_file)
        typer.echo(f"✓ Cleared Done section in {tasks_file}")


if __name__ == "__main__":
    app()
