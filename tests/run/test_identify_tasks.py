"""Tests for the ralph-loop run --identify-tasks option."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from wiggum.cli import app

runner = CliRunner()


class TestIdentifyTasks:
    """Tests for the `ralph-loop run --identify-tasks` option."""

    def test_identify_tasks_populates_tasks_file(self, tmp_path: Path) -> None:
        """--identify-tasks analyzes codebase and populates TASKS.md."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create minimal required files
            Path("templates").mkdir()
            (Path("templates") / "META-PROMPT.md").write_text(
                "Analyze {{goal}}\n{{existing_tasks}}"
            )
            Path("LOOP-PROMPT.md").write_text("## Goal\n\nTest goal")
            Path("TASKS.md").write_text(
                "# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n"
            )

            # Mock Claude to return task suggestions
            mock_output = """```markdown
## Goal

Test goal

## Tasks

- [ ] Refactor utility functions for clarity
- [ ] Add missing test coverage
- [ ] Clean up unused imports
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=mock_output
            ):
                result = runner.invoke(app, ["run", "--identify-tasks"])

            assert result.exit_code == 0
            content = Path("TASKS.md").read_text()
            assert "- [ ] Refactor utility functions for clarity" in content
            assert "- [ ] Add missing test coverage" in content
            assert "- [ ] Clean up unused imports" in content

    def test_identify_tasks_does_not_run_loop(self, tmp_path: Path) -> None:
        """--identify-tasks exits after identifying tasks, doesn't run loop."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "META-PROMPT.md").write_text(
                "Analyze {{goal}}\n{{existing_tasks}}"
            )
            Path("LOOP-PROMPT.md").write_text("## Goal\n\nTest goal")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n")

            mock_output = """```markdown
## Goal

Test goal

## Tasks

- [ ] Some task
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=mock_output
            ) as mock_planning:
                # Also patch subprocess.run to track if loop would run
                with patch("subprocess.run") as mock_run:
                    result = runner.invoke(app, ["run", "--identify-tasks"])

            assert result.exit_code == 0
            # Planning should have been called
            assert mock_planning.called
            # Loop should NOT have run (no subprocess.run calls for claude)
            # The run_claude_for_planning is mocked, so subprocess.run should not be called
            assert not mock_run.called

    def test_identify_tasks_merges_with_existing(self, tmp_path: Path) -> None:
        """--identify-tasks merges new tasks with existing ones, no duplicates."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "META-PROMPT.md").write_text(
                "Analyze {{goal}}\n{{existing_tasks}}"
            )
            Path("LOOP-PROMPT.md").write_text("## Goal\n\nTest goal")
            Path("TASKS.md").write_text(
                "# Tasks\n\n"
                "## Done\n\n"
                "- [x] Completed task\n\n"
                "## In Progress\n\n"
                "## Todo\n\n"
                "- [ ] Existing task\n"
            )

            mock_output = """```markdown
## Goal

Test goal

## Tasks

- [ ] Existing task
- [ ] New refactoring task
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=mock_output
            ):
                result = runner.invoke(app, ["run", "--identify-tasks"])

            assert result.exit_code == 0
            content = Path("TASKS.md").read_text()
            # Existing task should not be duplicated
            assert content.count("Existing task") == 1
            # New task should be added
            assert "- [ ] New refactoring task" in content
            # Completed task preserved
            assert "- [x] Completed task" in content

    def test_identify_tasks_displays_identified_tasks(self, tmp_path: Path) -> None:
        """--identify-tasks displays the identified tasks to user."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "META-PROMPT.md").write_text(
                "Analyze {{goal}}\n{{existing_tasks}}"
            )
            Path("LOOP-PROMPT.md").write_text("## Goal\n\nTest goal")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n")

            mock_output = """```markdown
## Goal

Test goal

## Tasks

- [ ] Simplify complex function
- [ ] Add error handling
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=mock_output
            ):
                result = runner.invoke(app, ["run", "--identify-tasks"])

            assert result.exit_code == 0
            # Should display identified tasks
            assert "Simplify complex function" in result.output
            assert "Add error handling" in result.output

    def test_identify_tasks_handles_empty_response(self, tmp_path: Path) -> None:
        """--identify-tasks handles case when Claude returns no tasks."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "META-PROMPT.md").write_text(
                "Analyze {{goal}}\n{{existing_tasks}}"
            )
            Path("LOOP-PROMPT.md").write_text("## Goal\n\nTest goal")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Existing\n")

            with patch("wiggum.cli.run_claude_for_planning", return_value=None):
                result = runner.invoke(app, ["run", "--identify-tasks"])

            assert result.exit_code == 0
            # Should indicate no tasks found
            assert "no" in result.output.lower() or "could not" in result.output.lower()
            # Existing tasks preserved
            content = Path("TASKS.md").read_text()
            assert "- [ ] Existing" in content

    def test_identify_tasks_handles_missing_meta_prompt(self, tmp_path: Path) -> None:
        """--identify-tasks errors gracefully if META-PROMPT.md is missing."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("## Goal\n\nTest goal")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n")

            result = runner.invoke(app, ["run", "--identify-tasks"])

            assert result.exit_code == 1
            assert (
                "meta" in result.output.lower() or "not found" in result.output.lower()
            )

    def test_identify_tasks_creates_tasks_file_if_missing(self, tmp_path: Path) -> None:
        """--identify-tasks creates TASKS.md if it doesn't exist."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "META-PROMPT.md").write_text(
                "Analyze {{goal}}\n{{existing_tasks}}"
            )
            Path("LOOP-PROMPT.md").write_text("## Goal\n\nTest goal")
            # Note: No TASKS.md file

            mock_output = """```markdown
## Goal

Test goal

## Tasks

- [ ] First identified task
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=mock_output
            ):
                result = runner.invoke(app, ["run", "--identify-tasks"])

            assert result.exit_code == 0
            assert Path("TASKS.md").exists()
            content = Path("TASKS.md").read_text()
            assert "- [ ] First identified task" in content

    def test_identify_tasks_uses_readme_for_context(self, tmp_path: Path) -> None:
        """--identify-tasks uses README.md content for goal inference."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "META-PROMPT.md").write_text(
                "Analyze {{goal}}\n{{existing_tasks}}"
            )
            Path("LOOP-PROMPT.md").write_text("## Goal\n\nBuild a CLI tool")
            Path("README.md").write_text(
                "# My CLI Tool\n\nA tool for automating tasks."
            )
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n")

            mock_output = """```markdown
## Goal

Build CLI automation tool

## Tasks

- [ ] Improve CLI help messages
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=mock_output
            ) as mock_planning:
                result = runner.invoke(app, ["run", "--identify-tasks"])

            assert result.exit_code == 0
            # Check that README content was passed to planning
            call_args = mock_planning.call_args[0][0]
            assert "My CLI Tool" in call_args or "automating" in call_args

    def test_identify_tasks_shows_count_of_added_tasks(self, tmp_path: Path) -> None:
        """--identify-tasks shows how many tasks were added."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "META-PROMPT.md").write_text(
                "Analyze {{goal}}\n{{existing_tasks}}"
            )
            Path("LOOP-PROMPT.md").write_text("## Goal\n\nTest goal")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n")

            mock_output = """```markdown
## Goal

Test goal

## Tasks

- [ ] Task one
- [ ] Task two
- [ ] Task three
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=mock_output
            ):
                result = runner.invoke(app, ["run", "--identify-tasks"])

            assert result.exit_code == 0
            # Should show count
            assert "3" in result.output or "three" in result.output.lower()
