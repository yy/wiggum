"""Markdown parsing for wiggum."""

import re
from typing import Optional

# Precompiled regex patterns for content extraction
_MARKDOWN_FENCE_RE = re.compile(r"```markdown\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_ANY_FENCE_RE = re.compile(r"```\w*\s*(.*?)\s*```", re.DOTALL)

# Precompiled regex patterns for task/constraint extraction
_TASKS_HEADING_RE = re.compile(r"^#{1,6}\s*Tasks\s*$", re.MULTILINE)
_CONSTRAINTS_HEADING_RE = re.compile(r"^#{1,6}\s*Constraints\s*$", re.MULTILINE)
_NEXT_HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)

_CHECKBOX_RE = re.compile(r"^-\s*\[\s*\]\s*(.+)$")
_CHECKED_RE = re.compile(r"^-\s*\[x\]\s*(.+)$", re.IGNORECASE)
_PLAIN_LIST_RE = re.compile(r"^-\s+(.+)$")
_NUMBERED_LIST_RE = re.compile(r"^\d+\.\s+(.+)$")

# Structural line: heading or list item
_STRUCTURAL_LINE_RE = re.compile(r"^(#{1,6}\s+|- |\d+\.\s+)", re.MULTILINE)


def _extract_fenced_content(output: str) -> Optional[str]:
    """Try markdown fences first, then any-lang fences."""
    match = _MARKDOWN_FENCE_RE.search(output)
    if match:
        content = match.group(1).strip()
        if content:
            return content

    match = _ANY_FENCE_RE.search(output)
    if match:
        content = match.group(1).strip()
        if content:
            return content

    return None


def _extract_unfenced_content(output: str) -> Optional[str]:
    """Find the first structural line and use everything from there."""
    match = _STRUCTURAL_LINE_RE.search(output)
    if match:
        content = output[match.start() :].strip()
        if content:
            return content
    return None


def _extract_tasks_from_section(text: str) -> list[str]:
    """Extract tasks using checkbox > plain list > numbered list priority."""
    # First pass: try checkboxes (skip checked items)
    tasks = []
    has_checkbox = False
    for line in text.strip().split("\n"):
        line = line.strip()
        if _CHECKED_RE.match(line):
            has_checkbox = True
            continue
        m = _CHECKBOX_RE.match(line)
        if m:
            has_checkbox = True
            tasks.append(m.group(1).strip())
    if has_checkbox:
        return tasks

    # Second pass: plain list items
    tasks = []
    for line in text.strip().split("\n"):
        line = line.strip()
        m = _PLAIN_LIST_RE.match(line)
        if m:
            tasks.append(m.group(1).strip())
    if tasks:
        return tasks

    # Third pass: numbered list items
    tasks = []
    for line in text.strip().split("\n"):
        line = line.strip()
        m = _NUMBERED_LIST_RE.match(line)
        if m:
            tasks.append(m.group(1).strip())
    return tasks


def _get_section_after_heading(content: str, heading_re: re.Pattern) -> Optional[str]:
    """Get the text content of a section following a heading."""
    match = heading_re.search(content)
    if not match:
        return None
    after = content[match.end() :]
    # Find the next heading to delimit this section
    next_heading = _NEXT_HEADING_RE.search(after.lstrip("\n"))
    if next_heading:
        section = after.lstrip("\n")[: next_heading.start()]
    else:
        section = after
    return section.strip()


def _has_tasks_heading(content: str) -> bool:
    """Check if content contains a Tasks heading at any level."""
    return bool(_TASKS_HEADING_RE.search(content))


def _extract_tasks(content: str) -> list[str]:
    """Extract tasks: try Tasks heading section first, then whole content."""
    section = _get_section_after_heading(content, _TASKS_HEADING_RE)
    if section is not None:
        tasks = _extract_tasks_from_section(section)
        if tasks:
            return tasks

    # Fallback: search entire content
    return _extract_tasks_from_section(content)


def _extract_constraints(content: str) -> dict:
    """Extract constraints with flexible heading level."""
    constraints = {}
    section = _get_section_after_heading(content, _CONSTRAINTS_HEADING_RE)
    if section is None:
        return constraints

    for line in section.split("\n"):
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
                constraints["internet_access"] = value.lower() in (
                    "true",
                    "yes",
                    "1",
                )

    return constraints


def parse_markdown_from_output(output: str) -> Optional[dict]:
    """Extract and parse markdown block from Claude output.

    Tries progressively looser extraction strategies:
    1. ```markdown fences (strict)
    2. ```<any-lang> fences
    3. Unfenced content starting at first structural line

    Within the extracted content, tasks are found via:
    1. #{1,6} Tasks heading section, then:
       a. - [ ] checkboxes
       b. - plain list items
       c. 1. numbered items
    2. If no Tasks heading, search entire content with same priority

    Returns:
        Dict with 'tasks' (list of str) and 'constraints' (dict),
        or None if parsing fails.
    """
    # Try extraction chain: fenced first, then unfenced
    content = _extract_fenced_content(output)
    if content is None:
        content = _extract_unfenced_content(output)
    if content is None:
        return None

    tasks = _extract_tasks(content)
    constraints = _extract_constraints(content)

    # Return None when no tasks were found unless a Tasks heading exists
    # (an empty Tasks section is a valid "no tasks" response, not a parse failure)
    if not tasks and not _has_tasks_heading(content):
        return None

    return {"tasks": tasks, "constraints": constraints}
