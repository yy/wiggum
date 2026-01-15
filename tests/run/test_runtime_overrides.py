"""Tests for runtime override flags in ralph-loop run command."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from wiggum.cli import app

runner = CliRunner()


class TestDefaultStopCondition:
    """Tests for the default stop condition behavior (tasks-based)."""

    def test_default_stop_condition_is_tasks(self, tmp_path: Path) -> None:
        """Default behavior is to check tasks in TASKS.md for completion."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        # All tasks complete
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")

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

        # Should exit immediately since all tasks are done (default behavior)
        mock_run.assert_not_called()
        assert "complete" in result.output.lower()
        assert result.exit_code == 0

    def test_custom_tasks_file_is_used(self, tmp_path: Path) -> None:
        """--tasks flag specifies a custom tasks file for stop condition."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        custom_tasks = tmp_path / "CUSTOM_TASKS.md"
        # All tasks complete in custom file
        custom_tasks.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")

        with patch("wiggum.agents_claude.subprocess.run") as mock_run:
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(custom_tasks),
                    "-n",
                    "5",
                ],
            )

        # Should exit immediately since all tasks are done
        mock_run.assert_not_called()
        assert "complete" in result.output.lower()
        assert result.exit_code == 0
