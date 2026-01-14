"""Tests for security constraint questions during init."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ralph_loop.cli import app

runner = CliRunner()


class TestInitSecurityQuestions:
    """Tests for security constraint options during init."""

    def test_init_creates_config_file_with_security_settings(
        self, tmp_path: Path
    ) -> None:
        """Init creates a .ralph-loop.toml config file with security settings."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            # Mock Claude to avoid actually calling it
            with patch("ralph_loop.cli.run_claude_for_planning", return_value=None):
                # Input: goal, doc files, task, empty line to end tasks, security choice (1=conservative)
                result = runner.invoke(
                    app,
                    ["init"],
                    input="Test project goal\nREADME.md\nTask 1\n\n1\n",
                )

            config_file = Path(".ralph-loop.toml")
            assert config_file.exists(), (
                f"Config file not created. Output: {result.output}"
            )

    def test_init_conservative_mode_creates_no_permissions(
        self, tmp_path: Path
    ) -> None:
        """Conservative mode (option 1) sets no special permissions."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            with patch("ralph_loop.cli.run_claude_for_planning", return_value=None):
                # Choose conservative mode (option 1)
                result = runner.invoke(
                    app,
                    ["init"],
                    input="Test project\nREADME.md\nTask 1\n\n1\n",
                )

            config_file = Path(".ralph-loop.toml")
            assert config_file.exists()
            content = config_file.read_text()
            assert "yolo = false" in content
            assert 'allow_paths = ""' in content

    def test_init_path_restricted_mode_stores_paths(self, tmp_path: Path) -> None:
        """Path-restricted mode (option 2) stores allowed paths."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            with patch("ralph_loop.cli.run_claude_for_planning", return_value=None):
                # Choose path-restricted mode (option 2) and provide paths
                result = runner.invoke(
                    app,
                    ["init"],
                    input="Test project\nREADME.md\nTask 1\n\n2\nsrc/,tests/\n",
                )

            config_file = Path(".ralph-loop.toml")
            assert config_file.exists(), f"Config not created. Output: {result.output}"
            content = config_file.read_text()
            assert "src/" in content
            assert "tests/" in content

    def test_init_yolo_mode_sets_dangerous_flag(self, tmp_path: Path) -> None:
        """YOLO mode (option 3) sets yolo = true in config."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            with patch("ralph_loop.cli.run_claude_for_planning", return_value=None):
                # Choose YOLO mode (option 3), confirm the warning
                result = runner.invoke(
                    app,
                    ["init"],
                    input="Test project\nREADME.md\nTask 1\n\n3\ny\n",
                )

            config_file = Path(".ralph-loop.toml")
            assert config_file.exists(), f"Config not created. Output: {result.output}"
            content = config_file.read_text()
            assert "yolo = true" in content

    def test_init_yolo_mode_shows_warning(self, tmp_path: Path) -> None:
        """YOLO mode shows a warning about security implications."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            with patch("ralph_loop.cli.run_claude_for_planning", return_value=None):
                # Choose YOLO mode (option 3)
                result = runner.invoke(
                    app,
                    ["init"],
                    input="Test project\nREADME.md\nTask 1\n\n3\ny\n",
                )

            # Check for warning in output
            assert (
                "warning" in result.output.lower()
                or "dangerous" in result.output.lower()
            )

    def test_init_yolo_mode_can_be_cancelled(self, tmp_path: Path) -> None:
        """User can cancel YOLO mode after seeing the warning."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            with patch("ralph_loop.cli.run_claude_for_planning", return_value=None):
                # Choose YOLO mode (option 3) but decline at warning, then choose conservative
                result = runner.invoke(
                    app,
                    ["init"],
                    input="Test project\nREADME.md\nTask 1\n\n3\nn\n1\n",
                )

            config_file = Path(".ralph-loop.toml")
            assert config_file.exists()
            content = config_file.read_text()
            # Should NOT have yolo = true since user cancelled
            assert "yolo = true" not in content


class TestRunReadsConfigFile:
    """Tests that run command reads from .ralph-loop.toml config."""

    def test_run_uses_config_yolo_setting(self, tmp_path: Path) -> None:
        """Run command uses yolo setting from config file."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create config file with yolo mode
            Path(".ralph-loop.toml").write_text("[security]\nyolo = true\n")
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Task 1\n")

            result = runner.invoke(app, ["run", "--dry-run"])

            assert "--dangerously-skip-permissions" in result.output

    def test_run_uses_config_allow_paths(self, tmp_path: Path) -> None:
        """Run command uses allow_paths setting from config file."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create config file with allowed paths
            Path(".ralph-loop.toml").write_text(
                '[security]\nallow_paths = "src/,tests/"\n'
            )
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Task 1\n")

            result = runner.invoke(app, ["run", "--dry-run"])

            assert "src/" in result.output
            assert "tests/" in result.output

    def test_run_cli_flags_override_config(self, tmp_path: Path) -> None:
        """CLI flags override config file settings."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create config file with conservative mode
            Path(".ralph-loop.toml").write_text("[security]\nyolo = false\n")
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Task 1\n")

            # Pass --yolo flag to override config
            result = runner.invoke(app, ["run", "--dry-run", "--yolo"])

            assert "--dangerously-skip-permissions" in result.output

    def test_run_works_without_config_file(self, tmp_path: Path) -> None:
        """Run command works when no config file exists."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Task 1\n")

            # Should not error out
            result = runner.invoke(app, ["run", "--dry-run"])

            assert result.exit_code == 0


class TestSecurityModeDisplay:
    """Tests for displaying security mode information."""

    def test_init_displays_security_options(self, tmp_path: Path) -> None:
        """Init command displays the three security options."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            with patch("ralph_loop.cli.run_claude_for_planning", return_value=None):
                result = runner.invoke(
                    app,
                    ["init"],
                    input="Test project\nREADME.md\nTask 1\n\n1\n",
                )

            # Check that security options are displayed
            assert "conservative" in result.output.lower() or "1)" in result.output
            assert "path" in result.output.lower() or "2)" in result.output
            assert "yolo" in result.output.lower() or "3)" in result.output
