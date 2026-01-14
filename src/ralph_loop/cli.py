"""CLI interface for ralph-loop."""

import subprocess
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(help="Ralph Wiggum loop for agents")

CONFIG_FILE = ".ralph-loop.toml"


def read_config() -> dict:
    """Read configuration from .ralph-loop.toml.

    Returns:
        Configuration dict with 'security' section containing 'yolo' and 'allow_paths'.
        Returns empty dict if file doesn't exist.
    """
    config_path = Path(CONFIG_FILE)
    if not config_path.exists():
        return {}

    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        return tomllib.loads(config_path.read_text())
    except Exception:
        return {}


def write_config(config: dict) -> None:
    """Write configuration to .ralph-loop.toml.

    Args:
        config: Configuration dict to write.
    """
    config_path = Path(CONFIG_FILE)

    # Build TOML content manually (simple format)
    lines = []
    if "security" in config:
        lines.append("[security]")
        security = config["security"]
        if "yolo" in security:
            lines.append(f"yolo = {'true' if security['yolo'] else 'false'}")
        if "allow_paths" in security:
            lines.append(f'allow_paths = "{security["allow_paths"]}"')

    config_path.write_text("\n".join(lines) + "\n")


def get_templates_dir() -> Path:
    """Get the templates directory from the package."""
    import importlib.resources

    return Path(importlib.resources.files("ralph_loop").joinpath("../../../templates"))


def parse_stop_condition(value: str) -> tuple[str, Optional[Path]]:
    """Parse stop condition value.

    Args:
        value: Stop condition string like 'tasks', 'file:/path/to/file', or 'none'

    Returns:
        Tuple of (condition_type, file_path) where condition_type is 'tasks', 'file', or 'none'
        and file_path is the path for file conditions (None otherwise).

    Raises:
        ValueError: If the value is invalid.
    """
    value = value.strip()
    if value == "tasks":
        return ("tasks", None)
    elif value == "none":
        return ("none", None)
    elif value.startswith("file:"):
        file_path = value[5:].strip()
        if not file_path:
            raise ValueError("file: condition requires a path (e.g., file:DONE.md)")
        return ("file", Path(file_path))
    else:
        raise ValueError(
            f"Invalid stop condition: '{value}'. Use 'tasks', 'none', or 'file:<path>'"
        )


