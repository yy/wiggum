"""Tests for --keep-running flag that continues loop even when tasks are complete.

When tasks are all done but iterations remain, the agent can identify more tasks
and add them to TASKS.md. This is controlled by --keep-running flag.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from wiggum.cli import app

runner = CliRunner()


class TestKeepRunningFlag:
    """Tests for the --keep-running CLI flag."""

    def test_run_stops_by_default_when_tasks_complete(self, tmp_path: Path) -> None:
        """By default, loop stops when all tasks are complete."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
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

        # Should not call Claude because tasks are done
        mock_run.assert_not_called()
        assert "complete" in result.output.lower()
        assert result.exit_code == 0

    def test_keep_running_continues_when_tasks_complete(self, tmp_path: Path) -> None:
        """With --keep-running, loop continues even when all tasks are complete."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")

        call_count = 0

        def mock_subprocess_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return MagicMock(returncode=0, stdout="", stderr="")

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
                    "3",
                    "--keep-running",
                ],
            )

        # Should run all 3 iterations despite tasks being complete
        assert call_count == 3
        assert result.exit_code == 0

    def test_keep_running_runs_all_iterations(self, tmp_path: Path) -> None:
        """--keep-running runs for full max_iterations count."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        # Start with incomplete task
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        call_count = 0

        def mock_subprocess_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Mark task complete after first call
            if call_count == 1:
                tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return MagicMock(returncode=0, stdout="", stderr="")

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
                    "--keep-running",
                ],
            )

        # Should run all 5 iterations
        assert call_count == 5
        assert result.exit_code == 0

    def test_stop_when_done_explicitly_stops(self, tmp_path: Path) -> None:
        """--stop-when-done explicitly stops when tasks complete (default behavior)."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
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
                    "--stop-when-done",
                ],
            )

        # Should not call Claude because tasks are done
        mock_run.assert_not_called()
        assert "complete" in result.output.lower()
        assert result.exit_code == 0

    def test_keep_running_and_stop_when_done_are_mutually_exclusive(
        self, tmp_path: Path
    ) -> None:
        """--keep-running and --stop-when-done cannot be used together."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")

        result = runner.invoke(
            app,
            [
                "run",
                "-f",
                str(prompt_file),
                "--keep-running",
                "--stop-when-done",
            ],
        )

        # Should fail with error
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()


class TestKeepRunningDryRun:
    """Tests for --keep-running in dry-run output."""

    def test_dry_run_shows_stop_when_done_by_default(self, tmp_path: Path) -> None:
        """Dry run shows default behavior is to stop when tasks are done."""
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

        assert "stop when done" in result.output.lower()
        assert result.exit_code == 0

    def test_dry_run_shows_keep_running_when_set(self, tmp_path: Path) -> None:
        """Dry run shows keep-running mode when flag is set."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")

        result = runner.invoke(
            app,
            [
                "run",
                "-f",
                str(prompt_file),
                "--dry-run",
                "--keep-running",
            ],
        )

        assert "keep running" in result.output.lower()
        assert result.exit_code == 0


class TestKeepRunningConfig:
    """Tests for keep_running in .ralph-loop.toml configuration."""

    def test_config_keep_running_true_continues_loop(self, tmp_path: Path) -> None:
        """Config with keep_running = true continues loop when tasks complete."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text("[loop]\nkeep_running = true\n")

        call_count = 0

        def mock_subprocess_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return MagicMock(returncode=0, stdout="", stderr="")

        # Change to tmp_path so config file is found
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
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
                        "2",
                    ],
                )
        finally:
            os.chdir(original_cwd)

        # Should run both iterations
        assert call_count == 2
        assert result.exit_code == 0

    def test_cli_flag_overrides_config(self, tmp_path: Path) -> None:
        """CLI flag --stop-when-done overrides config keep_running = true."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text("[loop]\nkeep_running = true\n")

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
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
                        "--stop-when-done",
                    ],
                )
        finally:
            os.chdir(original_cwd)

        # Should not run because --stop-when-done overrides config
        mock_run.assert_not_called()
        assert "complete" in result.output.lower()
        assert result.exit_code == 0


class TestConfigFileWritesKeepRunning:
    """Tests that write_config correctly handles keep_running."""

    def test_write_config_includes_keep_running(self, tmp_path: Path) -> None:
        """write_config correctly writes keep_running to [loop] section."""
        from wiggum.cli import write_config, read_config

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            config = {
                "loop": {
                    "max_iterations": 10,
                    "keep_running": True,
                }
            }
            write_config(config)

            # Read back and verify
            result = read_config()
            assert result.get("loop", {}).get("keep_running") is True
        finally:
            os.chdir(original_cwd)
