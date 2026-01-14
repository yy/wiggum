"""Tests for TASKS.md format with Done section first.

This tests that the parser functions work correctly when the Done section
appears before the Todo section, which is the preferred format because
it makes it easier to append new tasks to the end of the file.
"""

from pathlib import Path

from ralph_loop.cli import get_current_task, tasks_remaining


class TestDoneFirstFormat:
    """Tests for TASKS.md with Done section appearing first."""

    def test_tasks_remaining_with_done_first_format(self, tmp_path: Path) -> None:
        """tasks_remaining correctly finds unchecked tasks when Done section is first."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] Completed task 1\n"
            "- [x] Completed task 2\n\n"
            "## In Progress\n\n"
            "## Todo\n\n"
            "- [ ] Pending task 1\n"
            "- [ ] Pending task 2\n"
        )
        assert tasks_remaining(tasks_file) is True

    def test_tasks_remaining_false_with_done_first_all_complete(
        self, tmp_path: Path
    ) -> None:
        """tasks_remaining returns False when all tasks are done (Done-first format)."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] Completed task 1\n"
            "- [x] Completed task 2\n\n"
            "## In Progress\n\n"
            "## Todo\n\n"
        )
        assert tasks_remaining(tasks_file) is False

    def test_get_current_task_with_done_first_format(self, tmp_path: Path) -> None:
        """get_current_task finds the first incomplete task with Done-first format."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] Already finished\n\n"
            "## In Progress\n\n"
            "## Todo\n\n"
            "- [ ] First pending task\n"
            "- [ ] Second pending task\n"
        )
        result = get_current_task(tasks_file)
        assert result == "First pending task"

    def test_get_current_task_returns_none_done_first_all_complete(
        self, tmp_path: Path
    ) -> None:
        """get_current_task returns None when all tasks complete (Done-first format)."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] Completed task 1\n"
            "- [x] Completed task 2\n\n"
            "## In Progress\n\n"
            "## Todo\n\n"
        )
        result = get_current_task(tasks_file)
        assert result is None

    def test_get_current_task_prefers_in_progress_over_todo(
        self, tmp_path: Path
    ) -> None:
        """Tasks in In Progress section are found first (Done-first format)."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] Completed\n\n"
            "## In Progress\n\n"
            "- [ ] Working on this now\n\n"
            "## Todo\n\n"
            "- [ ] Later task\n"
        )
        # get_current_task finds the first unchecked box in file order
        # With Done-first, In Progress comes before Todo
        result = get_current_task(tasks_file)
        assert result == "Working on this now"

    def test_tasks_remaining_with_mixed_tasks_done_first(self, tmp_path: Path) -> None:
        """tasks_remaining correctly handles mix of complete/incomplete (Done-first)."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] Task A done\n"
            "- [x] Task B done\n"
            "- [x] Task C done\n\n"
            "## In Progress\n\n"
            "- [ ] Task D in progress\n\n"
            "## Todo\n\n"
            "- [ ] Task E pending\n"
        )
        assert tasks_remaining(tasks_file) is True


class TestTemplateFormat:
    """Tests for the TASKS.md template format."""

    def test_template_has_done_section_first(self) -> None:
        """The TASKS.md template should have Done section before Todo."""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / "templates" / "TASKS.md"
        if template_path.exists():
            content = template_path.read_text()
            done_pos = content.find("## Done")
            todo_pos = content.find("## Todo")
            # Done should appear before Todo in the file
            assert done_pos < todo_pos, (
                f"Done section should appear before Todo section. "
                f"Done at {done_pos}, Todo at {todo_pos}"
            )

    def test_template_has_in_progress_section(self) -> None:
        """The TASKS.md template should have an In Progress section."""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / "templates" / "TASKS.md"
        if template_path.exists():
            content = template_path.read_text()
            assert "## In Progress" in content
