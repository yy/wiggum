"""Runner utilities for wiggum."""

import subprocess
from pathlib import Path
from typing import Optional, Tuple

from wiggum.agents import check_cli_available, get_cli_error_message
from wiggum.parsing import parse_markdown_from_output


RETRY_PROMPT_TEMPLATE = """Your previous response could not be parsed. Please respond again using this exact format:

```markdown
## Tasks

- [ ] Task description 1
- [ ] Task description 2
```

Your previous response was:
{previous_output}

Original request:
{original_prompt}"""


def run_claude_with_retry(
    prompt: str, max_retries: int = 3
) -> Tuple[Optional[dict], Optional[str]]:
    """Run Claude and retry if the output cannot be parsed.

    Args:
        prompt: The planning prompt to send to Claude.
        max_retries: Maximum number of attempts (default: 3).

    Returns:
        A tuple of (parsed_result, error_message). If successful, parsed_result
        is a dict with 'tasks' and 'constraints' keys. If failed, parsed_result
        is None and error_message contains the reason.
    """
    current_prompt = prompt

    for _ in range(max_retries):
        output, error = run_claude_for_planning(current_prompt)

        # Return immediately on Claude CLI errors
        if error:
            return None, error

        # Return error if no output
        if not output:
            return None, "Claude returned no output"

        result = parse_markdown_from_output(output)

        if result:
            return result, None

        # Build retry prompt with format hint and previous output
        current_prompt = RETRY_PROMPT_TEMPLATE.format(
            previous_output=output, original_prompt=prompt
        )

    return None, f"Could not parse Claude's response after {max_retries} attempts"


def run_claude_for_planning(meta_prompt: str) -> Tuple[Optional[str], Optional[str]]:
    """Run Claude with meta prompt and return output.

    Args:
        meta_prompt: The planning prompt to send to Claude.

    Returns:
        A tuple of (output, error_message). If successful, output is the stdout
        and error_message is None. If failed, output is None and error_message
        contains the reason.
    """
    # Validate Claude CLI is available before running
    if not check_cli_available("claude"):
        return None, get_cli_error_message("claude")

    result = subprocess.run(
        ["claude", "--print", "-p", meta_prompt],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout, None


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
