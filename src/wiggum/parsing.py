"""Markdown parsing for ralph-loop."""

import re
from typing import Optional


def parse_markdown_from_output(output: str) -> Optional[dict]:
    """Extract and parse markdown block from Claude output.

    Expects markdown in the format:
    ```markdown
    ## Goal

    One line goal description

    ## Tasks

    - [ ] Task 1
    - [ ] Task 2

    ## Constraints

    security_mode: conservative|path_restricted|yolo
    allow_paths: comma,separated,paths
    internet_access: true|false
    ```

    Returns:
        Dict with 'goal' (str), 'tasks' (list of str), and 'constraints' (dict),
        or None if parsing fails.
    """

    # Find markdown block in output
    match = re.search(r"```markdown\s*(.*?)\s*```", output, re.DOTALL | re.IGNORECASE)
    if not match:
        return None

    content = match.group(1).strip()
    if not content:
        return None

    # Extract goal from ## Goal section
    goal_match = re.search(r"##\s*Goal\s*\n+(.+?)(?=\n##|\Z)", content, re.DOTALL)
    if not goal_match:
        return None

    # Get first non-empty line as the goal
    goal_lines = [
        line.strip() for line in goal_match.group(1).strip().split("\n") if line.strip()
    ]
    if not goal_lines:
        return None
    goal = goal_lines[0]

    # Extract tasks from ## Tasks section
    tasks_match = re.search(r"##\s*Tasks\s*\n+(.+?)(?=\n##|\Z)", content, re.DOTALL)
    if not tasks_match:
        return None

    # Parse task lines (unchecked only: - [ ])
    tasks = []
    for line in tasks_match.group(1).strip().split("\n"):
        line = line.strip()
        # Match unchecked checkbox: - [ ]
        task_match = re.match(r"^-\s*\[\s*\]\s*(.+)$", line)
        if task_match:
            tasks.append(task_match.group(1).strip())

    if not tasks:
        return None

    # Extract constraints from ## Constraints section (optional)
    constraints = {}
    constraints_match = re.search(
        r"##\s*Constraints\s*\n+(.+?)(?=\n##|\Z)", content, re.DOTALL
    )
    if constraints_match:
        constraints_text = constraints_match.group(1).strip()
        for line in constraints_text.split("\n"):
            line = line.strip()
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                if key == "security_mode":
                    constraints["security_mode"] = value
                elif key == "allow_paths":
                    constraints["allow_paths"] = value
                elif key == "internet_access":
                    # Parse boolean
                    constraints["internet_access"] = value.lower() in (
                        "true",
                        "yes",
                        "1",
                    )

    return {"goal": goal, "tasks": tasks, "constraints": constraints}
