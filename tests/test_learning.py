"""Tests for the learning diary feature."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from wiggum.learning import (
    clear_diary,
    consolidate_learnings,
    ensure_diary_dir,
    has_diary_content,
    read_diary,
)


@pytest.fixture(autouse=True)
def restore_cwd():
    """Restore working directory after each test."""
    original_cwd = os.getcwd()
    yield
    os.chdir(original_cwd)


class TestEnsureDiaryDir:
    """Tests for ensure_diary_dir function."""

    def test_creates_diary_directory(self, tmp_path: Path) -> None:
        """Creates .wiggum/ directory if it doesn't exist."""
        os.chdir(tmp_path)

        ensure_diary_dir()

        assert (tmp_path / ".wiggum").exists()
        assert (tmp_path / ".wiggum").is_dir()

    def test_does_not_fail_if_directory_exists(self, tmp_path: Path) -> None:
        """Does not raise error if directory already exists."""
        os.chdir(tmp_path)
        (tmp_path / ".wiggum").mkdir()

        ensure_diary_dir()  # Should not raise

        assert (tmp_path / ".wiggum").exists()


class TestHasDiaryContent:
    """Tests for has_diary_content function."""

    def test_returns_false_when_no_diary_file(self, tmp_path: Path) -> None:
        """Returns False when diary file doesn't exist."""
        os.chdir(tmp_path)

        assert has_diary_content() is False

    def test_returns_false_when_diary_is_empty(self, tmp_path: Path) -> None:
        """Returns False when diary file is empty."""
        os.chdir(tmp_path)
        (tmp_path / ".wiggum").mkdir()
        (tmp_path / ".wiggum" / "session-diary.md").write_text("")

        assert has_diary_content() is False

    def test_returns_false_when_diary_is_whitespace_only(self, tmp_path: Path) -> None:
        """Returns False when diary file contains only whitespace."""
        os.chdir(tmp_path)
        (tmp_path / ".wiggum").mkdir()
        (tmp_path / ".wiggum" / "session-diary.md").write_text("   \n\n  ")

        assert has_diary_content() is False

    def test_returns_true_when_diary_has_content(self, tmp_path: Path) -> None:
        """Returns True when diary file has actual content."""
        os.chdir(tmp_path)
        (tmp_path / ".wiggum").mkdir()
        (tmp_path / ".wiggum" / "session-diary.md").write_text(
            "### Learning: Test\n**Context**: Test context"
        )

        assert has_diary_content() is True

    def test_returns_false_on_read_error(self, tmp_path: Path) -> None:
        """Returns False when diary file cannot be read."""
        os.chdir(tmp_path)
        (tmp_path / ".wiggum").mkdir()
        diary_file = tmp_path / ".wiggum" / "session-diary.md"
        diary_file.write_text("content")

        with patch("wiggum.learning.DIARY_PATH") as mock_path:
            mock_path.exists.return_value = True
            mock_path.read_text.side_effect = OSError("Permission denied")
            assert has_diary_content() is False


class TestReadDiary:
    """Tests for read_diary function."""

    def test_returns_empty_string_when_no_diary(self, tmp_path: Path) -> None:
        """Returns empty string when diary file doesn't exist."""
        os.chdir(tmp_path)

        assert read_diary() == ""

    def test_returns_diary_content(self, tmp_path: Path) -> None:
        """Returns the content of the diary file."""
        os.chdir(tmp_path)
        (tmp_path / ".wiggum").mkdir()
        content = "### Learning: Test\n**Context**: Test context"
        (tmp_path / ".wiggum" / "session-diary.md").write_text(content)

        assert read_diary() == content

    def test_returns_empty_string_on_read_error(self, tmp_path: Path) -> None:
        """Returns empty string when diary file cannot be read."""
        os.chdir(tmp_path)
        (tmp_path / ".wiggum").mkdir()
        diary_file = tmp_path / ".wiggum" / "session-diary.md"
        diary_file.write_text("content")

        with patch("wiggum.learning.DIARY_PATH") as mock_path:
            mock_path.exists.return_value = True
            mock_path.read_text.side_effect = OSError("Permission denied")
            assert read_diary() == ""


