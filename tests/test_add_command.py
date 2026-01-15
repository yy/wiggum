"""Tests for the ralph-loop add command."""

from pathlib import Path

from typer.testing import CliRunner

from wiggum.cli import app

runner = CliRunner()


class TestAddCommand:
    """Tests for the `ralph-loop add` command."""

    def test_add_task_to_existing_file(self, tmp_path: Path) -> None:
        """Adds a task to an existing TASKS.md file."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n- [ ] Existing task\n"
        )

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                ["add", "New task description", "--tasks-file", str(tasks_file)],
            )

        assert result.exit_code == 0
        content = tasks_file.read_text()
        assert "- [ ] New task description" in content
        assert "- [ ] Existing task" in content

    def test_add_task_creates_file_if_missing(self, tmp_path: Path) -> None:
        """Creates TASKS.md with proper structure if it doesn't exist."""
        tasks_file = tmp_path / "TASKS.md"

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                ["add", "First task", "--tasks-file", str(tasks_file)],
            )

        assert result.exit_code == 0
        assert tasks_file.exists()
        content = tasks_file.read_text()
        assert "# Tasks" in content
        assert "## Todo" in content
        assert "- [ ] First task" in content

    def test_add_task_to_default_file(self, tmp_path: Path) -> None:
        """Uses TASKS.md in current directory by default."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Copy file into isolated filesystem
            Path("TASKS.md").write_text(tasks_file.read_text())
            result = runner.invoke(app, ["add", "New task"])
            content = Path("TASKS.md").read_text()

        assert result.exit_code == 0
        assert "- [ ] New task" in content

    def test_add_task_appends_to_todo_section(self, tmp_path: Path) -> None:
        """Task is added to the Todo section, not elsewhere."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] Completed task\n\n"
            "## In Progress\n\n"
            "- [ ] In progress task\n\n"
            "## Todo\n\n"
            "- [ ] Existing todo\n"
        )

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                ["add", "Brand new task", "--tasks-file", str(tasks_file)],
            )

        assert result.exit_code == 0
        content = tasks_file.read_text()
        # New task should be after existing todo
        assert "- [ ] Existing todo\n- [ ] Brand new task" in content

    def test_add_task_short_flag(self, tmp_path: Path) -> None:
        """Supports -f as shorthand for --tasks-file."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                ["add", "New task", "-f", str(tasks_file)],
            )

        assert result.exit_code == 0
        content = tasks_file.read_text()
        assert "- [ ] New task" in content

    def test_add_empty_description_fails(self, tmp_path: Path) -> None:
        """Rejects empty task descriptions."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                ["add", "", "--tasks-file", str(tasks_file)],
            )

        assert result.exit_code != 0
        assert "empty" in result.output.lower() or "Error" in result.output

    def test_add_whitespace_only_description_fails(self, tmp_path: Path) -> None:
        """Rejects whitespace-only task descriptions."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                ["add", "   ", "--tasks-file", str(tasks_file)],
            )

        assert result.exit_code != 0

    def test_add_shows_confirmation_message(self, tmp_path: Path) -> None:
        """Shows confirmation message after adding task."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                ["add", "New task", "--tasks-file", str(tasks_file)],
            )

        assert result.exit_code == 0
        assert "Added" in result.output or "added" in result.output

    def test_add_multiple_tasks_sequentially(self, tmp_path: Path) -> None:
        """Can add multiple tasks one after another."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n## In Progress\n\n## Todo\n\n")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(
                app,
                ["add", "First task", "--tasks-file", str(tasks_file)],
            )
            runner.invoke(
                app,
                ["add", "Second task", "--tasks-file", str(tasks_file)],
            )
            runner.invoke(
                app,
                ["add", "Third task", "--tasks-file", str(tasks_file)],
            )

        content = tasks_file.read_text()
        assert "- [ ] First task" in content
        assert "- [ ] Second task" in content
        assert "- [ ] Third task" in content
        # Check order is preserved
        first_pos = content.find("First task")
        second_pos = content.find("Second task")
        third_pos = content.find("Third task")
        assert first_pos < second_pos < third_pos

    def test_add_handles_file_without_todo_section(self, tmp_path: Path) -> None:
        """Handles files that exist but don't have a Todo section."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\nSome random content\n")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                ["add", "New task", "--tasks-file", str(tasks_file)],
            )

        assert result.exit_code == 0
        content = tasks_file.read_text()
        assert "## Todo" in content
        assert "- [ ] New task" in content

    def test_add_preserves_existing_content(self, tmp_path: Path) -> None:
        """Adding a task doesn't modify other content."""
        original_content = (
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] Completed task\n\n"
            "## In Progress\n\n"
            "- [ ] In progress task\n\n"
            "## Todo\n\n"
            "- [ ] Existing todo\n"
        )
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(original_content)

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                app,
                ["add", "New task", "--tasks-file", str(tasks_file)],
            )

        assert result.exit_code == 0
        content = tasks_file.read_text()
        # Verify original content is preserved
        assert "- [x] Completed task" in content
        assert "- [ ] In progress task" in content
        assert "- [ ] Existing todo" in content
