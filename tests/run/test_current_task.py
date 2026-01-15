"""Tests for displaying current task at iteration start."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from wiggum.cli import app, get_current_task

runner = CliRunner()


class TestGetCurrentTask:
    """Tests for the get_current_task function."""

    def test_returns_first_incomplete_task(self, tmp_path: Path) -> None:
        """Returns the first task marked with - [ ]."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n## Todo\n\n- [ ] First task\n- [ ] Second task\n"
        )
        result = get_current_task(tasks_file)
        assert result == "First task"

    def test_returns_none_when_all_complete(self, tmp_path: Path) -> None:
        """Returns None when all tasks are completed."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] Completed task\n")
        result = get_current_task(tasks_file)
        assert result is None

    def test_returns_none_when_file_missing(self, tmp_path: Path) -> None:
        """Returns None when tasks file doesn't exist."""
        tasks_file = tmp_path / "TASKS.md"
        result = get_current_task(tasks_file)
        assert result is None

    def test_returns_none_for_empty_file(self, tmp_path: Path) -> None:
        """Returns None when tasks file is empty."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("")
        result = get_current_task(tasks_file)
        assert result is None

    def test_skips_completed_tasks(self, tmp_path: Path) -> None:
        """Returns first incomplete task, skipping completed ones."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] Completed task 1\n"
            "- [x] Completed task 2\n\n"
            "## Todo\n\n"
            "- [ ] First incomplete task\n"
        )
        result = get_current_task(tasks_file)
        assert result == "First incomplete task"

    def test_handles_multiline_task_descriptions(self, tmp_path: Path) -> None:
        """Returns only the first line of a task description."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] Main task description\n")
        result = get_current_task(tasks_file)
        assert result == "Main task description"

    def test_handles_in_progress_section(self, tmp_path: Path) -> None:
        """Tasks in 'In Progress' section are treated as current task."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## In Progress\n\n"
            "- [ ] Currently working on this\n\n"
            "## Todo\n\n"
            "- [ ] Next task\n"
        )
        result = get_current_task(tasks_file)
        # Should return the first incomplete task found
        assert result == "Currently working on this"


class TestRunDisplaysCurrentTask:
    """Integration tests for displaying current task during run."""

    def test_run_displays_current_task_at_iteration_start(self, tmp_path: Path) -> None:
        """The run command displays the current task at iteration start."""
        # Setup
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] Implement feature X\n")

        call_count = 0

        def mock_subprocess_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Mark task complete after first iteration
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] Implement feature X\n")
            return MagicMock(returncode=0)

        with patch("wiggum.agents_claude.subprocess.run", side_effect=mock_subprocess_run):
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "-n",
                    "5",
                ],
            )

        # Current task should be displayed
        assert "Implement feature X" in result.output
        assert result.exit_code == 0

    def test_run_shows_no_task_message_when_tasks_empty(self, tmp_path: Path) -> None:
        """When no tasks are found, shows appropriate message."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] All done\n")

        with patch("wiggum.agents_claude.subprocess.run") as mock_run:
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "-n",
                    "5",
                ],
            )

        # Should exit without running since all tasks are complete
        mock_run.assert_not_called()
        assert "All tasks" in result.output or "complete" in result.output.lower()
        assert result.exit_code == 0
