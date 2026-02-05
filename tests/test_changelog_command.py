"""Tests for the wiggum changelog command."""

from pathlib import Path

from typer.testing import CliRunner

from wiggum.changelog import (
    categorize_task,
    clear_done_tasks,
    format_changelog,
    merge_changelog,
    parse_existing_changelog,
    tasks_to_changelog_entries,
)
from wiggum.cli import app

runner = CliRunner()


class TestCategorizeTask:
    """Tests for task categorization logic."""

    def test_add_prefix(self) -> None:
        """Tasks starting with 'Add' are categorized as Added."""
        assert categorize_task("Add new changelog command") == "Added"

    def test_implement_prefix(self) -> None:
        """Tasks starting with 'Implement' are categorized as Added."""
        assert categorize_task("Implement user authentication") == "Added"

    def test_create_prefix(self) -> None:
        """Tasks starting with 'Create' are categorized as Added."""
        assert categorize_task("Create API endpoint") == "Added"

    def test_fix_prefix(self) -> None:
        """Tasks starting with 'Fix' are categorized as Fixed."""
        assert categorize_task("Fix edge case in parser") == "Fixed"

    def test_resolve_prefix(self) -> None:
        """Tasks starting with 'Resolve' are categorized as Fixed."""
        assert categorize_task("Resolve memory leak") == "Fixed"

    def test_update_prefix(self) -> None:
        """Tasks starting with 'Update' are categorized as Changed."""
        assert categorize_task("Update dependencies") == "Changed"

    def test_refactor_prefix(self) -> None:
        """Tasks starting with 'Refactor' are categorized as Changed."""
        assert categorize_task("Refactor authentication module") == "Changed"

    def test_improve_prefix(self) -> None:
        """Tasks starting with 'Improve' are categorized as Changed."""
        assert categorize_task("Improve error handling") == "Changed"

    def test_remove_prefix(self) -> None:
        """Tasks starting with 'Remove' are categorized as Removed."""
        assert categorize_task("Remove deprecated API") == "Removed"

    def test_delete_prefix(self) -> None:
        """Tasks starting with 'Delete' are categorized as Removed."""
        assert categorize_task("Delete unused files") == "Removed"

    def test_default_category(self) -> None:
        """Tasks without recognized prefix default to Changed."""
        assert categorize_task("Some random task") == "Changed"
        assert categorize_task("This task does something") == "Changed"

    def test_case_insensitive(self) -> None:
        """Categorization is case-insensitive."""
        assert categorize_task("add new feature") == "Added"
        assert categorize_task("ADD NEW FEATURE") == "Added"
        assert categorize_task("FIX a bug") == "Fixed"


class TestTasksToChangelogEntries:
    """Tests for grouping tasks by category."""

    def test_groups_by_category(self) -> None:
        """Tasks are grouped by their inferred category."""
        tasks = [
            "Add feature A",
            "Add feature B",
            "Fix bug X",
            "Update documentation",
        ]
        entries = tasks_to_changelog_entries(tasks)

        assert "Added" in entries
        assert len(entries["Added"]) == 2
        assert "Fixed" in entries
        assert len(entries["Fixed"]) == 1
        assert "Changed" in entries
        assert len(entries["Changed"]) == 1

    def test_empty_input(self) -> None:
        """Empty task list returns empty dict."""
        entries = tasks_to_changelog_entries([])
        assert entries == {}

    def test_single_category(self) -> None:
        """All tasks in same category."""
        tasks = ["Fix bug 1", "Fix bug 2", "Resolve issue"]
        entries = tasks_to_changelog_entries(tasks)

        assert list(entries.keys()) == ["Fixed"]
        assert len(entries["Fixed"]) == 3


