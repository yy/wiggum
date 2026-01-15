"""Tests for init command merging tasks when TASKS.md exists."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from wiggum.cli import app

runner = CliRunner()


class TestInitMergesTasks:
    """Tests for init command updating TASKS.md when it already exists."""

    def test_init_merges_tasks_when_tasks_file_exists(self, tmp_path: Path) -> None:
        """Init adds new tasks to existing TASKS.md instead of failing."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create templates
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Tasks\n\n{{tasks}}\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            # Create README so goal is inferred
            Path("README.md").write_text("# Test Project\n\nThis is a test.")

            # Create existing TASKS.md with some tasks
            Path("TASKS.md").write_text(
                "# Tasks\n\n"
                "## Done\n\n"
                "- [x] Previously completed task\n\n"
                "## In Progress\n\n"
                "## Todo\n\n"
                "- [ ] Existing todo task\n"
            )

            # Mock Claude to return suggestions
            mock_output = """```markdown
## Goal

Test goal

## Tasks

- [ ] New task from Claude
- [ ] Another new task
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=mock_output
            ):
                # Accept Claude's suggestions, choose conservative security
                result = runner.invoke(
                    app,
                    ["init"],
                    input="y\n1\n",  # Accept suggestions, conservative mode
                )

            # Should succeed without --force
            assert result.exit_code == 0, f"Expected success. Output: {result.output}"

            # Existing tasks should be preserved
            content = Path("TASKS.md").read_text()
            assert "- [x] Previously completed task" in content
            assert "- [ ] Existing todo task" in content

            # New tasks should be added
            assert "- [ ] New task from Claude" in content
            assert "- [ ] Another new task" in content

    def test_init_does_not_duplicate_existing_tasks(self, tmp_path: Path) -> None:
        """Init does not add tasks that already exist in TASKS.md."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create templates
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Tasks\n\n{{tasks}}\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            # Create README so goal is inferred
            Path("README.md").write_text("# Test Project\n\nThis is a test.")

            # Create existing TASKS.md with a task
            Path("TASKS.md").write_text(
                "# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n- [ ] Existing task\n"
            )

            # Claude suggests the same task plus a new one
            mock_output = """```markdown
## Goal

Test goal

## Tasks

- [ ] Existing task
- [ ] Brand new task
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=mock_output
            ):
                result = runner.invoke(
                    app,
                    ["init"],
                    input="y\n1\n",
                )

            assert result.exit_code == 0

            content = Path("TASKS.md").read_text()
            # Should have exactly one "Existing task", not duplicated
            assert content.count("Existing task") == 1
            # Should have the new task
            assert "- [ ] Brand new task" in content

    def test_init_preserves_done_and_in_progress_sections(self, tmp_path: Path) -> None:
        """Init preserves Done and In Progress sections when merging."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Tasks\n\n{{tasks}}\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            # Create README so goal is inferred
            Path("README.md").write_text("# Test Project\n\nThis is a test.")

            Path("TASKS.md").write_text(
                "# Tasks\n\n"
                "## Done\n\n"
                "- [x] Completed task 1\n"
                "- [x] Completed task 2\n\n"
                "## In Progress\n\n"
                "- [ ] Task being worked on\n\n"
                "## Todo\n\n"
                "- [ ] Pending task\n"
            )

            mock_output = """```markdown
## Goal

Test goal

## Tasks

- [ ] New task
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=mock_output
            ):
                result = runner.invoke(
                    app,
                    ["init"],
                    input="y\n1\n",
                )

            assert result.exit_code == 0

            content = Path("TASKS.md").read_text()
            # Done section preserved
            assert "- [x] Completed task 1" in content
            assert "- [x] Completed task 2" in content
            # In Progress section preserved
            assert "- [ ] Task being worked on" in content
            # Todo tasks preserved and new one added
            assert "- [ ] Pending task" in content
            assert "- [ ] New task" in content

    def test_init_errors_if_loop_prompt_exists_without_force(
        self, tmp_path: Path
    ) -> None:
        """Init still errors if LOOP-PROMPT.md exists (no merge for that file)."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text("## Goal\n\n{{goal}}\n")
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            # Create existing LOOP-PROMPT.md
            Path("LOOP-PROMPT.md").write_text("Existing loop prompt")

            with patch("wiggum.cli.run_claude_for_planning", return_value=None):
                result = runner.invoke(
                    app,
                    ["init"],
                    input="Test goal\nREADME.md\nTask 1\n\n1\n",
                )

            # Should error because LOOP-PROMPT.md exists
            assert result.exit_code == 1
            assert "exists" in result.output.lower() or "force" in result.output.lower()

    def test_init_force_overwrites_tasks_file(self, tmp_path: Path) -> None:
        """With --force, init completely overwrites TASKS.md."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Tasks\n\n{{tasks}}\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            # Create README so goal is inferred
            Path("README.md").write_text("# Test Project\n\nThis is a test.")

            # Create existing TASKS.md with tasks that should be overwritten
            Path("TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n- [ ] Task to be overwritten\n"
            )

            mock_output = """```markdown
## Goal

Test goal

## Tasks

- [ ] New task only
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=mock_output
            ):
                result = runner.invoke(
                    app,
                    ["init", "--force"],
                    input="y\n1\n",
                )

            assert result.exit_code == 0

            content = Path("TASKS.md").read_text()
            # Old task should be gone
            assert "Task to be overwritten" not in content
            # Only new task should exist
            assert "- [ ] New task only" in content

    def test_init_shows_merge_message_when_updating(self, tmp_path: Path) -> None:
        """Init shows a message indicating it's updating existing tasks."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Tasks\n\n{{tasks}}\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            # Create README so goal is inferred
            Path("README.md").write_text("# Test Project\n\nThis is a test.")

            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Existing task\n")

            mock_output = """```markdown
## Goal

Test goal

## Tasks

- [ ] New task
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=mock_output
            ):
                result = runner.invoke(
                    app,
                    ["init"],
                    input="y\n1\n",
                )

            assert result.exit_code == 0
            # Should indicate updating/merging
            output_lower = result.output.lower()
            assert (
                "updat" in output_lower
                or "merg" in output_lower
                or "add" in output_lower
            )

    def test_init_manual_entry_merges_with_existing(self, tmp_path: Path) -> None:
        """Manual task entry also merges with existing TASKS.md."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Tasks\n\n{{tasks}}\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] Old task\n")

            # Claude returns nothing, so user enters manually
            with patch("wiggum.cli.run_claude_for_planning", return_value=None):
                result = runner.invoke(
                    app,
                    ["init"],
                    input="My goal\nREADME.md\nManual task 1\nManual task 2\n\n1\n",
                )

            assert result.exit_code == 0

            content = Path("TASKS.md").read_text()
            # Old task preserved
            assert "- [ ] Old task" in content
            # New manual tasks added
            assert "- [ ] Manual task 1" in content
            assert "- [ ] Manual task 2" in content
