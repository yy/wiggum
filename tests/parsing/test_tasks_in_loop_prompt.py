"""Tests for embedding tasks in LOOP-PROMPT.md during init.

This tests that when ralph-loop init runs, the generated LOOP-PROMPT.md
includes the tasks inline (from TASKS.md) so the agent has all context
in a single prompt file.
"""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from wiggum.cli import app

runner = CliRunner()


class TestTasksEmbeddingInLoopPrompt:
    """Tests for embedding tasks in LOOP-PROMPT.md."""

    def test_loop_prompt_template_has_tasks_placeholder(self) -> None:
        """The LOOP-PROMPT.md template should have a {{tasks}} placeholder."""
        template_path = (
            Path(__file__).parent.parent.parent / "templates" / "LOOP-PROMPT.md"
        )
        assert template_path.exists(), "LOOP-PROMPT.md template not found"
        content = template_path.read_text()
        assert "{{tasks}}" in content, (
            "LOOP-PROMPT.md template should have {{tasks}} placeholder"
        )

    def test_init_embeds_tasks_in_loop_prompt(self, tmp_path: Path) -> None:
        """Init command should embed tasks into LOOP-PROMPT.md."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Tasks\n\n{{tasks}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            with patch("wiggum.cli.run_claude_for_planning", return_value=None):
                result = runner.invoke(
                    app,
                    ["init"],
                    input="Build a CLI tool\nREADME.md\nImplement login\nAdd tests\n\n1\n",
                )

            assert result.exit_code == 0, f"Init failed: {result.output}"

            loop_prompt = Path("LOOP-PROMPT.md")
            assert loop_prompt.exists(), "LOOP-PROMPT.md not created"
            content = loop_prompt.read_text()

            # Tasks should be embedded in the prompt
            assert "- [ ] Implement login" in content, (
                f"Tasks not embedded in LOOP-PROMPT.md. Content:\n{content}"
            )
            assert "- [ ] Add tests" in content, (
                f"Tasks not embedded in LOOP-PROMPT.md. Content:\n{content}"
            )

    def test_init_embeds_tasks_from_claude_suggestions(self, tmp_path: Path) -> None:
        """Init should embed Claude-suggested tasks in LOOP-PROMPT.md."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Tasks\n\n{{tasks}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")
            # Create README so the init flow skips the goal prompt
            Path("README.md").write_text("# Test Project\n\nA REST API project.")

            # Mock Claude to return suggested tasks
            mock_output = """```markdown
## Goal

Build a REST API

## Tasks

- [ ] Set up project structure
- [ ] Implement user endpoints
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=mock_output
            ):
                # Accept Claude's suggestions with 'y', then conservative mode
                result = runner.invoke(
                    app,
                    ["init"],
                    input="y\n1\n",  # Accept suggestions, conservative mode
                )

            assert result.exit_code == 0, f"Init failed: {result.output}"

            loop_prompt = Path("LOOP-PROMPT.md")
            content = loop_prompt.read_text()

            # Claude-suggested tasks should be embedded
            assert "- [ ] Set up project structure" in content, (
                f"Claude-suggested tasks not embedded. Content:\n{content}"
            )
            assert "- [ ] Implement user endpoints" in content, (
                f"Claude-suggested tasks not embedded. Content:\n{content}"
            )

    def test_init_handles_empty_tasks_list(self, tmp_path: Path) -> None:
        """Init should handle when no tasks are provided."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Tasks\n\n{{tasks}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            with patch("wiggum.cli.run_claude_for_planning", return_value=None):
                # Empty task input (just press enter)
                result = runner.invoke(
                    app,
                    ["init"],
                    input="Test project\nREADME.md\n\n1\n",
                )

            assert result.exit_code == 0, f"Init failed: {result.output}"

            loop_prompt = Path("LOOP-PROMPT.md")
            content = loop_prompt.read_text()

            # Should have placeholder task
            assert "- [ ]" in content, (
                f"Should have placeholder task. Content:\n{content}"
            )

    def test_tasks_placeholder_not_left_unreplaced(self, tmp_path: Path) -> None:
        """The {{tasks}} placeholder should not remain in generated files."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n## Tasks\n\n{{tasks}}\n\n## Workflow\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text("Analyze {{goal}}")

            with patch("wiggum.cli.run_claude_for_planning", return_value=None):
                result = runner.invoke(
                    app,
                    ["init"],
                    input="Test project\nREADME.md\nTask 1\n\n1\n",
                )

            loop_prompt = Path("LOOP-PROMPT.md")
            content = loop_prompt.read_text()

            # Raw placeholder should not remain
            assert "{{tasks}}" not in content, (
                f"{{{{tasks}}}} placeholder not replaced. Content:\n{content}"
            )
