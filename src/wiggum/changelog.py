"""Changelog generation from completed tasks."""

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional


@dataclass
class ChangelogVersion:
    """A version section in the changelog."""

    version: str
    date: Optional[str]
    entries: dict[str, list[str]] = field(default_factory=dict)


# Category keywords for inferring changelog categories
CATEGORY_KEYWORDS = {
    "Added": ["add", "implement", "create", "introduce", "new"],
    "Changed": [
        "update",
        "change",
        "improve",
        "refactor",
        "enhance",
        "modify",
        "rename",
    ],
    "Fixed": ["fix", "resolve", "correct", "repair", "patch"],
    "Removed": ["remove", "delete", "drop", "deprecate"],
}

# Order for displaying categories in changelog
CATEGORY_ORDER = ["Added", "Changed", "Fixed", "Removed"]


def _format_version_header(version: str, version_date: Optional[str] = None) -> str:
    """Format a version header line for the changelog.

    Args:
        version: Version string (e.g., "0.8.0" or "Unreleased").
        version_date: Date string for the version (e.g., "2024-01-15").

    Returns:
        Formatted version header with trailing newline.
    """
    if version == "Unreleased":
        return "## [Unreleased]\n"
    date_str = version_date or date.today().isoformat()
    return f"## [{version}] - {date_str}\n"


def _format_entries_by_category(entries: dict[str, list[str]]) -> list[str]:
    """Format changelog entries grouped by category.

    Args:
        entries: Dict mapping category names to task lists.

    Returns:
        List of formatted lines (category headers and task items).
    """
    lines: list[str] = []
    for category in CATEGORY_ORDER:
        if category in entries and entries[category]:
            lines.append(f"### {category}\n")
            for task in entries[category]:
                lines.append(f"- {task}")
            lines.append("")  # Blank line after category
    return lines


def categorize_task(description: str) -> str:
    """Infer changelog category from task description.

    Args:
        description: The task description text.

    Returns:
        One of: "Added", "Changed", "Fixed", "Removed"
    """
    # Normalize description for matching
    desc_lower = description.lower().strip()

    # Check each category's keywords
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            # Match at start of description or after common prefixes
            if desc_lower.startswith(keyword):
                return category
            # Also match patterns like "- Add feature" or "[ ] Add feature"
            if re.match(rf"^[\[\]\-\s]*{keyword}\b", desc_lower):
                return category

    # Default to Changed if no match
    return "Changed"


def tasks_to_changelog_entries(tasks: list[str]) -> dict[str, list[str]]:
    """Group tasks by changelog category.

    Args:
        tasks: List of task descriptions.

    Returns:
        Dict mapping category names to lists of task descriptions.
    """
    entries: dict[str, list[str]] = {}

    for task in tasks:
        category = categorize_task(task)
        if category not in entries:
            entries[category] = []
        entries[category].append(task)

    return entries


def format_changelog(
    entries: dict[str, list[str]],
    version: str = "Unreleased",
    version_date: Optional[str] = None,
    include_header: bool = True,
) -> str:
    """Format changelog entries as markdown.

    Args:
        entries: Dict mapping category names to task lists.
        version: Version string (e.g., "0.8.0" or "Unreleased").
        version_date: Date string for the version (e.g., "2024-01-15").
        include_header: Whether to include the top-level "# Changelog" header.

    Returns:
        Formatted markdown string.
    """
    lines = []

    if include_header:
        lines.append("# Changelog\n")

    # Version header
    lines.append(_format_version_header(version, version_date))

    # Add entries by category in order
    lines.extend(_format_entries_by_category(entries))

    return "\n".join(lines).rstrip() + "\n"


def parse_existing_changelog(content: str) -> tuple[str, list[ChangelogVersion]]:
    """Parse an existing changelog file.

    Args:
        content: The changelog file content.

    Returns:
        Tuple of (header_content, list of ChangelogVersion objects).
        Header content includes everything before the first version section.
    """
    versions: list[ChangelogVersion] = []

    # Find all version sections
    # Match patterns like "## [0.8.0] - 2024-01-15" or "## [Unreleased]"
    version_pattern = re.compile(
        r"^## \[([^\]]+)\](?:\s*-\s*(\d{4}-\d{2}-\d{2}))?\s*$", re.MULTILINE
    )

    matches = list(version_pattern.finditer(content))

    if not matches:
        # No versions found, return all content as header
        return content, []

    # Extract header (everything before first version)
    header = content[: matches[0].start()].rstrip() + "\n"

    # Parse each version section
    for i, match in enumerate(matches):
        version = match.group(1)
        version_date = match.group(2)

        # Get content until next version or end
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_content = content[start:end]

        # Parse categories within this version
        entries = _parse_version_entries(section_content)

        versions.append(
            ChangelogVersion(version=version, date=version_date, entries=entries)
        )

    return header, versions


def _parse_version_entries(content: str) -> dict[str, list[str]]:
    """Parse entries from a version section.

    Args:
        content: The content of a single version section.

    Returns:
        Dict mapping category names to lists of entries.
    """
    entries: dict[str, list[str]] = {}
    current_category: Optional[str] = None

    for line in content.split("\n"):
        # Check for category header
        category_match = re.match(r"^### (\w+)\s*$", line)
        if category_match:
            current_category = category_match.group(1)
            if current_category not in entries:
                entries[current_category] = []
            continue

        # Check for list item
        if current_category is not None and line.strip().startswith("- "):
            entry = line.strip()[2:]  # Remove "- " prefix
            entries[current_category].append(entry)

    return entries


def merge_changelog(
    existing_content: str,
    new_entries: dict[str, list[str]],
    version: str = "Unreleased",
    version_date: Optional[str] = None,
) -> str:
    """Merge new entries into an existing changelog.

    Args:
        existing_content: The existing changelog content.
        new_entries: New entries to add.
        version: Version string for the new entries.
        version_date: Date for the version.

    Returns:
        Updated changelog content.
    """
    header, versions = parse_existing_changelog(existing_content)

    # Check if we should update an existing version or add a new one
    existing_version = None
    for v in versions:
        if v.version == version:
            existing_version = v
            break

    if existing_version:
        # Merge into existing version
        for category, tasks in new_entries.items():
            if category not in existing_version.entries:
                existing_version.entries[category] = []
            existing_version.entries[category].extend(tasks)
    else:
        # Add new version at the top
        new_version = ChangelogVersion(
            version=version,
            date=version_date or date.today().isoformat(),
            entries=new_entries,
        )
        versions.insert(0, new_version)

    # Reconstruct changelog
    lines = [header.rstrip(), ""]

    for v in versions:
        lines.append(_format_version_header(v.version, v.date))
        lines.extend(_format_entries_by_category(v.entries))

    return "\n".join(lines).rstrip() + "\n"


def clear_done_tasks(tasks_file: Path) -> None:
    """Remove completed tasks from the Done section of TASKS.md.

    Args:
        tasks_file: Path to the tasks file.
    """
    if not tasks_file.exists():
        return

    content = tasks_file.read_text()

    # Find and clear the Done section content
    # Keep the ## Done header but remove its task items
    done_pattern = re.compile(r"(## Done\n+)((?:- \[[xX]\] .+\n?)*)", re.MULTILINE)

    def clear_done(match: re.Match[str]) -> str:
        return match.group(1) + "\n"

    new_content = done_pattern.sub(clear_done, content)
    tasks_file.write_text(new_content)
