"""Tests for removal of --prompt option (always use LOOP-PROMPT.md)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ralph_loop.cli import app

runner = CliRunner()


class TestPromptOptionRemoval:
    """Tests verifying --prompt option is removed and LOOP-PROMPT.md is required."""

    def test_run_without_prompt_file_errors(self, tmp_path: Path) -> None:
        """When LOOP-PROMPT.md doesn't exist and no -f specified, command errors."""
        import os

        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["run", "-n", "1"])
        finally:
            os.chdir(original_dir)

        assert result.exit_code != 0
        assert "LOOP-PROMPT.md" in result.output or "not found" in result.output.lower()

    def test_run_with_prompt_file_succeeds(self, tmp_path: Path) -> None:
        """When LOOP-PROMPT.md exists, run command reads from it."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("This is the loop prompt content")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] all done\n")

        with patch("ralph_loop.cli.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "-n",
                    "1",
                ],
            )

        assert result.exit_code == 0

    def test_run_with_custom_file_option(self, tmp_path: Path) -> None:
        """The -f/--file option allows specifying a custom prompt file."""
        custom_prompt = tmp_path / "custom-prompt.md"
        custom_prompt.write_text("Custom prompt content")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] done\n")

        with patch("ralph_loop.cli.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(custom_prompt),
                    "--tasks",
                    str(tasks_file),
                    "-n",
                    "1",
                ],
            )

        assert result.exit_code == 0

    def test_prompt_option_not_accepted(self, tmp_path: Path) -> None:
        """The -p/--prompt option should not be recognized."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test")

        result = runner.invoke(
            app,
            ["run", "-p", "inline prompt", "-f", str(prompt_file), "-n", "1"],
        )

        # Should fail because -p is not a valid option
        assert result.exit_code != 0
        # Error message should indicate unrecognized option
        assert (
            "no such option" in result.output.lower()
            or "unexpected" in result.output.lower()
            or "error" in result.output.lower()
        )

    def test_dry_run_shows_prompt_from_file(self, tmp_path: Path) -> None:
        """Dry run output shows prompt content read from file."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_content = "This is the test prompt from file"
        prompt_file.write_text(prompt_content)

        result = runner.invoke(
            app,
            ["run", "-f", str(prompt_file), "--dry-run"],
        )

        assert result.exit_code == 0
        assert prompt_content in result.output


class TestPromptFileDefault:
    """Tests for default LOOP-PROMPT.md behavior."""

    def test_default_prompt_file_is_loop_prompt_md(self, tmp_path: Path) -> None:
        """When no -f specified, defaults to LOOP-PROMPT.md in current directory."""
        import os

        # Create LOOP-PROMPT.md in tmp_path
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("Default prompt content")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] done\n")

        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("ralph_loop.cli.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                result = runner.invoke(
                    app,
                    ["run", "--tasks", str(tasks_file), "-n", "1"],
                )
        finally:
            os.chdir(original_dir)

        # Should succeed by reading LOOP-PROMPT.md
        assert result.exit_code == 0

    def test_missing_prompt_file_error_message(self, tmp_path: Path) -> None:
        """Error message clearly indicates LOOP-PROMPT.md is missing."""
        import os

        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["run", "-n", "1"])
        finally:
            os.chdir(original_dir)

        assert result.exit_code != 0
        assert "LOOP-PROMPT.md" in result.output
        assert "not found" in result.output.lower()
