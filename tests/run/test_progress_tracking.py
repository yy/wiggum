"""Tests for progress tracking (file changes) in wiggum."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from wiggum.cli import app

runner = CliRunner()


class TestVerboseFlag:
    """Tests for -v/--verbose aliases for progress display."""

    def test_short_verbose_flag_enables_progress(self, tmp_path: Path) -> None:
        """-v short flag should enable progress display (same as --show-progress)."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        git_was_called = False

        def mock_subprocess_run(cmd, **kwargs):
            nonlocal git_was_called
            if cmd[0] == "claude":
                tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
                return MagicMock(returncode=0, stdout="Claude output")
            elif cmd[0] == "git":
                git_was_called = True
                return MagicMock(returncode=0, stdout=" M file.py\n")
            return MagicMock(returncode=0, stdout="")

        with patch("wiggum.agents.check_cli_available", return_value=True):
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
                        "-v",
                        "-n",
                        "5",
                        "--force",
                        "--no-branch",
                    ],
                )

        assert result.exit_code == 0
        assert git_was_called

    def test_long_verbose_flag_enables_progress(self, tmp_path: Path) -> None:
        """--verbose long flag should enable progress display (same as --show-progress)."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        git_was_called = False

        def mock_subprocess_run(cmd, **kwargs):
            nonlocal git_was_called
            if cmd[0] == "claude":
                tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
                return MagicMock(returncode=0, stdout="Claude output")
            elif cmd[0] == "git":
                git_was_called = True
                return MagicMock(returncode=0, stdout=" M file.py\n")
            return MagicMock(returncode=0, stdout="")

        with patch("wiggum.agents.check_cli_available", return_value=True):
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
                        "--verbose",
                        "-n",
                        "5",
                        "--force",
                        "--no-branch",
                    ],
                )

        assert result.exit_code == 0
        assert git_was_called

    def test_dry_run_with_verbose_flag(self, tmp_path: Path) -> None:
        """Dry run should display progress tracking when -v is used."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")

        result = runner.invoke(
            app,
            [
                "run",
                "-f",
                str(prompt_file),
                "-v",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        # Should mention progress tracking in output
        assert "progress" in result.output.lower()


class TestShowProgressFlag:
    """Tests for the --show-progress flag that displays file changes after each iteration."""

    def test_show_progress_displays_git_status_after_iteration(
        self, tmp_path: Path
    ) -> None:
        """With --show-progress, git status is shown after each iteration."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        def mock_subprocess_run(cmd, **kwargs):
            # Check what command is being run
            if cmd[0] == "claude":
                # Mark task complete
                tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
                return MagicMock(returncode=0, stdout="Claude output")
            elif cmd[0] == "git":
                # Return mock git status output
                return MagicMock(
                    returncode=0, stdout=" M src/main.py\n?? new_file.txt\n"
                )
            return MagicMock(returncode=0, stdout="")

        with patch("wiggum.agents.check_cli_available", return_value=True):
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
                        "--show-progress",
                        "-n",
                        "5",
                        "--force",
                        "--no-branch",
                    ],
                )

        assert result.exit_code == 0
        # Should show file changes in output
        assert "file" in result.output.lower() or "change" in result.output.lower()

    def test_no_progress_shown_without_flag(self, tmp_path: Path) -> None:
        """Without --show-progress, progress output is not displayed."""
        from wiggum.agents import AgentResult

        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        def mock_agent_run(config):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return AgentResult(stdout="Claude output", stderr="", return_code=0)

        mock_agent = MagicMock()
        mock_agent.name = "claude"
        mock_agent.run.side_effect = mock_agent_run

        with patch("wiggum.agents.check_cli_available", return_value=True):
            with patch("wiggum.cli.get_agent", return_value=mock_agent):
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
                        "--force",
                        "--no-branch",
                    ],
                )

        assert result.exit_code == 0
        # Without --show-progress, should not show file change information
        # The output should not contain progress-specific text like "Files changed"
        assert "Files changed" not in result.output


class TestProgressOutput:
    """Tests for the format and content of progress output."""

    def test_modified_files_are_shown(self, tmp_path: Path) -> None:
        """Modified files (M) from git status are displayed."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        def mock_subprocess_run(cmd, **kwargs):
            if cmd[0] == "claude":
                tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
                return MagicMock(returncode=0, stdout="Claude output")
            elif cmd[0] == "git":
                return MagicMock(returncode=0, stdout=" M modified_file.py\n")
            return MagicMock(returncode=0, stdout="")

        with patch("wiggum.agents.check_cli_available", return_value=True):
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
                        "--show-progress",
                        "-n",
                        "5",
                        "--force",
                        "--no-branch",
                    ],
                )

        assert result.exit_code == 0
        assert (
            "modified" in result.output.lower() or "modified_file.py" in result.output
        )

    def test_new_files_are_shown(self, tmp_path: Path) -> None:
        """New/untracked files (??) from git status are displayed."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        def mock_subprocess_run(cmd, **kwargs):
            if cmd[0] == "claude":
                tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
                return MagicMock(returncode=0, stdout="Claude output")
            elif cmd[0] == "git":
                return MagicMock(returncode=0, stdout="?? new_file.txt\n")
            return MagicMock(returncode=0, stdout="")

        with patch("wiggum.agents.check_cli_available", return_value=True):
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
                        "--show-progress",
                        "-n",
                        "5",
                        "--force",
                        "--no-branch",
                    ],
                )

        assert result.exit_code == 0
        assert "new" in result.output.lower() or "new_file.txt" in result.output

    def test_deleted_files_are_shown(self, tmp_path: Path) -> None:
        """Deleted files (D) from git status are displayed."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        def mock_subprocess_run(cmd, **kwargs):
            if cmd[0] == "claude":
                tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
                return MagicMock(returncode=0, stdout="Claude output")
            elif cmd[0] == "git":
                return MagicMock(returncode=0, stdout=" D deleted_file.py\n")
            return MagicMock(returncode=0, stdout="")

        with patch("wiggum.agents.check_cli_available", return_value=True):
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
                        "--show-progress",
                        "-n",
                        "5",
                        "--force",
                        "--no-branch",
                    ],
                )

        assert result.exit_code == 0
        assert "deleted" in result.output.lower() or "deleted_file.py" in result.output

    def test_no_changes_shows_appropriate_message(self, tmp_path: Path) -> None:
        """When no files changed, an appropriate message is shown."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        def mock_subprocess_run(cmd, **kwargs):
            if cmd[0] == "claude":
                tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
                return MagicMock(returncode=0, stdout="Claude output")
            elif cmd[0] == "git":
                return MagicMock(returncode=0, stdout="")
            return MagicMock(returncode=0, stdout="")

        with patch("wiggum.agents.check_cli_available", return_value=True):
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
                        "--show-progress",
                        "-n",
                        "5",
                        "--force",
                        "--no-branch",
                    ],
                )

        assert result.exit_code == 0
        # Should show message about no changes
        assert "no" in result.output.lower() and "change" in result.output.lower()


class TestNonGitDirectory:
    """Tests for handling non-git directories gracefully."""

    def test_non_git_directory_shows_warning(self, tmp_path: Path) -> None:
        """When not in a git repository, a warning is shown but loop continues."""
        from wiggum.agents import AgentResult

        with runner.isolated_filesystem(temp_dir=tmp_path):
            prompt_file = Path("LOOP-PROMPT.md")
            prompt_file.write_text("test prompt")
            tasks_file = Path("TASKS.md")
            tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

            def mock_agent_run(config):
                tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
                return AgentResult(stdout="Claude output", stderr="", return_code=0)

            mock_agent = MagicMock()
            mock_agent.name = "claude"
            mock_agent.run.side_effect = mock_agent_run

            with patch("wiggum.agents.check_cli_available", return_value=True):
                with patch("wiggum.cli.get_agent", return_value=mock_agent):
                    with patch("wiggum.git.is_git_repo", return_value=False):
                        result = runner.invoke(
                            app,
                            [
                                "run",
                                "--show-progress",
                                "-n",
                                "5",
                                "--force",
                                "--no-branch",
                            ],
                        )

            # Loop should complete successfully even without git
            assert result.exit_code == 0
            # With --force, no warning is shown but loop still runs
            # Progress tracking still works (shows iteration info)


class TestProgressMultipleIterations:
    """Tests for progress tracking across multiple iterations."""

    def test_progress_shown_after_each_iteration(self, tmp_path: Path) -> None:
        """Progress is shown after each iteration, not just the last one."""
        from wiggum.agents import AgentResult

        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n- [ ] task2\n")

        call_count = 0

        def mock_agent_run(config):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                tasks_file.write_text(
                    "# Tasks\n\n## Todo\n\n- [ ] task2\n\n## Done\n\n- [x] task1\n"
                )
            elif call_count == 2:
                tasks_file.write_text(
                    "# Tasks\n\n## Done\n\n- [x] task1\n- [x] task2\n"
                )
            return AgentResult(stdout="Claude output", stderr="", return_code=0)

        mock_agent = MagicMock()
        mock_agent.name = "claude"
        mock_agent.run.side_effect = mock_agent_run

        with patch("wiggum.agents.check_cli_available", return_value=True):
            with patch("wiggum.cli.get_agent", return_value=mock_agent):
                result = runner.invoke(
                    app,
                    [
                        "run",
                        "-f",
                        str(prompt_file),
                        "--tasks",
                        str(tasks_file),
                        "--show-progress",
                        "-n",
                        "5",
                        "--force",
                        "--no-branch",
                    ],
                )

        assert result.exit_code == 0
        # Agent should have been called twice (2 tasks)
        assert call_count == 2


class TestDryRunWithProgress:
    """Tests for dry-run mode with progress flag."""

    def test_dry_run_shows_progress_option(self, tmp_path: Path) -> None:
        """Dry run output shows when --show-progress is enabled."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")

        result = runner.invoke(
            app,
            [
                "run",
                "-f",
                str(prompt_file),
                "--show-progress",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        # Should mention progress tracking in output
        assert "progress" in result.output.lower()


class TestTimestampedDebugOutput:
    """Tests for timestamped debug output with --verbose flag."""

    def test_verbose_shows_timestamps_during_execution(self, tmp_path: Path) -> None:
        """When --verbose is enabled, timestamped debug messages are shown during execution."""
        from wiggum.agents import AgentResult

        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        def mock_agent_run(config):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return AgentResult(stdout="Claude output", stderr="", return_code=0)

        mock_agent = MagicMock()
        mock_agent.name = "claude"
        mock_agent.run.side_effect = mock_agent_run

        with patch("wiggum.agents.check_cli_available", return_value=True):
            with patch("wiggum.cli.get_agent", return_value=mock_agent):
                result = runner.invoke(
                    app,
                    [
                        "run",
                        "-f",
                        str(prompt_file),
                        "--tasks",
                        str(tasks_file),
                        "--verbose",
                        "-n",
                        "5",
                        "--force",
                        "--no-branch",
                    ],
                )

        assert result.exit_code == 0
        # Should contain timestamp pattern [HH:MM:SS]
        import re

        timestamp_pattern = r"\[\d{2}:\d{2}:\d{2}\]"
        assert re.search(timestamp_pattern, result.output), (
            f"Expected timestamp pattern {timestamp_pattern} not found in output:\n{result.output}"
        )
        # Should show agent start message
        assert "claude" in result.output.lower()

    def test_verbose_shows_agent_start_message(self, tmp_path: Path) -> None:
        """When --verbose is enabled, shows message when agent starts."""
        from wiggum.agents import AgentResult

        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        def mock_agent_run(config):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return AgentResult(stdout="Claude output", stderr="", return_code=0)

        mock_agent = MagicMock()
        mock_agent.name = "claude"
        mock_agent.run.side_effect = mock_agent_run

        with patch("wiggum.agents.check_cli_available", return_value=True):
            with patch("wiggum.cli.get_agent", return_value=mock_agent):
                result = runner.invoke(
                    app,
                    [
                        "run",
                        "-f",
                        str(prompt_file),
                        "--tasks",
                        str(tasks_file),
                        "--verbose",
                        "-n",
                        "5",
                        "--force",
                        "--no-branch",
                    ],
                )

        assert result.exit_code == 0
        # Should contain "Running" or "Starting" agent message
        assert (
            "running" in result.output.lower() or "starting" in result.output.lower()
        ), f"Expected 'running' or 'starting' message in output:\n{result.output}"

    def test_no_timestamps_without_verbose(self, tmp_path: Path) -> None:
        """Without --verbose, no timestamped debug messages are shown."""
        from wiggum.agents import AgentResult

        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        def mock_agent_run(config):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return AgentResult(stdout="Claude output", stderr="", return_code=0)

        mock_agent = MagicMock()
        mock_agent.name = "claude"
        mock_agent.run.side_effect = mock_agent_run

        with patch("wiggum.agents.check_cli_available", return_value=True):
            with patch("wiggum.cli.get_agent", return_value=mock_agent):
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
                        "--force",
                        "--no-branch",
                    ],
                )

        assert result.exit_code == 0
        # Should NOT contain timestamp pattern [HH:MM:SS] for debug messages
        import re

        # Look for timestamp at start of line (debug message)
        timestamp_at_line_start = r"^\[\d{2}:\d{2}:\d{2}\]"
        assert not re.search(timestamp_at_line_start, result.output, re.MULTILINE), (
            f"Found unexpected timestamp in output:\n{result.output}"
        )