class TestFormatChangelog:
    """Tests for changelog formatting."""

    def test_basic_format(self) -> None:
        """Generates basic changelog structure."""
        entries = {"Added": ["New feature"], "Fixed": ["Bug fix"]}
        result = format_changelog(entries)

        assert "# Changelog" in result
        assert "## [Unreleased]" in result
        assert "### Added" in result
        assert "- New feature" in result
        assert "### Fixed" in result
        assert "- Bug fix" in result

    def test_versioned_format(self) -> None:
        """Generates versioned changelog."""
        entries = {"Added": ["New feature"]}
        result = format_changelog(entries, version="0.8.0")

        assert "## [0.8.0]" in result
        assert "Unreleased" not in result

    def test_with_date(self) -> None:
        """Includes date when provided."""
        entries = {"Added": ["New feature"]}
        result = format_changelog(entries, version="0.8.0", version_date="2024-01-15")

        assert "## [0.8.0] - 2024-01-15" in result

    def test_category_order(self) -> None:
        """Categories appear in standard order: Added, Changed, Fixed, Removed."""
        entries = {
            "Removed": ["Removed X"],
            "Added": ["Added Y"],
            "Fixed": ["Fixed Z"],
            "Changed": ["Changed W"],
        }
        result = format_changelog(entries)

        added_pos = result.find("### Added")
        changed_pos = result.find("### Changed")
        fixed_pos = result.find("### Fixed")
        removed_pos = result.find("### Removed")

        assert added_pos < changed_pos < fixed_pos < removed_pos

    def test_without_header(self) -> None:
        """Can exclude top-level header."""
        entries = {"Added": ["New feature"]}
        result = format_changelog(entries, include_header=False)

        assert "# Changelog" not in result
        assert "## [Unreleased]" in result


class TestParseExistingChangelog:
    """Tests for parsing existing changelog files."""

    def test_parse_single_version(self) -> None:
        """Parses changelog with single version."""
        content = """# Changelog

## [0.7.0] - 2024-01-10

### Added
- Feature one
- Feature two

### Fixed
- Bug fix
"""
        header, versions = parse_existing_changelog(content)

        assert "# Changelog" in header
        assert len(versions) == 1
        assert versions[0].version == "0.7.0"
        assert versions[0].date == "2024-01-10"
        assert versions[0].entries["Added"] == ["Feature one", "Feature two"]
        assert versions[0].entries["Fixed"] == ["Bug fix"]

    def test_parse_multiple_versions(self) -> None:
        """Parses changelog with multiple versions."""
        content = """# Changelog

## [Unreleased]

### Added
- New thing

## [0.7.0] - 2024-01-10

### Fixed
- Old fix
"""
        header, versions = parse_existing_changelog(content)

        assert len(versions) == 2
        assert versions[0].version == "Unreleased"
        assert versions[1].version == "0.7.0"

    def test_parse_empty_changelog(self) -> None:
        """Returns empty list for changelog without versions."""
        content = "# Changelog\n\nSome intro text.\n"
        header, versions = parse_existing_changelog(content)

        assert header.strip() == content.strip()
        assert versions == []


class TestMergeChangelog:
    """Tests for merging new entries into existing changelog."""

    def test_merge_into_existing_version(self) -> None:
        """Merges entries into existing Unreleased section."""
        existing = """# Changelog

## [Unreleased]

### Added
- Existing feature
"""
        new_entries = {"Added": ["New feature"], "Fixed": ["Bug fix"]}
        result = merge_changelog(existing, new_entries, version="Unreleased")

        assert "- Existing feature" in result
        assert "- New feature" in result
        assert "- Bug fix" in result

    def test_add_new_version(self) -> None:
        """Adds new version section when it doesn't exist."""
        existing = """# Changelog

## [0.7.0] - 2024-01-10

### Added
- Old feature
"""
        new_entries = {"Added": ["New feature"]}
        result = merge_changelog(existing, new_entries, version="0.8.0")

        assert "## [0.8.0]" in result
        assert "- New feature" in result
        # New version should come before old
        assert result.find("[0.8.0]") < result.find("[0.7.0]")


