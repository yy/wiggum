"""Tests for security constraint questions during init."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from wiggum.cli import app

runner = CliRunner()


class TestInitSecurityQuestions:
    """Tests for security constraint options during init."""

    def test_init_creates_config_file_with_security_settings(
        self, tmp_path: Path
    ) -> None:
        """Init creates a .wiggum.toml config file with security settings."""
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
            with patch(
                "wiggum.runner.run_claude_for_planning", return_value=(None, None)
            ):
                # Input: doc files, task, empty line to end tasks, security choice (1=conservative), git (n)
                result = runner.invoke(
                    app,
                    ["init"],
                    input="README.md\nTask 1\n\n1\nn\n",
                )

            config_file = Path(".wiggum.toml")
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

            with patch(
                "wiggum.runner.run_claude_for_planning", return_value=(None, None)
            ):
                # Choose conservative mode (option 1), git (n)
                result = runner.invoke(
                    app,
                    ["init"],
                    input="README.md\nTask 1\n\n1\nn\n",
                )

            config_file = Path(".wiggum.toml")
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

            with patch(
                "wiggum.runner.run_claude_for_planning", return_value=(None, None)
            ):
                # Choose path-restricted mode (option 2), provide paths, git (n)
                result = runner.invoke(
                    app,
                    ["init"],
                    input="README.md\nTask 1\n\n2\nsrc/,tests/\nn\n",
                )

            config_file = Path(".wiggum.toml")
            assert config_file.exists(), f"Config not created. Output: {result.output}"
            content = config_file.read_text()
            assert "src/" in content
            assert "tests/" in content

    def test_init_yolo_mode_sets_flag(self, tmp_path: Path) -> None:
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

            with patch(
                "wiggum.runner.run_claude_for_planning", return_value=(None, None)
            ):
                # Choose YOLO mode (option 3), git (n)
                result = runner.invoke(
                    app,
                    ["init"],
                    input="README.md\nTask 1\n\n3\nn\n",
                )

            config_file = Path(".wiggum.toml")
            assert config_file.exists(), f"Config not created. Output: {result.output}"
            content = config_file.read_text()
            assert "yolo = true" in content


class TestRunReadsConfigFile:
    """Tests that run command reads from .wiggum.toml config."""

    def test_run_uses_config_yolo_setting(self, tmp_path: Path) -> None:
        """Run command uses yolo setting from config file."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create config file with yolo mode
            Path(".wiggum.toml").write_text("[security]\nyolo = true\n")
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Task 1\n")

            result = runner.invoke(app, ["run", "--dry-run"])

            assert "--dangerously-skip-permissions" in result.output

    def test_run_uses_config_allow_paths(self, tmp_path: Path) -> None:
        """Run command uses allow_paths setting from config file."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create config file with allowed paths
            Path(".wiggum.toml").write_text('[security]\nallow_paths = "src/,tests/"\n')
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Task 1\n")

            result = runner.invoke(app, ["run", "--dry-run"])

            assert "src/" in result.output
            assert "tests/" in result.output

    def test_run_cli_flags_override_config(self, tmp_path: Path) -> None:
        """CLI flags override config file settings."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create config file with conservative mode
            Path(".wiggum.toml").write_text("[security]\nyolo = false\n")
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

            with patch(
                "wiggum.runner.run_claude_for_planning", return_value=(None, None)
            ):
                result = runner.invoke(
                    app,
                    ["init"],
                    input="README.md\nTask 1\n\n1\nn\n",
                )

            # Check that security options are displayed
            assert "conservative" in result.output.lower() or "1)" in result.output
            assert "path" in result.output.lower() or "2)" in result.output
            assert "yolo" in result.output.lower() or "3)" in result.output


class TestInitUpdatesGitignore:
    """Tests for .gitignore updates during init."""

    def test_init_adds_wiggum_to_existing_gitignore(self, tmp_path: Path) -> None:
        """Init adds all wiggum entries to existing .gitignore."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")
            # Create existing .gitignore
            Path(".gitignore").write_text("node_modules/\n.env\n")

            with patch(
                "wiggum.runner.run_claude_for_planning", return_value=(None, None)
            ):
                result = runner.invoke(
                    app,
                    ["init"],
                    input="README.md\nTask 1\n\n1\nn\n",
                )

            assert result.exit_code == 0, f"Init failed: {result.output}"
            gitignore_content = Path(".gitignore").read_text()
            assert ".wiggum/" in gitignore_content
            assert "LOOP-PROMPT.md" in gitignore_content
            assert "TASKS.md" in gitignore_content
            assert ".wiggum.toml" in gitignore_content

    def test_init_preserves_existing_gitignore_entries(self, tmp_path: Path) -> None:
        """Init preserves existing .gitignore entries."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")
            # Create existing .gitignore
            Path(".gitignore").write_text("node_modules/\n.env\n")

            with patch(
                "wiggum.runner.run_claude_for_planning", return_value=(None, None)
            ):
                result = runner.invoke(
                    app,
                    ["init"],
                    input="README.md\nTask 1\n\n1\nn\n",
                )

            assert result.exit_code == 0
            gitignore_content = Path(".gitignore").read_text()
            assert "node_modules/" in gitignore_content
            assert ".env" in gitignore_content

    def test_init_does_not_duplicate_wiggum_in_gitignore(self, tmp_path: Path) -> None:
        """Init does not add entries already in .gitignore."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")
            # Create .gitignore with all wiggum entries already present
            Path(".gitignore").write_text(
                ".wiggum/\nLOOP-PROMPT.md\nTASKS.md\n.wiggum.toml\nnode_modules/\n"
            )

            with patch(
                "wiggum.runner.run_claude_for_planning", return_value=(None, None)
            ):
                result = runner.invoke(
                    app,
                    ["init"],
                    input="README.md\nTask 1\n\n1\nn\n",
                )

            assert result.exit_code == 0
            gitignore_content = Path(".gitignore").read_text()
            # Each should appear only once
            assert gitignore_content.count(".wiggum/") == 1
            assert gitignore_content.count("LOOP-PROMPT.md") == 1
            assert gitignore_content.count("TASKS.md") == 1
            assert gitignore_content.count(".wiggum.toml") == 1

    def test_init_creates_gitignore_if_missing(self, tmp_path: Path) -> None:
        """Init creates .gitignore with wiggum entries if it doesn't exist."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            with patch(
                "wiggum.runner.run_claude_for_planning", return_value=(None, None)
            ):
                result = runner.invoke(
                    app,
                    ["init"],
                    input="README.md\nTask 1\n\n1\nn\n",
                )

            assert result.exit_code == 0
            assert Path(".gitignore").exists()
            gitignore_content = Path(".gitignore").read_text()
            assert ".wiggum/" in gitignore_content
            assert "LOOP-PROMPT.md" in gitignore_content
            assert "TASKS.md" in gitignore_content
            assert ".wiggum.toml" in gitignore_content