class TestClearDiary:
    """Tests for clear_diary function."""

    def test_deletes_diary_file(self, tmp_path: Path) -> None:
        """Deletes the diary file when it exists."""
        os.chdir(tmp_path)
        (tmp_path / ".wiggum").mkdir()
        diary_file = tmp_path / ".wiggum" / "session-diary.md"
        diary_file.write_text("some content")

        clear_diary()

        assert not diary_file.exists()

    def test_does_not_fail_when_no_diary(self, tmp_path: Path) -> None:
        """Does not raise error when diary file doesn't exist."""
        os.chdir(tmp_path)

        clear_diary()  # Should not raise


class TestConsolidateLearnings:
    """Tests for consolidate_learnings function."""

    def test_returns_false_when_no_diary_content(self, tmp_path: Path) -> None:
        """Returns False when diary has no content."""
        os.chdir(tmp_path)

        result = consolidate_learnings(agent_name=None, yolo=True)

        assert result is False

    def test_calls_agent_with_correct_prompt(self, tmp_path: Path) -> None:
        """Calls agent with diary content and CLAUDE.md content."""
        os.chdir(tmp_path)
        # Set up diary
        (tmp_path / ".wiggum").mkdir()
        diary_content = "### Learning: Test\n**Context**: Test"
        (tmp_path / ".wiggum" / "session-diary.md").write_text(diary_content)
        # Set up CLAUDE.md
        claude_md_content = "# Project\n\nExisting content"
        (tmp_path / "CLAUDE.md").write_text(claude_md_content)

        mock_agent = MagicMock()
        mock_agent.run.return_value = MagicMock(return_code=0)

        with patch("wiggum.learning.get_agent", return_value=mock_agent):
            with patch(
                "wiggum.learning.resolve_templates_dir",
                return_value=Path(__file__).parent.parent
                / "src"
                / "wiggum"
                / "templates",
            ):
                result = consolidate_learnings(agent_name="claude", yolo=True)

        assert result is True
        mock_agent.run.assert_called_once()
        config = mock_agent.run.call_args[0][0]
        assert diary_content in config.prompt
        assert claude_md_content in config.prompt
        assert config.yolo is True

    def test_returns_false_on_agent_failure(self, tmp_path: Path) -> None:
        """Returns False when agent returns non-zero exit code."""
        os.chdir(tmp_path)
        (tmp_path / ".wiggum").mkdir()
        (tmp_path / ".wiggum" / "session-diary.md").write_text("some content")

        mock_agent = MagicMock()
        mock_agent.run.return_value = MagicMock(return_code=1)

        with patch("wiggum.learning.get_agent", return_value=mock_agent):
            with patch(
                "wiggum.learning.resolve_templates_dir",
                return_value=Path(__file__).parent.parent
                / "src"
                / "wiggum"
                / "templates",
            ):
                result = consolidate_learnings(agent_name="claude", yolo=True)

        assert result is False

    def test_returns_false_when_template_missing(self, tmp_path: Path) -> None:
        """Returns False when CONSOLIDATE-PROMPT.md template is missing."""
        os.chdir(tmp_path)
        (tmp_path / ".wiggum").mkdir()
        (tmp_path / ".wiggum" / "session-diary.md").write_text("some content")

        # Use a directory without the template
        empty_templates = tmp_path / "templates"
        empty_templates.mkdir()

        with patch(
            "wiggum.learning.resolve_templates_dir", return_value=empty_templates
        ):
            result = consolidate_learnings(agent_name="claude", yolo=True)

        assert result is False

    def test_handles_missing_claude_md(self, tmp_path: Path) -> None:
        """Works when CLAUDE.md doesn't exist."""
        os.chdir(tmp_path)
        (tmp_path / ".wiggum").mkdir()
        (tmp_path / ".wiggum" / "session-diary.md").write_text("diary content")

        mock_agent = MagicMock()
        mock_agent.run.return_value = MagicMock(return_code=0)

        with patch("wiggum.learning.get_agent", return_value=mock_agent):
            with patch(
                "wiggum.learning.resolve_templates_dir",
                return_value=Path(__file__).parent.parent
                / "src"
                / "wiggum"
                / "templates",
            ):
                result = consolidate_learnings(agent_name="claude", yolo=True)

        assert result is True
        config = mock_agent.run.call_args[0][0]
        assert "(No CLAUDE.md exists)" in config.prompt