class TestChangelogCommand:
    """Tests for the `wiggum changelog` CLI command."""

    def test_generates_changelog_from_done_tasks(self, tmp_path: Path) -> None:
        """Generates changelog from completed tasks."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] Add new feature\n"
            "- [x] Fix critical bug\n\n"
            "## Todo\n\n"
        )
        output_file = tmp_path / "CHANGELOG.md"

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                [
                    "changelog",
                    "--tasks-file",
                    str(tasks_file),
                    "--output",
                    str(output_file),
                    "--force",
                ],
            )

        assert result.exit_code == 0
        assert output_file.exists()

        content = output_file.read_text()
        assert "# Changelog" in content
        assert "Add new feature" in content
        assert "Fix critical bug" in content

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        """--dry-run shows preview without writing file."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] Add feature\n\n## Todo\n\n")
        output_file = tmp_path / "CHANGELOG.md"

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                [
                    "changelog",
                    "--tasks-file",
                    str(tasks_file),
                    "--output",
                    str(output_file),
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0
        assert "Preview:" in result.output
        assert "Add feature" in result.output
        assert not output_file.exists()

    def test_version_flag(self, tmp_path: Path) -> None:
        """--version creates versioned section."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] Add feature\n\n## Todo\n\n")
        output_file = tmp_path / "CHANGELOG.md"

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                [
                    "changelog",
                    "--tasks-file",
                    str(tasks_file),
                    "--output",
                    str(output_file),
                    "--version",
                    "0.8.0",
                    "--force",
                ],
            )

        assert result.exit_code == 0
        content = output_file.read_text()
        assert "[0.8.0]" in content
        assert "Unreleased" not in content

    def test_append_mode(self, tmp_path: Path) -> None:
        """--append adds to existing changelog."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n## Done\n\n- [x] Add new feature\n\n## Todo\n\n"
        )
        output_file = tmp_path / "CHANGELOG.md"
        output_file.write_text(
            "# Changelog\n\n"
            "## [0.7.0] - 2024-01-10\n\n"
            "### Added\n\n"
            "- Existing feature\n"
        )

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                [
                    "changelog",
                    "--tasks-file",
                    str(tasks_file),
                    "--output",
                    str(output_file),
                    "--append",
                ],
            )

        assert result.exit_code == 0
        content = output_file.read_text()
        assert "Existing feature" in content
        assert "Add new feature" in content

    def test_clear_done_flag(self, tmp_path: Path) -> None:
        """--clear-done removes tasks from Done section."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] Completed task\n\n"
            "## Todo\n\n"
            "- [ ] Pending task\n"
        )
        output_file = tmp_path / "CHANGELOG.md"

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                [
                    "changelog",
                    "--tasks-file",
                    str(tasks_file),
                    "--output",
                    str(output_file),
                    "--clear-done",
                    "--force",
                ],
            )

        assert result.exit_code == 0
        assert "Cleared Done section" in result.output

        tasks_content = tasks_file.read_text()
        assert "Completed task" not in tasks_content
        assert "Pending task" in tasks_content

    def test_no_done_tasks_exits_cleanly(self, tmp_path: Path) -> None:
        """Exits with message when no completed tasks."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n## Todo\n\n- [ ] Task\n")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                ["changelog", "--tasks-file", str(tasks_file)],
            )

        assert result.exit_code == 0
        assert "No completed tasks" in result.output

    def test_missing_tasks_file_error(self, tmp_path: Path) -> None:
        """Shows error when tasks file doesn't exist."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                ["changelog", "--tasks-file", "nonexistent.md"],
            )

        assert result.exit_code == 1
        assert "No tasks file found" in result.output

    def test_shows_task_summary(self, tmp_path: Path) -> None:
        """Shows summary of categorized tasks."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] Add feature A\n"
            "- [x] Add feature B\n"
            "- [x] Fix bug\n\n"
            "## Todo\n\n"
        )
        output_file = tmp_path / "CHANGELOG.md"

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                [
                    "changelog",
                    "--tasks-file",
                    str(tasks_file),
                    "--output",
                    str(output_file),
                    "--force",
                ],
            )

        assert result.exit_code == 0
        assert "3 task(s)" in result.output
        assert "added" in result.output.lower()
        assert "fixed" in result.output.lower()

    def test_prompts_before_overwrite(self, tmp_path: Path) -> None:
        """Prompts for confirmation before overwriting existing file."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] Add feature\n\n## Todo\n\n")
        output_file = tmp_path / "CHANGELOG.md"
        output_file.write_text("# Existing changelog\n")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Answer 'n' to confirmation
            result = runner.invoke(
                app,
                [
                    "changelog",
                    "--tasks-file",
                    str(tasks_file),
                    "--output",
                    str(output_file),
                ],
                input="n\n",
            )

        assert result.exit_code == 0
        assert "Aborted" in result.output
        # File should not be modified
        assert "Existing changelog" in output_file.read_text()

    def test_default_files(self, tmp_path: Path) -> None:
        """Uses TASKS.md and CHANGELOG.md by default."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("TASKS.md").write_text(
                "# Tasks\n\n## Done\n\n- [x] Add feature\n\n## Todo\n\n"
            )
            result = runner.invoke(app, ["changelog", "--force"])

            assert result.exit_code == 0
            assert Path("CHANGELOG.md").exists()


