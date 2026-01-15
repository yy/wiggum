"""Tests for stop conditions in ralph-loop.

The only stop condition is TASKS.md checkmarks (besides max iterations).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from wiggum.cli import app, tasks_remaining

runner = CliRunner()


class TestTasksRemaining:
    """Tests for the tasks_remaining function."""

    def test_tasks_remaining_true_when_unchecked_tasks(self, tmp_path: Path) -> None:
        """Returns True when there are unchecked task boxes."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n- [ ] task2\n")
        assert tasks_remaining(tasks_file) is True

    def test_tasks_remaining_false_when_all_complete(self, tmp_path: Path) -> None:
        """Returns False when all tasks are checked."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n- [x] task2\n")
        assert tasks_remaining(tasks_file) is False

    def test_tasks_remaining_true_when_file_missing(self, tmp_path: Path) -> None:
        """Returns True when tasks file doesn't exist (keep running)."""
        tasks_file = tmp_path / "TASKS.md"
        assert tasks_remaining(tasks_file) is True

    def test_tasks_remaining_mixed_tasks(self, tmp_path: Path) -> None:
        """Returns True when some tasks are complete but others remain."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n## Done\n\n- [x] done1\n\n## Todo\n\n- [ ] todo1\n"
        )
        assert tasks_remaining(tasks_file) is True


class TestRunStopsOnTasksComplete:
    """Tests that run command stops when all tasks in TASKS.md are complete."""

    def test_run_exits_immediately_when_all_tasks_complete(
        self, tmp_path: Path
    ) -> None:
        """The loop exits without running if all tasks are already complete."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n- [x] task2\n")

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

        # Claude should never be called because all tasks are complete
        mock_run.assert_not_called()
        assert "complete" in result.output.lower()
        assert result.exit_code == 0

    def test_run_stops_when_tasks_completed_during_loop(self, tmp_path: Path) -> None:
        """The loop stops after an iteration if tasks become complete."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        call_count = 0

        def mock_subprocess_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Mark task complete after first call
            if call_count == 1:
                tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch(
            "wiggum.agents_claude.subprocess.run", side_effect=mock_subprocess_run
        ):
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

        # Claude should be called exactly once
        assert call_count == 1
        assert "complete" in result.output.lower()
        assert result.exit_code == 0

    def test_run_continues_while_tasks_remain(self, tmp_path: Path) -> None:
        """The loop keeps running while there are unchecked tasks."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n- [ ] task2\n")

        call_count = 0

        def mock_subprocess_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Mark one task complete after each iteration
            if call_count == 1:
                tasks_file.write_text(
                    "# Tasks\n\n## Done\n\n- [x] task1\n\n## Todo\n\n- [ ] task2\n"
                )
            elif call_count == 2:
                tasks_file.write_text(
                    "# Tasks\n\n## Done\n\n- [x] task1\n- [x] task2\n"
                )
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch(
            "wiggum.agents_claude.subprocess.run", side_effect=mock_subprocess_run
        ):
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

        # Claude should be called twice (once for each task)
        assert call_count == 2
        assert result.exit_code == 0


class TestRemovedStopConditionFlags:
    """Tests that --stop-condition and --stop-file flags have been removed."""

    def test_stop_condition_flag_not_accepted(self, tmp_path: Path) -> None:
        """--stop-condition flag should not be accepted."""
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
            ],
        )

        # Should fail because flag doesn't exist
        assert result.exit_code != 0
        assert "no such option" in result.output.lower()

    def test_stop_file_flag_not_accepted(self, tmp_path: Path) -> None:
        """--stop-file flag should not be accepted."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")

        result = runner.invoke(
            app,
            [
                "run",
                "-f",
                str(prompt_file),
                "--stop-file",
                "DONE.md",
            ],
        )

        # Should fail because flag doesn't exist
        assert result.exit_code != 0
        assert "no such option" in result.output.lower()


class TestDryRunOutput:
    """Tests for dry-run mode output."""

    def test_dry_run_shows_tasks_stop_condition(self, tmp_path: Path) -> None:
        """Dry run output shows tasks-based stop condition."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")

        result = runner.invoke(
            app,
            [
                "run",
                "-f",
                str(prompt_file),
                "--dry-run",
            ],
        )

        assert "stop condition" in result.output.lower()
        assert "tasks" in result.output.lower()
        assert result.exit_code == 0
