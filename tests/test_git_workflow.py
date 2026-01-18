"""Tests for the git safety features in the run command."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from wiggum.cli import app

runner = CliRunner()


class TestGitSafetyDryRun:
    """Tests for git safety dry run output."""

    def test_dry_run_shows_git_safety_enabled_by_default(self, tmp_path: Path) -> None:
        """Shows git safety is enabled by default."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Test task\n")
            result = runner.invoke(app, ["run", "--dry-run"])

        assert result.exit_code == 0
        assert "Git safety: enabled" in result.output

    def test_dry_run_shows_git_safety_disabled_with_no_branch(
        self, tmp_path: Path
    ) -> None:
        """Shows git safety disabled when --no-branch is used."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Test task\n")
            result = runner.invoke(app, ["run", "--dry-run", "--no-branch"])

        assert result.exit_code == 0
        assert "Git safety: disabled (--no-branch)" in result.output

    def test_dry_run_shows_git_safety_disabled_with_force(self, tmp_path: Path) -> None:
        """Shows git safety disabled when --force is used."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Test task\n")
            result = runner.invoke(app, ["run", "--dry-run", "--force"])

        assert result.exit_code == 0
        assert "Git safety: disabled (--force)" in result.output

    def test_dry_run_shows_pr_creation_when_enabled(self, tmp_path: Path) -> None:
        """Shows PR creation when --pr flag is used."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Test task\n")
            result = runner.invoke(app, ["run", "--dry-run", "--pr"])

        assert result.exit_code == 0
        assert "PR creation: enabled" in result.output

    def test_dry_run_shows_branch_prefix(self, tmp_path: Path) -> None:
        """Shows branch prefix in dry run."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Test task\n")
            result = runner.invoke(
                app, ["run", "--dry-run", "--branch-prefix", "myprefix"]
            )

        assert result.exit_code == 0
        assert "Branch prefix: myprefix" in result.output

    def test_dry_run_default_branch_prefix(self, tmp_path: Path) -> None:
        """Uses 'wiggum' as default branch prefix."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Test task\n")
            result = runner.invoke(app, ["run", "--dry-run"])

        assert result.exit_code == 0
        assert "Branch prefix: wiggum" in result.output


class TestGitSafetyConfig:
    """Tests for git safety configuration resolution."""

    def test_pr_from_config(self, tmp_path: Path) -> None:
        """Reads auto_pr setting from config file."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".wiggum.toml").write_text("[git]\nauto_pr = true")
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Test task\n")
            result = runner.invoke(app, ["run", "--dry-run"])

        assert result.exit_code == 0
        assert "PR creation: enabled" in result.output

    def test_branch_prefix_from_config(self, tmp_path: Path) -> None:
        """Reads branch_prefix from config file."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".wiggum.toml").write_text('[git]\nbranch_prefix = "feature"')
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Test task\n")
            result = runner.invoke(app, ["run", "--dry-run"])

        assert result.exit_code == 0
        assert "Branch prefix: feature" in result.output


class TestGitSafetyNonGitRepo:
    """Tests for git safety behavior in non-git repositories."""

    def test_non_git_repo_prompts_for_confirmation(self, tmp_path: Path) -> None:
        """Non-git repo asks for confirmation to proceed."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Test task\n")
            # Answer 'n' to the confirmation prompt
            with patch("wiggum.agents.check_cli_available", return_value=True):
                result = runner.invoke(app, ["run", "-n", "1"], input="n\n")

        assert result.exit_code == 0
        assert "Not a git repository" in result.output

    def test_non_git_repo_force_skips_prompt(self, tmp_path: Path) -> None:
        """--force skips the confirmation prompt in non-git repos."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Done\n\n- [x] Done\n")

            with patch("wiggum.agents.check_cli_available", return_value=True):
                with patch("wiggum.cli.get_agent") as mock_get_agent:
                    mock_agent = mock_get_agent.return_value
                    mock_agent.run.return_value.stdout = "output"
                    mock_agent.run.return_value.stderr = ""
                    mock_agent.run.return_value.return_code = 0
                    result = runner.invoke(app, ["run", "-n", "1", "--force"])

        # Should not prompt, just run (and exit immediately since tasks are done)
        assert "Not a git repository" not in result.output


class TestGitSafetyPrRequiresGitRepo:
    """Tests that --pr requires a git repository."""

    def test_pr_requires_git_repo(self, tmp_path: Path) -> None:
        """--pr flag requires a git repository."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("LOOP-PROMPT.md").write_text("Test prompt")
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Test task\n")

            with patch("wiggum.agents.check_cli_available", return_value=True):
                # Answer 'y' to proceed without git, but --pr should fail
                result = runner.invoke(app, ["run", "-n", "1", "--pr"], input="y\n")

        assert result.exit_code == 1
        assert "--pr requires a git repository" in result.output