class TestClearDoneTasks:
    """Tests for clear_done_tasks() edge cases."""

    def test_nonexistent_file_returns_silently(self, tmp_path: Path) -> None:
        """Returns without error when file doesn't exist."""
        tasks_file = tmp_path / "nonexistent.md"
        # Should not raise
        clear_done_tasks(tasks_file)

    def test_empty_done_section_preserved(self, tmp_path: Path) -> None:
        """Preserves the Done header when section is already empty."""
        tasks_file = tmp_path / "TASKS.md"
        original = "# Tasks\n\n## Done\n\n## Todo\n\n- [ ] Task\n"
        tasks_file.write_text(original)

        clear_done_tasks(tasks_file)

        result = tasks_file.read_text()
        assert "## Done" in result
        assert "## Todo" in result
        assert "- [ ] Task" in result

    def test_clears_lowercase_x_checkbox(self, tmp_path: Path) -> None:
        """Clears tasks with lowercase [x] checkbox."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n## Done\n\n- [x] Completed task\n\n## Todo\n\n"
        )

        clear_done_tasks(tasks_file)

        result = tasks_file.read_text()
        assert "Completed task" not in result
        assert "## Done" in result

    def test_clears_uppercase_x_checkbox(self, tmp_path: Path) -> None:
        """Clears tasks with uppercase [X] checkbox."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n## Done\n\n- [X] Completed task\n\n## Todo\n\n"
        )

        clear_done_tasks(tasks_file)

        result = tasks_file.read_text()
        assert "Completed task" not in result
        assert "## Done" in result

    def test_clears_multiple_tasks(self, tmp_path: Path) -> None:
        """Clears all completed tasks from Done section."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] First task\n"
            "- [x] Second task\n"
            "- [X] Third task\n\n"
            "## Todo\n\n"
        )

        clear_done_tasks(tasks_file)

        result = tasks_file.read_text()
        assert "First task" not in result
        assert "Second task" not in result
        assert "Third task" not in result
        assert "## Done" in result

    def test_preserves_todo_section(self, tmp_path: Path) -> None:
        """Preserves tasks in the Todo section."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n## Done\n\n- [x] Completed\n\n## Todo\n\n- [ ] Pending task\n"
        )

        clear_done_tasks(tasks_file)

        result = tasks_file.read_text()
        assert "Completed" not in result
        assert "Pending task" in result

    def test_no_done_section_unchanged(self, tmp_path: Path) -> None:
        """File without Done section remains unchanged."""
        tasks_file = tmp_path / "TASKS.md"
        original = "# Tasks\n\n## Todo\n\n- [ ] Task\n"
        tasks_file.write_text(original)

        clear_done_tasks(tasks_file)

        assert tasks_file.read_text() == original

    def test_done_section_at_end_of_file(self, tmp_path: Path) -> None:
        """Handles Done section at end of file without trailing newline."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n## Todo\n\n- [ ] Task\n\n## Done\n\n- [x] Completed"
        )

        clear_done_tasks(tasks_file)

        result = tasks_file.read_text()
        assert "Completed" not in result
        assert "## Done" in result
        assert "- [ ] Task" in result

    def test_preserves_content_after_done_section(self, tmp_path: Path) -> None:
        """Preserves sections that appear after the Done section."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n## Done\n\n- [x] Completed\n\n## Notes\n\nSome notes here.\n"
        )

        clear_done_tasks(tasks_file)

        result = tasks_file.read_text()
        assert "Completed" not in result
        assert "## Notes" in result
        assert "Some notes here." in result
