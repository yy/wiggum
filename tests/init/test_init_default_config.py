"""Tests for default configuration values written during init."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from wiggum.cli import app, read_config

runner = CliRunner()


class TestInitWritesDefaultLoopConfig:
    """Tests for init writing default [loop] configuration."""

    def test_init_writes_default_max_iterations(self, tmp_path: Path) -> None:
        """Init writes default max_iterations to config file."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            with patch("wiggum.cli.run_claude_for_planning", return_value=None):
                result = runner.invoke(
                    app,
                    ["init"],
                    input="Test goal\nREADME.md\nTask 1\n\n1\n",
                )

            assert result.exit_code == 0, f"Init failed: {result.output}"

            config = read_config()
            assert "loop" in config, "Config should have [loop] section"
            assert "max_iterations" in config["loop"], (
                "Config should have max_iterations in [loop] section"
            )
            assert config["loop"]["max_iterations"] == 10, (
                "Default max_iterations should be 10"
            )

    def test_init_writes_loop_section_with_security(self, tmp_path: Path) -> None:
        """Init writes both [security] and [loop] sections."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            with patch("wiggum.cli.run_claude_for_planning", return_value=None):
                # Choose yolo mode (option 3) and confirm
                result = runner.invoke(
                    app,
                    ["init"],
                    input="Test goal\nREADME.md\nTask 1\n\n3\ny\n",
                )

            assert result.exit_code == 0, f"Init failed: {result.output}"

            config_file = Path(".ralph-loop.toml")
            content = config_file.read_text()

            # Should have both sections
            assert "[security]" in content
            assert "[loop]" in content
            assert "max_iterations" in content

    def test_config_file_format_readable(self, tmp_path: Path) -> None:
        """Config file is human-readable with expected format."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            with patch("wiggum.cli.run_claude_for_planning", return_value=None):
                result = runner.invoke(
                    app,
                    ["init"],
                    input="Test goal\nREADME.md\nTask 1\n\n1\n",
                )

            assert result.exit_code == 0

            content = Path(".ralph-loop.toml").read_text()
            # Should have the expected format
            assert "max_iterations = 10" in content
