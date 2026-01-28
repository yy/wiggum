"""Tests for the wiggum clean command."""

from pathlib import Path

from typer.testing import CliRunner

from wiggum.cli import app

runner = CliRunner()


class TestCleanCommand:
    """Tests for the `wiggum clean` command."""

    def test_clean_removes_config_files(self, tmp_path: Path) -> None:
        """Removes LOOP-PROMPT.md and .wiggum.toml by default."""
        loop_prompt = tmp_path / "LOOP-PROMPT.md"
        config = tmp_path / ".wiggum.toml"
        tasks = tmp_path / "TASKS.md"

        loop_prompt.write_text("# Prompt\n")
        config.write_text("[loop]\n")
        tasks.write_text("# Tasks\n\n## Todo\n\n- [ ] Task\n")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text(loop_prompt.read_text())
            Path(".wiggum.toml").write_text(config.read_text())
            Path("TASKS.md").write_text(tasks.read_text())

            result = runner.invoke(app, ["clean", "--force", "--keep-tasks"])

            assert not Path("LOOP-PROMPT.md").exists()
            assert not Path(".wiggum.toml").exists()
            assert Path("TASKS.md").exists()

        assert result.exit_code == 0
        assert "Removed" in result.output

    def test_clean_keeps_tasks_by_default(self, tmp_path: Path) -> None:
        """TASKS.md is kept by default when using --force."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("# Prompt\n")
            Path(".wiggum.toml").write_text("[loop]\n")
            Path("TASKS.md").write_text("# Tasks\n")

            result = runner.invoke(app, ["clean", "--force"])

            assert not Path("LOOP-PROMPT.md").exists()
            assert not Path(".wiggum.toml").exists()
            # Without --keep-tasks or --all, --force keeps TASKS.md
            assert Path("TASKS.md").exists()

        assert result.exit_code == 0
        assert "Kept TASKS.md" in result.output

    def test_clean_all_removes_tasks_too(self, tmp_path: Path) -> None:
        """--all flag removes TASKS.md as well."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("# Prompt\n")
            Path(".wiggum.toml").write_text("[loop]\n")
            Path("TASKS.md").write_text("# Tasks\n")

            result = runner.invoke(app, ["clean", "--all", "--force"])

            assert not Path("LOOP-PROMPT.md").exists()
            assert not Path(".wiggum.toml").exists()
            assert not Path("TASKS.md").exists()

        assert result.exit_code == 0

    def test_clean_keep_tasks_explicit(self, tmp_path: Path) -> None:
        """--keep-tasks explicitly keeps TASKS.md."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("# Prompt\n")
            Path(".wiggum.toml").write_text("[loop]\n")
            Path("TASKS.md").write_text("# Tasks\n")

            result = runner.invoke(app, ["clean", "--keep-tasks", "--force"])

            assert not Path("LOOP-PROMPT.md").exists()
            assert not Path(".wiggum.toml").exists()
            assert Path("TASKS.md").exists()

        assert result.exit_code == 0
        assert "Kept TASKS.md" in result.output

    def test_clean_dry_run_shows_what_would_be_removed(self, tmp_path: Path) -> None:
        """--dry-run shows files without actually removing them."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("# Prompt\n")
            Path(".wiggum.toml").write_text("[loop]\n")
            Path("TASKS.md").write_text("# Tasks\n")

            result = runner.invoke(app, ["clean", "--dry-run"])

            # Files should still exist
            assert Path("LOOP-PROMPT.md").exists()
            assert Path(".wiggum.toml").exists()
            assert Path("TASKS.md").exists()

        assert result.exit_code == 0
        assert "Would remove" in result.output
        assert "LOOP-PROMPT.md" in result.output
        assert ".wiggum.toml" in result.output
        assert "Would keep" in result.output
        assert "TASKS.md" in result.output

    def test_clean_dry_run_all_shows_tasks_removal(self, tmp_path: Path) -> None:
        """--dry-run --all shows TASKS.md would be removed."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("# Prompt\n")
            Path(".wiggum.toml").write_text("[loop]\n")
            Path("TASKS.md").write_text("# Tasks\n")

            result = runner.invoke(app, ["clean", "--dry-run", "--all"])

            # Files should still exist
            assert Path("LOOP-PROMPT.md").exists()
            assert Path(".wiggum.toml").exists()
            assert Path("TASKS.md").exists()

        assert result.exit_code == 0
        assert "Would remove" in result.output
        assert "TASKS.md" in result.output

    def test_clean_no_files_exist(self, tmp_path: Path) -> None:
        """Shows message when no wiggum files are found."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["clean"])

        assert result.exit_code == 0
        assert "No wiggum files found" in result.output

    def test_clean_partial_files_exist(self, tmp_path: Path) -> None:
        """Only removes files that exist."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".wiggum.toml").write_text("[loop]\n")
            # No LOOP-PROMPT.md or TASKS.md

            result = runner.invoke(app, ["clean", "--force"])

            assert not Path(".wiggum.toml").exists()

        assert result.exit_code == 0
        assert "Removed" in result.output
        assert ".wiggum.toml" in result.output

    def test_clean_requires_confirmation_without_force(self, tmp_path: Path) -> None:
        """Prompts for confirmation without --force."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("# Prompt\n")
            Path(".wiggum.toml").write_text("[loop]\n")

            # Answer 'n' to confirmation
            result = runner.invoke(app, ["clean"], input="n\n")

            # Files should still exist
            assert Path("LOOP-PROMPT.md").exists()
            assert Path(".wiggum.toml").exists()

        assert result.exit_code == 0
        assert "Remove these files?" in result.output

    def test_clean_confirmation_yes(self, tmp_path: Path) -> None:
        """Files are removed when user confirms."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("# Prompt\n")
            Path(".wiggum.toml").write_text("[loop]\n")

            result = runner.invoke(app, ["clean", "--keep-tasks"], input="y\n")

            assert not Path("LOOP-PROMPT.md").exists()
            assert not Path(".wiggum.toml").exists()

        assert result.exit_code == 0
        assert "Removed" in result.output

    def test_clean_prompts_about_tasks_when_present(self, tmp_path: Path) -> None:
        """Asks about TASKS.md when it exists and --keep-tasks/--all not specified."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("# Prompt\n")
            Path(".wiggum.toml").write_text("[loop]\n")
            Path("TASKS.md").write_text("# Tasks\n")

            # Answer 'n' to tasks question, 'y' to removal
            result = runner.invoke(app, ["clean"], input="n\ny\n")

            assert not Path("LOOP-PROMPT.md").exists()
            assert not Path(".wiggum.toml").exists()
            assert Path("TASKS.md").exists()

        assert result.exit_code == 0
        assert "TASKS.md contains your task list" in result.output

    def test_clean_prompts_tasks_answer_yes(self, tmp_path: Path) -> None:
        """TASKS.md is removed when user confirms."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("# Prompt\n")
            Path(".wiggum.toml").write_text("[loop]\n")
            Path("TASKS.md").write_text("# Tasks\n")

            # Answer 'y' to tasks question, 'y' to removal
            result = runner.invoke(app, ["clean"], input="y\ny\n")

            assert not Path("LOOP-PROMPT.md").exists()
            assert not Path(".wiggum.toml").exists()
            assert not Path("TASKS.md").exists()

        assert result.exit_code == 0

    def test_clean_all_and_keep_tasks_conflict(self, tmp_path: Path) -> None:
        """--all and --keep-tasks are mutually exclusive."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("# Prompt\n")

            result = runner.invoke(app, ["clean", "--all", "--keep-tasks"])

        # Typer returns 2 for usage errors
        assert result.exit_code != 0
        # Should mention the conflict
        assert (
            "mutually exclusive" in result.output.lower()
            or "cannot" in result.output.lower()
        )

    def test_clean_shows_removed_file_names(self, tmp_path: Path) -> None:
        """Output includes names of removed files."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("# Prompt\n")
            Path(".wiggum.toml").write_text("[loop]\n")

            result = runner.invoke(app, ["clean", "--force"])

        assert result.exit_code == 0
        assert "LOOP-PROMPT.md" in result.output
        assert ".wiggum.toml" in result.output

    def test_clean_does_not_remove_backups(self, tmp_path: Path) -> None:
        """Backup files (.bak) are not removed."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("# Prompt\n")
            Path("LOOP-PROMPT.md.bak").write_text("# Old Prompt\n")
            Path(".wiggum.toml").write_text("[loop]\n")
            Path(".wiggum.toml.bak").write_text("[old]\n")

            result = runner.invoke(app, ["clean", "--force"])

            assert not Path("LOOP-PROMPT.md").exists()
            assert Path("LOOP-PROMPT.md.bak").exists()
            assert not Path(".wiggum.toml").exists()
            assert Path(".wiggum.toml.bak").exists()

        assert result.exit_code == 0

    def test_clean_only_tasks_exist(self, tmp_path: Path) -> None:
        """When only TASKS.md exists, shows appropriate message."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("TASKS.md").write_text("# Tasks\n")

            result = runner.invoke(app, ["clean", "--keep-tasks"])

        assert result.exit_code == 0
        # No config files to remove
        assert (
            "No wiggum files found" in result.output
            or "nothing to remove" in result.output.lower()
        )

    def test_clean_only_tasks_with_all(self, tmp_path: Path) -> None:
        """When only TASKS.md exists and --all is used, removes it."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("TASKS.md").write_text("# Tasks\n")

            result = runner.invoke(app, ["clean", "--all", "--force"])

            assert not Path("TASKS.md").exists()

        assert result.exit_code == 0
        assert "Removed" in result.output
        assert "TASKS.md" in result.output
