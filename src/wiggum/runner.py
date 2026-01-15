"""Runner utilities for ralph-loop."""

import subprocess
from pathlib import Path
from typing import Optional


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
