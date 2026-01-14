"""CLI interface for ralph-loop."""

import subprocess
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(help="Ralph Wiggum loop for agents")


def get_templates_dir() -> Path:
    """Get the templates directory from the package."""
    import importlib.resources

    return Path(importlib.resources.files("ralph_loop").joinpath("../../../templates"))


@app.command()
def run(
    prompt: Optional[str] = typer.Option(None, "-p", "--prompt", help="Inline prompt"),
    prompt_file: Optional[Path] = typer.Option(
        None, "-f", "--file", help="Prompt file (default: LOOP-PROMPT.md)"
    ),
    tasks_file: Path = typer.Option(
        Path("TASKS.md"), "--tasks", help="Tasks file to check for completion"
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
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would run"),
) -> None:
    """Run the agent loop. Stops when all tasks in TASKS.md are complete."""
    # Determine prompt source
    if prompt is None:
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
        typer.echo(f"Prompt:\n---\n{prompt}\n---")
        return

    for i in range(1, max_iterations + 1):
        # Check if all tasks are done before running
        if not tasks_remaining(tasks_file):
            typer.echo(f"\nAll tasks in {tasks_file} are complete. Exiting.")
            break

        typer.echo(f"\n{'=' * 60}")
        typer.echo(f"Iteration {i}/{max_iterations}")
        typer.echo(f"{'=' * 60}\n")

        # Run claude
        cmd = ["claude", "--print", "-p", prompt]
        if yolo:
            cmd.append("--dangerously-skip-permissions")
        if allow_paths:
            for path in allow_paths.split(","):
                cmd.extend(["--allowedTools", f"Edit:{path.strip()}*"])
                cmd.extend(["--allowedTools", f"Write:{path.strip()}*"])
        try:
            subprocess.run(cmd, check=False)
        except FileNotFoundError:
            typer.echo(
                "Error: 'claude' command not found. Is Claude Code installed?", err=True
            )
            raise typer.Exit(1)

        # Check if all tasks are done after running
        if not tasks_remaining(tasks_file):
            typer.echo(f"\nAll tasks in {tasks_file} are complete. Exiting.")
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

    # Generate files from templates
    prompt_template = prompt_template_path.read_text()
    prompt_content = prompt_template.replace("{{goal}}", goal).replace(
        "{{doc_files}}", doc_files
    )

    tasks_template = (
        tasks_template_path.read_text()
        if tasks_template_path.exists()
        else "# Tasks\n\n## Todo\n\n{{tasks}}\n\n## Done\n"
    )
    tasks_content = tasks_template.replace(
        "{{tasks}}", "\n".join(tasks) if tasks else "- [ ] (add your first task here)"
    )

    prompt_path.write_text(prompt_content)
    tasks_path.write_text(tasks_content)

    typer.echo(f"\nCreated {prompt_path} and {tasks_path}")
    typer.echo("\nRun the loop with: ralph-loop run")


if __name__ == "__main__":
    app()
