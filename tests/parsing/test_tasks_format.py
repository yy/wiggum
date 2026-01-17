"""Tests for TASKS.md parser behavior."""

from pathlib import Path

from wiggum.cli import get_current_task, tasks_remaining


class TestTasksParser:
    """Tests for task parsing functions."""

    def test_tasks_remaining_with_pending_tasks(self, tmp_path: Path) -> None:
        """tasks_remaining returns True when unchecked tasks exist."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] Completed task 1\n\n"
            "## Todo\n\n"
            "- [ ] Pending task 1\n"
        )
        assert tasks_remaining(tasks_file) is True

    def test_tasks_remaining_false_when_all_complete(self, tmp_path: Path) -> None:
        """tasks_remaining returns False when all tasks are done."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] Completed task 1\n"
            "- [x] Completed task 2\n\n"
            "## Todo\n\n"
        )
        assert tasks_remaining(tasks_file) is False

    def test_get_current_task_finds_first_incomplete(self, tmp_path: Path) -> None:
        """get_current_task returns the first incomplete task."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] Already finished\n\n"
            "## Todo\n\n"
            "- [ ] First pending task\n"
            "- [ ] Second pending task\n"
        )
        result = get_current_task(tasks_file)
        assert result == "First pending task"

    def test_get_current_task_returns_none_when_all_complete(
        self, tmp_path: Path
    ) -> None:
        """get_current_task returns None when all tasks complete."""
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            "## Done\n\n"
            "- [x] Completed task 1\n"
            "- [x] Completed task 2\n\n"
            "## Todo\n\n"
        )
        result = get_current_task(tasks_file)
        assert result is None
