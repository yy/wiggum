"""Tests for logging functionality in ralph-loop."""

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ralph_loop.cli import app

runner = CliRunner()


class TestLogFileOption:
    """Tests for the --log-file option."""

    def test_log_file_is_created_when_specified(self, tmp_path: Path) -> None:
        """When --log-file is specified, the log file is created."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        log_file = tmp_path / "loop.log"

        def mock_subprocess_run(cmd, **kwargs):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return MagicMock(returncode=0, stdout="Test output from claude")

        with patch("ralph_loop.cli.subprocess.run", side_effect=mock_subprocess_run):
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "--log-file",
                    str(log_file),
                    "-n",
                    "5",
                ],
            )

        assert result.exit_code == 0
        assert log_file.exists()

    def test_no_log_file_created_without_option(self, tmp_path: Path) -> None:
        """Without --log-file, no log file is created."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        log_file = tmp_path / "loop.log"

        def mock_subprocess_run(cmd, **kwargs):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return MagicMock(returncode=0, stdout="Test output")

        with patch("ralph_loop.cli.subprocess.run", side_effect=mock_subprocess_run):
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

        assert result.exit_code == 0
        assert not log_file.exists()


class TestLogFileContent:
    """Tests for the content written to the log file."""

    def test_log_contains_iteration_number(self, tmp_path: Path) -> None:
        """Log entries include the iteration number."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        log_file = tmp_path / "loop.log"

        def mock_subprocess_run(cmd, **kwargs):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return MagicMock(returncode=0, stdout="Claude output here")

        with patch("ralph_loop.cli.subprocess.run", side_effect=mock_subprocess_run):
            runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "--log-file",
                    str(log_file),
                    "-n",
                    "5",
                ],
            )

        log_content = log_file.read_text()
        # Should contain iteration number
        assert "Iteration 1" in log_content or "iteration 1" in log_content.lower()

    def test_log_contains_timestamp(self, tmp_path: Path) -> None:
        """Log entries include a timestamp."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        log_file = tmp_path / "loop.log"

        def mock_subprocess_run(cmd, **kwargs):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return MagicMock(returncode=0, stdout="Claude output here")

        with patch("ralph_loop.cli.subprocess.run", side_effect=mock_subprocess_run):
            runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "--log-file",
                    str(log_file),
                    "-n",
                    "5",
                ],
            )

        log_content = log_file.read_text()
        # Should contain a timestamp in ISO-like format (YYYY-MM-DD HH:MM:SS)
        timestamp_pattern = r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"
        assert re.search(timestamp_pattern, log_content) is not None

    def test_log_contains_claude_output(self, tmp_path: Path) -> None:
        """Log entries include the output from claude."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        log_file = tmp_path / "loop.log"

        expected_output = "This is unique test output from claude 12345"

        def mock_subprocess_run(cmd, **kwargs):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return MagicMock(returncode=0, stdout=expected_output)

        with patch("ralph_loop.cli.subprocess.run", side_effect=mock_subprocess_run):
            runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "--log-file",
                    str(log_file),
                    "-n",
                    "5",
                ],
            )

        log_content = log_file.read_text()
        assert expected_output in log_content


class TestLogFileMultipleIterations:
    """Tests for logging across multiple iterations."""

    def test_log_appends_multiple_iterations(self, tmp_path: Path) -> None:
        """Log file contains entries for all iterations."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n## Todo\n\n- [ ] task1\n- [ ] task2\n- [ ] task3\n"
        )
        log_file = tmp_path / "loop.log"

        call_count = 0

        def mock_subprocess_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                tasks_file.write_text(
                    "# Tasks\n\n## Todo\n\n- [ ] task2\n- [ ] task3\n\n## Done\n\n- [x] task1\n"
                )
            elif call_count == 2:
                tasks_file.write_text(
                    "# Tasks\n\n## Todo\n\n- [ ] task3\n\n## Done\n\n- [x] task1\n- [x] task2\n"
                )
            elif call_count == 3:
                tasks_file.write_text(
                    "# Tasks\n\n## Done\n\n- [x] task1\n- [x] task2\n- [x] task3\n"
                )
            return MagicMock(returncode=0, stdout=f"Output for iteration {call_count}")

        with patch("ralph_loop.cli.subprocess.run", side_effect=mock_subprocess_run):
            runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "--log-file",
                    str(log_file),
                    "-n",
                    "10",
                ],
            )

        log_content = log_file.read_text()
        # Should contain entries for all 3 iterations
        assert "Iteration 1" in log_content or "iteration 1" in log_content.lower()
        assert "Iteration 2" in log_content or "iteration 2" in log_content.lower()
        assert "Iteration 3" in log_content or "iteration 3" in log_content.lower()
        assert "Output for iteration 1" in log_content
        assert "Output for iteration 2" in log_content
        assert "Output for iteration 3" in log_content

    def test_log_appends_to_existing_file(self, tmp_path: Path) -> None:
        """Log file appends to existing content (doesn't overwrite)."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        log_file = tmp_path / "loop.log"

        # Pre-populate log file
        existing_content = "Previous log entry\n"
        log_file.write_text(existing_content)

        def mock_subprocess_run(cmd, **kwargs):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return MagicMock(returncode=0, stdout="New output")

        with patch("ralph_loop.cli.subprocess.run", side_effect=mock_subprocess_run):
            runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "--log-file",
                    str(log_file),
                    "-n",
                    "5",
                ],
            )

        log_content = log_file.read_text()
        # Should contain both old and new content
        assert "Previous log entry" in log_content
        assert "New output" in log_content


class TestDryRunWithLogFile:
    """Tests for dry-run mode with log file option."""

    def test_dry_run_shows_log_file_option(self, tmp_path: Path) -> None:
        """Dry run output shows the log file when specified."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        log_file = tmp_path / "loop.log"

        result = runner.invoke(
            app,
            [
                "run",
                "-f",
                str(prompt_file),
                "--log-file",
                str(log_file),
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        # Should mention log file in output
        assert "log" in result.output.lower() or str(log_file) in result.output
