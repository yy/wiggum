"""Tests for the wiggum suggest command."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from wiggum.cli import app

runner = CliRunner()


class TestSuggestCommand:
    """Tests for the `wiggum suggest` command."""

    def test_suggest_displays_found_tasks(self, tmp_path: Path) -> None:
        """Displays task suggestions from Claude."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n")

        mock_output = """```markdown
## Tasks

- [ ] First suggested task
- [ ] Second suggested task

## Constraints

security_mode: conservative
```"""

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "wiggum.runner.run_claude_for_planning",
                return_value=(mock_output, None),
            ):
                result = runner.invoke(
                    app,
                    ["suggest", "--tasks-file", str(tasks_file), "--yes"],
                )

        assert result.exit_code == 0
        assert "First suggested task" in result.output
        assert "Second suggested task" in result.output

    def test_suggest_adds_tasks_with_yes_flag(self, tmp_path: Path) -> None:
        """Adds all tasks without prompting when --yes is used."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n")

        mock_output = """```markdown
## Tasks

- [ ] Task one
- [ ] Task two

## Constraints

security_mode: yolo
```"""

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "wiggum.runner.run_claude_for_planning",
                return_value=(mock_output, None),
            ):
                result = runner.invoke(
                    app,
                    ["suggest", "--tasks-file", str(tasks_file), "--yes"],
                )

        assert result.exit_code == 0
        content = tasks_file.read_text()
        assert "- [ ] Task one" in content
        assert "- [ ] Task two" in content

    def test_suggest_skips_existing_tasks(self, tmp_path: Path) -> None:
        """Does not add tasks that already exist in TASKS.md."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] Existing task\n")

        mock_output = """```markdown
## Tasks

- [ ] Existing task
- [ ] New task

## Constraints

security_mode: conservative
```"""

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "wiggum.runner.run_claude_for_planning",
                return_value=(mock_output, None),
            ):
                result = runner.invoke(
                    app,
                    ["suggest", "--tasks-file", str(tasks_file), "--yes"],
                )

        assert result.exit_code == 0
        content = tasks_file.read_text()
        # Should have new task
        assert "- [ ] New task" in content
        # Should only have one instance of existing task
        assert content.count("Existing task") == 1

    def test_suggest_shows_count_of_new_tasks(self, tmp_path: Path) -> None:
        """Shows the number of new tasks found."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n")

        mock_output = """```markdown
## Tasks

- [ ] Task A
- [ ] Task B
- [ ] Task C

## Constraints

security_mode: conservative
```"""

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "wiggum.runner.run_claude_for_planning",
                return_value=(mock_output, None),
            ):
                result = runner.invoke(
                    app,
                    ["suggest", "--tasks-file", str(tasks_file), "--yes"],
                )

        assert result.exit_code == 0
        assert "3 new task suggestion" in result.output

    def test_suggest_shows_added_count(self, tmp_path: Path) -> None:
        """Shows the count of tasks actually added."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n")

        mock_output = """```markdown
## Tasks

- [ ] Single task

## Constraints

security_mode: conservative
```"""

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "wiggum.runner.run_claude_for_planning",
                return_value=(mock_output, None),
            ):
                result = runner.invoke(
                    app,
                    ["suggest", "--tasks-file", str(tasks_file), "--yes"],
                )

        assert result.exit_code == 0
        assert "Added 1 task(s)" in result.output

    def test_suggest_all_tasks_exist_message(self, tmp_path: Path) -> None:
        """Shows message when all suggested tasks already exist."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n## Todo\n\n- [ ] Existing task\n- [ ] Another existing\n"
        )

        mock_output = """```markdown
## Tasks

- [ ] Existing task
- [ ] Another existing

## Constraints

security_mode: conservative
```"""

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "wiggum.runner.run_claude_for_planning",
                return_value=(mock_output, None),
            ):
                result = runner.invoke(
                    app,
                    ["suggest", "--tasks-file", str(tasks_file), "--yes"],
                )

        assert result.exit_code == 0
        assert "All suggested tasks already exist" in result.output

    def test_suggest_no_tasks_message(self, tmp_path: Path) -> None:
        """Shows message when no tasks are suggested."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n")

        mock_output = """```markdown
## Tasks

## Constraints

security_mode: conservative
```"""

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "wiggum.runner.run_claude_for_planning",
                return_value=(mock_output, None),
            ):
                result = runner.invoke(
                    app,
                    ["suggest", "--tasks-file", str(tasks_file), "--yes"],
                )

        assert result.exit_code == 0
        assert "No tasks suggested" in result.output

    def test_suggest_handles_claude_failure(self, tmp_path: Path) -> None:
        """Handles case when Claude CLI is not available."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "wiggum.runner.run_claude_for_planning",
                return_value=(None, "Error: 'claude' command not found."),
            ):
                result = runner.invoke(
                    app,
                    ["suggest", "--tasks-file", str(tasks_file), "--yes"],
                )

        assert result.exit_code == 1
        assert "claude" in result.output.lower()
        assert "not found" in result.output.lower()

    def test_suggest_uses_default_tasks_file(self, tmp_path: Path) -> None:
        """Uses TASKS.md in current directory by default."""
        mock_output = """```markdown
## Tasks

- [ ] A task

## Constraints

security_mode: conservative
```"""

        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("TASKS.md").write_text("# Tasks\n\n## Todo\n\n")
            with patch(
                "wiggum.runner.run_claude_for_planning",
                return_value=(mock_output, None),
            ):
                result = runner.invoke(app, ["suggest", "--yes"])
            content = Path("TASKS.md").read_text()

        assert result.exit_code == 0
        assert "- [ ] A task" in content

    def test_suggest_short_flag(self, tmp_path: Path) -> None:
        """Supports -f as shorthand for --tasks-file."""
        tasks_file = tmp_path / "custom.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n")

        mock_output = """```markdown
## Tasks

- [ ] Custom task

## Constraints

security_mode: conservative
```"""

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "wiggum.runner.run_claude_for_planning",
                return_value=(mock_output, None),
            ):
                result = runner.invoke(
                    app,
                    ["suggest", "-f", str(tasks_file), "-y"],
                )

        assert result.exit_code == 0
        content = tasks_file.read_text()
        assert "- [ ] Custom task" in content

    def test_suggest_creates_tasks_file_if_missing(self, tmp_path: Path) -> None:
        """Creates TASKS.md if it doesn't exist."""
        tasks_file = tmp_path / "TASKS.md"

        mock_output = """```markdown
## Tasks

- [ ] New task

## Constraints

security_mode: conservative
```"""

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "wiggum.runner.run_claude_for_planning",
                return_value=(mock_output, None),
            ):
                result = runner.invoke(
                    app,
                    ["suggest", "--tasks-file", str(tasks_file), "--yes"],
                )

        assert result.exit_code == 0
        assert tasks_file.exists()
        content = tasks_file.read_text()
        assert "- [ ] New task" in content

    def test_suggest_case_insensitive_duplicate_check(self, tmp_path: Path) -> None:
        """Duplicate check is case-insensitive."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] Fix the BUG\n")

        mock_output = """```markdown
## Tasks

- [ ] fix the bug
- [ ] New task

## Constraints

security_mode: conservative
```"""

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "wiggum.runner.run_claude_for_planning",
                return_value=(mock_output, None),
            ):
                result = runner.invoke(
                    app,
                    ["suggest", "--tasks-file", str(tasks_file), "--yes"],
                )

        assert result.exit_code == 0
        content = tasks_file.read_text()
        # Should only have one bug fix task (case-insensitive match)
        assert content.lower().count("fix the bug") == 1
        # Should have new task
        assert "- [ ] New task" in content

    def test_suggest_interactive_mode_prompts(self, tmp_path: Path) -> None:
        """Interactive mode prompts for each task."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n")

        mock_output = """```markdown
## Tasks

- [ ] First task
- [ ] Second task

## Constraints

security_mode: conservative
```"""

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "wiggum.runner.run_claude_for_planning",
                return_value=(mock_output, None),
            ):
                # Accept first, reject second
                result = runner.invoke(
                    app,
                    ["suggest", "--tasks-file", str(tasks_file)],
                    input="y\nn\n",
                )

        assert result.exit_code == 0
        content = tasks_file.read_text()
        assert "- [ ] First task" in content
        assert "Second task" not in content
        assert "Added 1 task(s)" in result.output

    def test_suggest_interactive_skip_all(self, tmp_path: Path) -> None:
        """Interactive mode can skip all tasks."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n")

        mock_output = """```markdown
## Tasks

- [ ] Task one
- [ ] Task two

## Constraints

security_mode: conservative
```"""

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "wiggum.runner.run_claude_for_planning",
                return_value=(mock_output, None),
            ):
                result = runner.invoke(
                    app,
                    ["suggest", "--tasks-file", str(tasks_file)],
                    input="n\nn\n",
                )

        assert result.exit_code == 0
        content = tasks_file.read_text()
        assert "Task one" not in content
        assert "Task two" not in content
        assert "Added 0 task(s)" in result.output

    def test_suggest_uses_readme_for_context(self, tmp_path: Path) -> None:
        """Uses README.md content for context if available."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n")
        readme_file = tmp_path / "README.md"
        readme_file.write_text("# My Project\n\nThis is a test project.")

        mock_output = """```markdown
## Tasks

- [ ] Task

## Constraints

security_mode: conservative
```"""

        captured_prompt = []

        def capture_prompt(prompt: str):
            captured_prompt.append(prompt)
            return (mock_output, None)

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Copy README to isolated filesystem
            Path("README.md").write_text(readme_file.read_text())
            with patch(
                "wiggum.runner.run_claude_for_planning", side_effect=capture_prompt
            ):
                runner.invoke(
                    app,
                    ["suggest", "--tasks-file", str(tasks_file), "--yes"],
                )

        # Verify README content was included in the prompt
        assert len(captured_prompt) == 1
        assert "My Project" in captured_prompt[0]
        assert "test project" in captured_prompt[0]
