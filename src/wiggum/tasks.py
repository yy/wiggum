"""Task management for ralph-loop."""

import re
from pathlib import Path
from typing import Optional


def tasks_remaining(tasks_file: Path = Path("TASKS.md")) -> bool:
    """Check if there are incomplete tasks in TASKS.md."""
    if not tasks_file.exists():
        return True  # No tasks file means we don't know, keep running

    content = tasks_file.read_text()
    # Count unchecked boxes in Todo section

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

    # Find first unchecked task: - [ ] task description
    match = re.search(r"^- \[ \] (.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def get_existing_tasks_context(tasks_file: Path) -> str:
    """Generate context about existing tasks for the meta-prompt.

    Args:
        tasks_file: Path to the tasks file.

    Returns:
        A formatted string describing existing tasks, or empty string if no tasks exist.
    """
    if not tasks_file.exists():
        return ""

    content = tasks_file.read_text()
    if not content.strip():
        return ""

    # Extract completed tasks
    done_tasks = re.findall(r"^- \[[xX]\] (.+)$", content, re.MULTILINE)
    # Extract pending/in-progress tasks (unchecked)
    pending_tasks = re.findall(r"^- \[ \] (.+)$", content, re.MULTILINE)

    # If no tasks at all, return empty
    if not done_tasks and not pending_tasks:
        return ""

    # Build context string
    parts = ["## Existing Tasks\n"]
    parts.append("There is already a TASKS.md file with the following tasks:\n")

    if done_tasks:
        parts.append("\n### Completed")
        for task in done_tasks:
            parts.append(f"- [x] {task.strip()}")

    if pending_tasks:
        parts.append("\n### Pending")
        for task in pending_tasks:
            parts.append(f"- [ ] {task.strip()}")

    parts.append(
        "\n\n**Important**: Do NOT suggest tasks that duplicate the above. "
        "Focus on NEW tasks that build on or complement the existing work."
    )

    return "\n".join(parts)


def get_existing_task_descriptions(tasks_file: Path) -> set[str]:
    """Extract all task descriptions from an existing TASKS.md file.

    Args:
        tasks_file: Path to the tasks file.

    Returns:
        Set of task descriptions (without checkbox prefixes), normalized to lowercase.
    """
    if not tasks_file.exists():
        return set()

    content = tasks_file.read_text()
    # Match both checked and unchecked tasks: - [x] or - [ ]
    task_matches = re.findall(
        r"^- \[[x ]\] (.+)$", content, re.MULTILINE | re.IGNORECASE
    )
    # Normalize to lowercase for comparison
    return {task.strip().lower() for task in task_matches}


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
