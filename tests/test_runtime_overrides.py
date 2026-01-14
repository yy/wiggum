"""Tests for runtime override flags in ralph-loop run command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ralph_loop.cli import app

runner = CliRunner()


class TestStopConditionFlag:
    """Tests for the --stop-condition flag."""

    def test_stop_condition_tasks_checks_tasks_file(self, tmp_path: Path) -> None:
        """--stop-condition=tasks checks TASKS.md for completion (default behavior)."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        # All tasks complete
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")

        with patch("ralph_loop.cli.subprocess.run") as mock_run:
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "--stop-condition",
                    "tasks",
                    "-n",
                    "5",
                ],
            )

        # Should exit immediately since all tasks are done
        mock_run.assert_not_called()
        assert "complete" in result.output.lower()
        assert result.exit_code == 0

    def test_stop_condition_file_colon_path_checks_file(self, tmp_path: Path) -> None:
        """--stop-condition=file:path checks for file existence."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        stop_file = tmp_path / "DONE.md"
        stop_file.write_text("done")

        with patch("ralph_loop.cli.subprocess.run") as mock_run:
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "--stop-condition",
                    f"file:{stop_file}",
                    "-n",
                    "5",
                ],
            )

        # Should exit immediately since stop file exists
        mock_run.assert_not_called()
        assert "stop file" in result.output.lower() or "exists" in result.output.lower()
        assert result.exit_code == 0

    def test_stop_condition_none_only_uses_iteration_limit(
        self, tmp_path: Path
    ) -> None:
        """--stop-condition=none disables task/file checks, only uses iteration limit."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        # All tasks complete - but we should still run because stop-condition=none
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")

        call_count = 0

        def mock_subprocess_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return MagicMock(returncode=0, stdout="output", stderr="")

        with patch("ralph_loop.cli.subprocess.run", side_effect=mock_subprocess_run):
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "--stop-condition",
                    "none",
                    "-n",
                    "3",
                ],
            )

        # Should run all 3 iterations despite tasks being complete
        assert call_count == 3
        assert result.exit_code == 0

    def test_stop_condition_invalid_value_shows_error(self, tmp_path: Path) -> None:
        """Invalid --stop-condition value shows an error."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")

        result = runner.invoke(
            app,
            [
                "run",
                "-f",
                str(prompt_file),
                "--stop-condition",
                "invalid_value",
            ],
        )

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "error" in result.output.lower()

    def test_stop_condition_default_is_tasks(self, tmp_path: Path) -> None:
        """Without --stop-condition, default behavior is to check tasks."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        # All tasks complete
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")

        with patch("ralph_loop.cli.subprocess.run") as mock_run:
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


class TestStopConditionDryRun:
    """Tests for --stop-condition in dry-run mode."""

    def test_dry_run_shows_stop_condition_tasks(self, tmp_path: Path) -> None:
        """Dry run shows stop condition when set to tasks."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")

        result = runner.invoke(
            app,
            [
                "run",
                "-f",
                str(prompt_file),
                "--stop-condition",
                "tasks",
                "--dry-run",
            ],
        )

        assert (
            "stop condition" in result.output.lower()
            or "tasks" in result.output.lower()
        )
        assert result.exit_code == 0

    def test_dry_run_shows_stop_condition_file(self, tmp_path: Path) -> None:
        """Dry run shows stop condition when set to file:path."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")

        result = runner.invoke(
            app,
            [
                "run",
                "-f",
                str(prompt_file),
                "--stop-condition",
                "file:DONE.md",
                "--dry-run",
            ],
        )

        assert (
            "stop condition" in result.output.lower() or "file" in result.output.lower()
        )
        assert result.exit_code == 0

    def test_dry_run_shows_stop_condition_none(self, tmp_path: Path) -> None:
        """Dry run shows stop condition when set to none."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")

        result = runner.invoke(
            app,
            [
                "run",
                "-f",
                str(prompt_file),
                "--stop-condition",
                "none",
                "--dry-run",
            ],
        )

        assert (
            "stop condition" in result.output.lower() or "none" in result.output.lower()
        )
        assert result.exit_code == 0


class TestStopConditionWithStopFile:
    """Tests for interaction between --stop-condition and --stop-file."""

    def test_stop_file_still_works_for_backwards_compatibility(
        self, tmp_path: Path
    ) -> None:
        """--stop-file flag still works for backwards compatibility."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        stop_file = tmp_path / "DONE.md"
        stop_file.write_text("done")

        with patch("ralph_loop.cli.subprocess.run") as mock_run:
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "--stop-file",
                    str(stop_file),
                    "-n",
                    "5",
                ],
            )

        # Should exit immediately since stop file exists
        mock_run.assert_not_called()
        assert "stop file" in result.output.lower()
        assert result.exit_code == 0

    def test_stop_condition_file_overrides_stop_file(self, tmp_path: Path) -> None:
        """--stop-condition=file:X takes precedence over --stop-file."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        # Old stop file exists
        old_stop_file = tmp_path / "OLD_DONE.md"
        old_stop_file.write_text("done")
        # New stop file does not exist
        new_stop_file = tmp_path / "NEW_DONE.md"

        call_count = 0

        def mock_subprocess_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Create the new stop file after first iteration
            if call_count == 1:
                new_stop_file.write_text("done")
            return MagicMock(returncode=0, stdout="output", stderr="")

        with patch("ralph_loop.cli.subprocess.run", side_effect=mock_subprocess_run):
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "--stop-file",
                    str(old_stop_file),  # This exists but should be ignored
                    "--stop-condition",
                    f"file:{new_stop_file}",  # This doesn't exist initially
                    "-n",
                    "5",
                ],
            )

        # Should run once (new stop file didn't exist initially)
        # then stop (new stop file was created)
        assert call_count == 1
        assert result.exit_code == 0
