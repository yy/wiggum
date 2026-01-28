"""Tests for the upgrade command."""

from pathlib import Path
from typer.testing import CliRunner

from wiggum.cli import app

runner = CliRunner()


class TestUpgradeCommand:
    """Test the upgrade command."""

    def test_upgrade_shows_help(self) -> None:
        """Test that upgrade command has help text."""
        result = runner.invoke(app, ["upgrade", "--help"])
        assert result.exit_code == 0
        assert "upgrade" in result.output.lower()

    def test_upgrade_no_files_suggests_init(self, tmp_path: Path) -> None:
        """Test upgrade when no wiggum files exist suggests running init."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = runner.invoke(app, ["upgrade"])
            assert result.exit_code == 1
            assert "wiggum init" in result.output.lower()
        finally:
            os.chdir(original_cwd)

    def test_upgrade_dry_run_shows_changes(self, tmp_path: Path) -> None:
        """Test that --dry-run shows changes without modifying."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            # Create an old version LOOP-PROMPT.md
            prompt_file = tmp_path / "LOOP-PROMPT.md"
            prompt_file.write_text("Old content\n<!-- wiggum-template: 0.4.0 -->")

            result = runner.invoke(app, ["upgrade", "--dry-run"])

            # Should show what would change
            assert "LOOP-PROMPT.md" in result.output
            # Should not modify the file
            assert (
                prompt_file.read_text()
                == "Old content\n<!-- wiggum-template: 0.4.0 -->"
            )
        finally:
            os.chdir(original_cwd)

    def test_upgrade_creates_backup(self, tmp_path: Path) -> None:
        """Test that upgrade creates backup of LOOP-PROMPT.md."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            # Create an old version LOOP-PROMPT.md
            prompt_file = tmp_path / "LOOP-PROMPT.md"
            old_content = "Old content\n<!-- wiggum-template: 0.4.0 -->"
            prompt_file.write_text(old_content)

            runner.invoke(app, ["upgrade", "--force"])

            # Should create backup
            backup_file = tmp_path / "LOOP-PROMPT.md.bak"
            assert backup_file.exists()
            assert backup_file.read_text() == old_content
        finally:
            os.chdir(original_cwd)

    def test_upgrade_no_backup_flag(self, tmp_path: Path) -> None:
        """Test that --no-backup skips backup creation."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            prompt_file = tmp_path / "LOOP-PROMPT.md"
            prompt_file.write_text("Old content\n<!-- wiggum-template: 0.4.0 -->")

            runner.invoke(app, ["upgrade", "--force", "--no-backup"])

            backup_file = tmp_path / "LOOP-PROMPT.md.bak"
            assert not backup_file.exists()
        finally:
            os.chdir(original_cwd)

    def test_upgrade_force_skips_confirmation(self, tmp_path: Path) -> None:
        """Test that --force skips confirmation prompt."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            prompt_file = tmp_path / "LOOP-PROMPT.md"
            prompt_file.write_text("Old content\n<!-- wiggum-template: 0.4.0 -->")

            result = runner.invoke(app, ["upgrade", "--force"])

            # Should not ask for confirmation
            assert "Upgrade?" not in result.output
            assert result.exit_code == 0
        finally:
            os.chdir(original_cwd)

    def test_upgrade_prompt_only(self, tmp_path: Path) -> None:
        """Test that 'upgrade prompt' only upgrades LOOP-PROMPT.md."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            prompt_file = tmp_path / "LOOP-PROMPT.md"
            prompt_file.write_text("Old content\n<!-- wiggum-template: 0.4.0 -->")

            config_file = tmp_path / ".wiggum.toml"
            config_content = "[security]\nyolo = true\n"
            config_file.write_text(config_content)

            result = runner.invoke(app, ["upgrade", "prompt", "--force"])

            # LOOP-PROMPT.md should be updated
            assert "wiggum-template: 0.5.0" in prompt_file.read_text()
            # Config should be unchanged
            assert config_file.read_text() == config_content
        finally:
            os.chdir(original_cwd)

    def test_upgrade_config_only(self, tmp_path: Path) -> None:
        """Test that 'upgrade config' only upgrades .wiggum.toml."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            prompt_file = tmp_path / "LOOP-PROMPT.md"
            old_prompt = "Old content\n<!-- wiggum-template: 0.4.0 -->"
            prompt_file.write_text(old_prompt)

            config_file = tmp_path / ".wiggum.toml"
            config_file.write_text("[security]\nyolo = true\n")

            runner.invoke(app, ["upgrade", "config", "--force"])

            # LOOP-PROMPT.md should be unchanged
            assert prompt_file.read_text() == old_prompt
            # Config should have new options
            config_content = config_file.read_text()
            assert "security" in config_content
        finally:
            os.chdir(original_cwd)

    def test_upgrade_preserves_user_values(self, tmp_path: Path) -> None:
        """Test that upgrade preserves existing user config values."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            config_file = tmp_path / ".wiggum.toml"
            config_file.write_text(
                '[security]\nyolo = true\nallow_paths = "src/"\n\n[loop]\nmax_iterations = 20\n'
            )

            runner.invoke(app, ["upgrade", "config", "--force"])

            # User values should be preserved
            config_content = config_file.read_text()
            assert "yolo = true" in config_content
            assert "max_iterations = 20" in config_content
        finally:
            os.chdir(original_cwd)

    def test_upgrade_invalid_target(self, tmp_path: Path) -> None:
        """Test that invalid target shows error."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            # Create a file so we don't get "no files" error
            prompt_file = tmp_path / "LOOP-PROMPT.md"
            prompt_file.write_text("content")

            result = runner.invoke(app, ["upgrade", "invalid"])

            assert result.exit_code == 1
            assert "Unknown target" in result.output
        finally:
            os.chdir(original_cwd)


class TestVersionParsing:
    """Test version detection from files."""

    def test_extract_version_from_template(self) -> None:
        """Test extracting version from template file."""
        from wiggum.upgrade import extract_template_version

        content = "Some content\n<!-- wiggum-template: 0.5.0 -->\nMore content"
        version = extract_template_version(content)
        assert version == "0.5.0"

    def test_extract_version_no_tag(self) -> None:
        """Test extracting version when no tag exists."""
        from wiggum.upgrade import extract_template_version

        content = "Some content without version tag"
        version = extract_template_version(content)
        assert version is None

    def test_compare_versions(self) -> None:
        """Test version comparison logic."""
        from wiggum.upgrade import is_version_outdated

        assert is_version_outdated("0.4.0", "0.5.0") is True
        assert is_version_outdated("0.5.0", "0.5.0") is False
        assert is_version_outdated("0.5.1", "0.5.0") is False
        assert is_version_outdated(None, "0.5.0") is True


class TestConfigUpgrade:
    """Test config file upgrade logic."""

    def test_get_missing_config_options(self) -> None:
        """Test detection of missing config options."""
        from wiggum.upgrade import get_missing_config_options

        existing = {"security": {"yolo": True}}
        missing = get_missing_config_options(existing)

        # Should detect missing sections/options
        assert "loop" in missing or any("loop" in str(m) for m in missing)

    def test_merge_config_preserves_values(self) -> None:
        """Test that merge preserves existing values."""
        from wiggum.upgrade import merge_config_with_defaults

        existing = {"security": {"yolo": True, "allow_paths": "src/"}}
        merged = merge_config_with_defaults(existing)

        # Original values should be preserved
        assert merged["security"]["yolo"] is True
        assert merged["security"]["allow_paths"] == "src/"


class TestTasksUpgrade:
    """Test TASKS.md upgrade logic."""

    def test_tasks_file_needs_upgrade_missing_sections(self) -> None:
        """Test detection of missing sections in TASKS.md."""
        from wiggum.upgrade import tasks_file_needs_upgrade

        # Missing ## Todo section
        content = "# Tasks\n\n## Done\n\n- [x] Task 1\n"
        assert tasks_file_needs_upgrade(content) is True

        # Has all sections
        content = "# Tasks\n\n## Todo\n\n- [ ] Task 1\n\n## Done\n"
        assert tasks_file_needs_upgrade(content) is False

    def test_add_missing_sections(self) -> None:
        """Test adding missing sections to TASKS.md."""
        from wiggum.upgrade import add_missing_task_sections

        content = "# Tasks\n\n## Done\n\n- [x] Task 1\n"
        upgraded = add_missing_task_sections(content)

        assert "## Todo" in upgraded
        assert "## Done" in upgraded
        # Should preserve existing tasks
        assert "- [x] Task 1" in upgraded