@app.command()
def run(
    prompt_file: Optional[Path] = typer.Option(
        None, "-f", "--file", help="Prompt file (default: LOOP-PROMPT.md)"
    ),
    tasks_file: Path = typer.Option(
        Path("TASKS.md"), "--tasks", help="Tasks file to check for completion"
    ),
    stop_file: Optional[Path] = typer.Option(
        None,
        "--stop-file",
        help="Exit when this file exists (legacy, prefer --stop-condition)",
    ),
    stop_condition: Optional[str] = typer.Option(
        None,
        "--stop-condition",
        help="Stop condition: 'tasks' (default), 'file:<path>', or 'none'",
    ),
    max_iterations: int = typer.Option(
        10, "-n", "--max-iterations", help="Max iterations"
    ),
    yolo: bool = typer.Option(
        False,
        "--yolo",
        help="Skip all permission prompts (passes --dangerously-skip-permissions to claude)",
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
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would run"),
    log_file: Optional[Path] = typer.Option(
        None, "--log-file", help="Log each iteration's output to this file"
    ),
    show_progress: bool = typer.Option(
        False,
        "--show-progress",
        help="Show file changes (via git status) after each iteration",
    ),
) -> None:
    """Run the agent loop. Stops when all tasks in TASKS.md are complete."""
    # Read config file and apply settings (CLI flags override config)
    config = read_config()
    security_config = config.get("security", {})

    # Apply config values if CLI flags not explicitly set
    if not yolo and security_config.get("yolo", False):
        yolo = True
    if allow_paths is None and security_config.get("allow_paths"):
        allow_paths = security_config.get("allow_paths")

    # Check for mutually exclusive flags
    if continue_session and reset_session:
        typer.echo(
            "Error: --continue and --reset are mutually exclusive. Cannot use both.",
            err=True,
        )
        raise typer.Exit(1)

    # Parse and determine effective stop condition
    condition_type = "tasks"  # Default
    effective_stop_file: Optional[Path] = stop_file  # For backwards compatibility

    if stop_condition is not None:
        try:
            condition_type, parsed_file = parse_stop_condition(stop_condition)
            if condition_type == "file":
                effective_stop_file = parsed_file
        except ValueError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)

    # Determine prompt source - always from file
    if prompt_file is None:
        prompt_file = Path("LOOP-PROMPT.md")
    if not prompt_file.exists():
        typer.echo(f"Error: Prompt file '{prompt_file}' not found", err=True)
        raise typer.Exit(1)
    prompt = prompt_file.read_text()

    if dry_run:
        cmd = ["claude", "--print", "-p", "<prompt>"]
        if yolo:
            cmd.append("--dangerously-skip-permissions")
        if allow_paths:
            for path in allow_paths.split(","):
                cmd.extend(["--allowedTools", f"Edit:{path.strip()}*"])
                cmd.extend(["--allowedTools", f"Write:{path.strip()}*"])
        typer.echo(f"Would run {max_iterations} iterations")
        typer.echo(f"Command: {' '.join(cmd)}")
        # Show stop condition
        if condition_type == "tasks":
            typer.echo(f"Stop condition: tasks (check {tasks_file})")
        elif condition_type == "file":
            typer.echo(f"Stop condition: file ({effective_stop_file})")
        elif condition_type == "none":
            typer.echo("Stop condition: none (only iteration limit)")
        # Legacy: also show if --stop-file was explicitly provided
        if stop_file and stop_condition is None:
            typer.echo(f"Stop file: {stop_file}")
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
        if condition_type == "none":
            return None  # Only iteration limit applies
        if condition_type == "file" or effective_stop_file:
            if file_exists_check(effective_stop_file):
                return f"Stop file '{effective_stop_file}' exists. Exiting."
        if condition_type == "tasks":
            if not tasks_remaining(tasks_file):
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

        # Run claude
        cmd = ["claude", "--print", "-p", prompt]
        # After first iteration, continue session if requested
        if continue_session and i > 1:
            cmd.append("-c")
        if yolo:
            cmd.append("--dangerously-skip-permissions")
        if allow_paths:
            for path in allow_paths.split(","):
                cmd.extend(["--allowedTools", f"Edit:{path.strip()}*"])
                cmd.extend(["--allowedTools", f"Write:{path.strip()}*"])
        try:
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            # Print output to console
            if result.stdout:
                typer.echo(result.stdout)
            if result.stderr:
                typer.echo(result.stderr, err=True)
            # Log output to file if requested
            if log_file:
                write_log_entry(log_file, i, result.stdout or "")
            # Show file changes if requested
            if show_progress:
                success, changes = get_file_changes()
                typer.echo("\n--- File Changes ---")
                typer.echo(changes)
        except FileNotFoundError:
            typer.echo(
                "Error: 'claude' command not found. Is Claude Code installed?", err=True
            )
            raise typer.Exit(1)

        # Check stop conditions after running
        exit_message = check_stop_conditions()
        if exit_message:
            typer.echo(f"\n{exit_message}")
            break

    typer.echo(f"\n{'=' * 60}")
    typer.echo("Loop completed")
    typer.echo(f"{'=' * 60}")


def tasks_remaining(tasks_file: Path = Path("TASKS.md")) -> bool:
    """Check if there are incomplete tasks in TASKS.md."""
    if not tasks_file.exists():
        return True  # No tasks file means we don't know, keep running

    content = tasks_file.read_text()
    # Count unchecked boxes in Todo section
    import re

    # Find unchecked tasks: - [ ]
    unchecked = re.findall(r"^- \[ \]", content, re.MULTILINE)
    return len(unchecked) > 0


