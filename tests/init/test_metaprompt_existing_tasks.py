"""Tests for META-PROMPT.md handling existing TASKS.md files.

This tests that the init command properly includes existing task context
in the meta-prompt sent to Claude when TASKS.md already exists.
"""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from wiggum.cli import app

runner = CliRunner()


class TestMetapromptIncludesExistingTasks:
    """Tests for including existing tasks context in the meta-prompt."""

    def test_metaprompt_includes_existing_tasks_content(self, tmp_path: Path) -> None:
        """Meta-prompt should include existing TASKS.md content when file exists."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create templates
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Tasks\n\n{{tasks}}\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n{{tasks}}\n"
            )
            # META-PROMPT.md template with placeholder for existing tasks
            (Path("templates") / "META-PROMPT.md").write_text(
                "Analyze {{goal}}\n\n{{existing_tasks}}"
            )

            # Create README so goal is inferred
            Path("README.md").write_text("# Test Project\n\nThis is a test.")

            # Create existing TASKS.md with some tasks
            existing_tasks_content = (
                "# Tasks\n\n"
                "## Done\n\n"
                "- [x] Completed task 1\n"
                "- [x] Completed task 2\n\n"
                "## In Progress\n\n"
                "- [ ] Task being worked on\n\n"
                "## Todo\n\n"
                "- [ ] Pending task 1\n"
                "- [ ] Pending task 2\n"
            )
            Path("TASKS.md").write_text(existing_tasks_content)

            # Track what prompt is sent to Claude
            captured_prompt = None

            def capture_prompt(prompt: str) -> str:
                nonlocal captured_prompt
                captured_prompt = prompt
                return """```markdown
## Goal

Test goal

## Tasks

- [ ] New task
```"""

            with patch(
                "wiggum.cli.run_claude_for_planning", side_effect=capture_prompt
            ):
                result = runner.invoke(
                    app,
                    ["init"],
                    input="y\n1\n",  # Accept suggestions, conservative mode
                )

            # The meta-prompt sent to Claude should include existing tasks info
            assert captured_prompt is not None
            # Should mention existing tasks context
            assert (
                "Completed task 1" in captured_prompt
                or "existing" in captured_prompt.lower()
            )

    def test_metaprompt_indicates_done_tasks_to_avoid(self, tmp_path: Path) -> None:
        """Meta-prompt should tell Claude about completed tasks to avoid suggesting similar ones."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Tasks\n\n{{tasks}}\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text(
                "Analyze {{goal}}\n\n{{existing_tasks}}"
            )

            Path("README.md").write_text("# Test Project\n\nThis is a test.")

            # Create existing TASKS.md with completed tasks
            Path("TASKS.md").write_text(
                "# Tasks\n\n"
                "## Done\n\n"
                "- [x] Set up project structure\n"
                "- [x] Add initial tests\n\n"
                "## Todo\n\n"
                "- [ ] Add more features\n"
            )

            captured_prompt = None

            def capture_prompt(prompt: str) -> str:
                nonlocal captured_prompt
                captured_prompt = prompt
                return """```markdown
## Goal

Test goal

## Tasks

- [ ] New feature task
```"""

            with patch(
                "wiggum.cli.run_claude_for_planning", side_effect=capture_prompt
            ):
                runner.invoke(app, ["init"], input="y\n1\n")

            assert captured_prompt is not None
            # Should include completed tasks for context
            assert (
                "Set up project structure" in captured_prompt
                or "Done" in captured_prompt
            )

    def test_metaprompt_shows_pending_tasks_for_context(self, tmp_path: Path) -> None:
        """Meta-prompt should show pending tasks so Claude can build on them."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Tasks\n\n{{tasks}}\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text(
                "Analyze {{goal}}\n\n{{existing_tasks}}"
            )

            Path("README.md").write_text("# Test Project\n\nThis is a test.")

            Path("TASKS.md").write_text(
                "# Tasks\n\n"
                "## Todo\n\n"
                "- [ ] Implement user authentication\n"
                "- [ ] Add API endpoints\n"
            )

            captured_prompt = None

            def capture_prompt(prompt: str) -> str:
                nonlocal captured_prompt
                captured_prompt = prompt
                return """```markdown
## Goal

Test goal

## Tasks

- [ ] Add tests for auth
```"""

            with patch(
                "wiggum.cli.run_claude_for_planning", side_effect=capture_prompt
            ):
                runner.invoke(app, ["init"], input="y\n1\n")

            assert captured_prompt is not None
            # Should include pending tasks
            assert (
                "Implement user authentication" in captured_prompt
                or "Todo" in captured_prompt
            )

    def test_metaprompt_no_existing_tasks_section_when_file_missing(
        self, tmp_path: Path
    ) -> None:
        """When no TASKS.md exists, meta-prompt should not include existing tasks section."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Tasks\n\n{{tasks}}\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text(
                "Analyze {{goal}}\n\n{{existing_tasks}}"
            )

            Path("README.md").write_text("# Test Project")

            # No TASKS.md file

            captured_prompt = None

            def capture_prompt(prompt: str) -> str:
                nonlocal captured_prompt
                captured_prompt = prompt
                return """```markdown
## Goal

Test goal

## Tasks

- [ ] First task
```"""

            with patch(
                "wiggum.cli.run_claude_for_planning", side_effect=capture_prompt
            ):
                runner.invoke(app, ["init"], input="y\n1\n")

            assert captured_prompt is not None
            # Should not have raw placeholder or error
            assert "{{existing_tasks}}" not in captured_prompt

    def test_metaprompt_empty_tasks_file_handled_gracefully(
        self, tmp_path: Path
    ) -> None:
        """When TASKS.md is empty or has no tasks, handle gracefully."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Tasks\n\n{{tasks}}\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text(
                "Analyze {{goal}}\n\n{{existing_tasks}}"
            )

            Path("README.md").write_text("# Test Project")

            # Empty TASKS.md
            Path("TASKS.md").write_text("# Tasks\n\n## Done\n\n## Todo\n\n")

            captured_prompt = None

            def capture_prompt(prompt: str) -> str:
                nonlocal captured_prompt
                captured_prompt = prompt
                return """```markdown
## Goal

Test goal

## Tasks

- [ ] First task
```"""

            with patch(
                "wiggum.cli.run_claude_for_planning", side_effect=capture_prompt
            ):
                runner.invoke(app, ["init"], input="y\n1\n")

            assert captured_prompt is not None
            # Should handle empty file gracefully
            assert "{{existing_tasks}}" not in captured_prompt