class TestLearningConfigResolution:
    """Tests for learning config resolution in resolve_run_config."""

    def _base_config_args(self) -> dict:
        """Return base arguments for resolve_run_config."""
        return {
            "yolo": False,
            "allow_paths": None,
            "max_iterations": None,
            "tasks_file": None,
            "prompt_file": None,
            "agent": None,
            "log_file": None,
            "show_progress": False,
            "continue_session": False,
            "reset_session": False,
            "keep_running": False,
            "stop_when_done": False,
            "create_pr": False,
            "no_branch": False,
            "force": False,
            "branch_prefix": None,
            "diary": False,
            "no_diary": False,
            "no_consolidate": False,
            "keep_diary_flag": False,
            "no_keep_diary": False,
        }

    def test_diary_and_no_diary_mutually_exclusive(self, tmp_path: Path) -> None:
        """Cannot use --diary and --no-diary together."""
        from wiggum.config import resolve_run_config

        os.chdir(tmp_path)
        args = self._base_config_args()
        args["diary"] = True
        args["no_diary"] = True

        with pytest.raises(ValueError, match="mutually exclusive"):
            resolve_run_config(**args)

    def test_keep_diary_and_no_keep_diary_mutually_exclusive(
        self, tmp_path: Path
    ) -> None:
        """Cannot use --keep-diary and --no-keep-diary together."""
        from wiggum.config import resolve_run_config

        os.chdir(tmp_path)
        args = self._base_config_args()
        args["keep_diary_flag"] = True
        args["no_keep_diary"] = True

        with pytest.raises(ValueError, match="mutually exclusive"):
            resolve_run_config(**args)

    def test_diary_flag_enables_learning(self, tmp_path: Path) -> None:
        """--diary flag enables learning even when config disables it."""
        from wiggum.config import resolve_run_config, write_config

        os.chdir(tmp_path)
        write_config({"learning": {"enabled": False}})
        args = self._base_config_args()
        args["diary"] = True

        cfg = resolve_run_config(**args)

        assert cfg.learning_enabled is True

    def test_no_diary_flag_disables_learning(self, tmp_path: Path) -> None:
        """--no-diary flag disables learning."""
        from wiggum.config import resolve_run_config

        os.chdir(tmp_path)
        args = self._base_config_args()
        args["no_diary"] = True

        cfg = resolve_run_config(**args)

        assert cfg.learning_enabled is False

    def test_keep_diary_flag_overrides_config(self, tmp_path: Path) -> None:
        """--keep-diary flag overrides config setting."""
        from wiggum.config import resolve_run_config, write_config

        os.chdir(tmp_path)
        write_config({"learning": {"keep_diary": False}})
        args = self._base_config_args()
        args["keep_diary_flag"] = True

        cfg = resolve_run_config(**args)

        assert cfg.keep_diary is True

    def test_no_keep_diary_flag_overrides_config(self, tmp_path: Path) -> None:
        """--no-keep-diary flag overrides config setting."""
        from wiggum.config import resolve_run_config

        os.chdir(tmp_path)
        args = self._base_config_args()
        args["no_keep_diary"] = True

        cfg = resolve_run_config(**args)

        assert cfg.keep_diary is False

    def test_learning_defaults_enabled(self, tmp_path: Path) -> None:
        """Learning is enabled by default."""
        from wiggum.config import resolve_run_config

        os.chdir(tmp_path)
        args = self._base_config_args()

        cfg = resolve_run_config(**args)

        assert cfg.learning_enabled is True
        assert cfg.keep_diary is True
        assert cfg.auto_consolidate is True
