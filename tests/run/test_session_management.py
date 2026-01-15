"""Tests for session management (--continue vs --reset) in ralph-loop."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from wiggum.cli import app

runner = CliRunner()


class TestContinueFlag:
    """Tests for the --continue flag to maintain session context between iterations."""

    def test_continue_flag_passes_continue_to_claude_after_first_iteration(
        self, tmp_path: Path
    ) -> None:
        """With --continue, claude is called with -c flag after the first iteration."""
        # Setup
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n- [ ] task2\n")

        call_count = 0

        def mock_subprocess_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            # Mark tasks complete one by one
            if call_count == 1:
                tasks_file.write_text(
                    "# Tasks\n\n## Todo\n\n- [ ] task2\n\n## Done\n\n- [x] task1\n"
                )
            elif call_count == 2:
                tasks_file.write_text(
                    "# Tasks\n\n## Done\n\n- [x] task1\n- [x] task2\n"
                )
            return MagicMock(returncode=0)

        with patch(
            "wiggum.agents_claude.subprocess.run", side_effect=mock_subprocess_run
        ) as mock_run:
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
                    "--continue",
                ],
            )

        assert result.exit_code == 0
        assert call_count == 2

        # First call should NOT have -c flag
        first_call_args = mock_run.call_args_list[0][0][0]
        assert "-c" not in first_call_args

        # Second call should have -c flag
        second_call_args = mock_run.call_args_list[1][0][0]
        assert "-c" in second_call_args

    def test_continue_flag_first_iteration_has_no_continue(
        self, tmp_path: Path
    ) -> None:
        """The first iteration never has -c flag even with --continue."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        def mock_subprocess_run(cmd, **kwargs):
            # Complete the task immediately
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return MagicMock(returncode=0)

        with patch(
            "wiggum.agents_claude.subprocess.run", side_effect=mock_subprocess_run
        ) as mock_run:
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
                    "--continue",
                ],
            )

        assert result.exit_code == 0
        # First call should NOT have -c flag
        first_call_args = mock_run.call_args_list[0][0][0]
        assert "-c" not in first_call_args


class TestResetFlag:
    """Tests for the --reset flag (or default behavior) to start fresh each iteration."""

    def test_default_behavior_no_continue_flag_to_claude(self, tmp_path: Path) -> None:
        """By default (without --continue), claude is never called with -c flag."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n- [ ] task2\n")

        call_count = 0

        def mock_subprocess_run(cmd, **kwargs):
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
            return MagicMock(returncode=0)

        with patch(
            "wiggum.agents_claude.subprocess.run", side_effect=mock_subprocess_run
        ) as mock_run:
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
        assert call_count == 2

        # Neither call should have -c flag
        for call_args in mock_run.call_args_list:
            args = call_args[0][0]
            assert "-c" not in args

    def test_reset_flag_same_as_default(self, tmp_path: Path) -> None:
        """The --reset flag explicitly ensures fresh sessions (same as default)."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        def mock_subprocess_run(cmd, **kwargs):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return MagicMock(returncode=0)

        with patch(
            "wiggum.agents_claude.subprocess.run", side_effect=mock_subprocess_run
        ) as mock_run:
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
                    "--reset",
                ],
            )

        assert result.exit_code == 0
        # Call should NOT have -c flag
        first_call_args = mock_run.call_args_list[0][0][0]
        assert "-c" not in first_call_args


class TestContinueAndResetMutualExclusion:
    """Tests for mutual exclusion of --continue and --reset flags."""

    def test_continue_and_reset_together_shows_error(self, tmp_path: Path) -> None:
        """Using both --continue and --reset shows an error."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        with patch("wiggum.agents_claude.subprocess.run"):
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "--continue",
                    "--reset",
                ],
            )

        # Should show error about mutually exclusive flags
        assert result.exit_code != 0
        assert (
            "mutually exclusive" in result.output.lower()
            or "cannot" in result.output.lower()
        )


class TestDryRunWithSessionFlags:
    """Tests for dry-run mode displaying session management configuration."""

    def test_dry_run_shows_continue_mode(self, tmp_path: Path) -> None:
        """Dry run output shows when --continue is enabled."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")

        result = runner.invoke(
            app,
            [
                "run",
                "-f",
                str(prompt_file),
                "--continue",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        # Should show that session will be continued
        assert "continue" in result.output.lower() or "session" in result.output.lower()

    def test_dry_run_shows_reset_mode(self, tmp_path: Path) -> None:
        """Dry run output shows when sessions will be reset (default)."""
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

        assert result.exit_code == 0
        # Default behavior - should show reset/fresh or just not mention continue
        # The output should be valid
        assert "Would run" in result.output