def get_current_task(tasks_file: Path = Path("TASKS.md")) -> Optional[str]:
    """Get the first incomplete task from TASKS.md.

    Args:
        tasks_file: Path to the tasks file.

    Returns:
        The task description (without the checkbox), or None if no tasks remain.
    """
    if not tasks_file.exists():
        return None

    content = tasks_file.read_text()
    if not content:
        return None

    import re

    # Find first unchecked task: - [ ] task description
    match = re.search(r"^- \[ \] (.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def file_exists_check(stop_file: Optional[Path]) -> bool:
    """Check if the stop file exists.

    Args:
        stop_file: Path to check, or None if no stop file is configured.

    Returns:
        True if stop_file is set and exists, False otherwise.
    """
    if stop_file is None:
        return False
    return stop_file.exists()


def get_file_changes() -> tuple[bool, str]:
    """Get file changes using git status.

    Returns:
        A tuple of (success, message) where success is True if git status ran,
        and message is either the formatted file changes or an error message.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False, "Not a git repository - progress tracking unavailable"

        if not result.stdout.strip():
            return True, "No file changes"

        # Parse git status output
        modified = []
        new_files = []
        deleted = []
        other = []

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            status = line[:2]
            filename = line[3:]

            if "M" in status:
                modified.append(filename)
            elif status == "??":
                new_files.append(filename)
            elif "D" in status:
                deleted.append(filename)
            elif "A" in status:
                new_files.append(filename)
            else:
                other.append(filename)

        # Build output message
        parts = []
        if modified:
            parts.append(f"Modified: {', '.join(modified)}")
        if new_files:
            parts.append(f"New: {', '.join(new_files)}")
        if deleted:
            parts.append(f"Deleted: {', '.join(deleted)}")
        if other:
            parts.append(f"Other: {', '.join(other)}")

        return True, "\n".join(parts) if parts else "No file changes"
    except FileNotFoundError:
        return False, "Git not found - progress tracking unavailable"


def write_log_entry(log_file: Path, iteration: int, output: str) -> None:
    """Write a log entry to the specified log file.

    Args:
        log_file: Path to the log file.
        iteration: The iteration number.
        output: The output from claude to log.
    """
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    separator = "=" * 60
    log_entry = (
        f"\n{separator}\nIteration {iteration} - {timestamp}\n{separator}\n{output}\n"
    )

    with open(log_file, "a") as f:
        f.write(log_entry)


def run_claude_for_planning(meta_prompt: str) -> Optional[str]:
    """Run Claude with meta prompt and return output."""
    try:
        result = subprocess.run(
            ["claude", "--print", "-p", meta_prompt],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout
    except FileNotFoundError:
        return None


def parse_toml_from_output(output: str) -> Optional[dict]:
    """Extract and parse TOML block from Claude output."""
    import re

    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    # Find TOML block in output
    match = re.search(r"```toml\s*(.*?)\s*```", output, re.DOTALL)
    if match:
        try:
            return tomllib.loads(match.group(1))
        except Exception:
            return None
    return None


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

    # Check for existing files
    if not force:
        if prompt_path.exists():
            typer.echo(
                f"Error: {prompt_path} already exists. Use --force to overwrite.",
                err=True,
            )
            raise typer.Exit(1)
        if tasks_path.exists():
            typer.echo(
                f"Error: {tasks_path} already exists. Use --force to overwrite.",
                err=True,
            )
            raise typer.Exit(1)

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
    output = run_claude_for_planning(meta_prompt)

    use_suggestions = False
    doc_files = "README.md, CLAUDE.md"
    tasks = []

    if output:
        config = parse_toml_from_output(output)
        if config:
            # Get goal from Claude if we inferred from README
            if not goal:
                goal = config.get("project", {}).get("goal", "")
            doc_files = config.get("project", {}).get("doc_files", doc_files)
            suggested_tasks = config.get("tasks", [])

            typer.echo("\nSuggested configuration:")
            typer.echo(f"  Goal: {goal}")
            typer.echo(f"  Doc files: {doc_files}")
            typer.echo("\nSuggested tasks:")
            for t in suggested_tasks:
                typer.echo(f"  - {t.get('description', '')}")

            if typer.confirm("\nUse these suggestions?", default=True):
                tasks = [f"- [ ] {t.get('description', '')}" for t in suggested_tasks]
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

    # Ask about security constraints
    security_yolo = False
    security_allow_paths = ""

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
        typer.echo("This is dangerous and should only be used for trusted projects.")
        if typer.confirm("Are you sure you want to enable YOLO mode?", default=False):
            security_yolo = True
        else:
            # User cancelled, ask again
            typer.echo("\nYOLO mode cancelled. Choosing a different mode:")
            security_choice = typer.prompt("Choose security mode [1/2]", default="1")
            if security_choice == "2":
                security_allow_paths = typer.prompt(
                    "Enter paths to allow (comma-separated, e.g., 'src/,tests/')"
                )

    # Write security config
    write_config(
        {
            "security": {
                "yolo": security_yolo,
                "allow_paths": security_allow_paths,
            }
        }
    )

    # Generate files from templates
    prompt_template = prompt_template_path.read_text()
    prompt_content = prompt_template.replace("{{goal}}", goal).replace(
        "{{doc_files}}", doc_files
    )

    tasks_template = (
        tasks_template_path.read_text()
        if tasks_template_path.exists()
        else "# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n{{tasks}}\n"
    )
    tasks_content = tasks_template.replace(
        "{{tasks}}", "\n".join(tasks) if tasks else "- [ ] (add your first task here)"
    )

    prompt_path.write_text(prompt_content)
    tasks_path.write_text(tasks_content)

    typer.echo(f"\nCreated {prompt_path}, {tasks_path}, and {CONFIG_FILE}")
    typer.echo("\nRun the loop with: ralph-loop run")


def add_task_to_file(tasks_file: Path, task_description: str) -> None:
    """Add a task to the tasks file.

    Args:
        tasks_file: Path to the tasks file.
        task_description: The task description to add.

    This function handles:
    - Creating the file with proper structure if it doesn't exist
    - Appending to the ## Todo section if it exists
    - Adding a ## Todo section if missing
    """
    task_line = f"- [ ] {task_description}\n"

    if not tasks_file.exists():
        # Create new file with standard structure
        content = f"# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n{task_line}"
        tasks_file.write_text(content)
        return

    content = tasks_file.read_text()

    # Check if ## Todo section exists
    if "## Todo" in content:
        # Find the end of the Todo section content and append there
        # The Todo section ends at EOF or at the next ## header
        import re

        # Find ## Todo and append after its content
        todo_match = re.search(r"(## Todo\n+)(.*?)(\n## |\Z)", content, re.DOTALL)
        if todo_match:
            # Insert new task at end of Todo section content
            start = todo_match.start(2) + len(todo_match.group(2))
            # Ensure there's a newline before the task if content exists
            if todo_match.group(2).strip():
                # There's existing content, append with newline
                new_content = (
                    content[:start].rstrip("\n")
                    + "\n"
                    + task_line
                    + content[start:].lstrip("\n")
                )
            else:
                # Empty Todo section, just add the task
                new_content = (
                    content[: todo_match.end(1)]
                    + task_line
                    + content[todo_match.start(3) :]
                )
            tasks_file.write_text(new_content)
        else:
            # Fallback: append to end
            if not content.endswith("\n"):
                content += "\n"
            tasks_file.write_text(content + task_line)
    else:
        # No ## Todo section, add one
        if not content.endswith("\n"):
            content += "\n"
        content += f"\n## Todo\n\n{task_line}"
        tasks_file.write_text(content)


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
