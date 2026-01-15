"""Tests for [session] section in .ralph-loop.toml configuration."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from wiggum.cli import app, read_config, write_config

runner = CliRunner()


@pytest.fixture(autouse=True)
def restore_cwd():
    """Restore working directory after each test."""
    original_cwd = os.getcwd()
    yield
    os.chdir(original_cwd)


class TestSessionConfigReading:
    """Tests for reading [session] config from .ralph-loop.toml."""

    def test_read_session_section_continue_session_true(self, tmp_path: Path) -> None:
        """read_config returns continue_session=true from [session] section."""
        config_content = """[security]
yolo = false

[session]
continue_session = true
"""
        os.chdir(tmp_path)
        (tmp_path / ".ralph-loop.toml").write_text(config_content)

        config = read_config()

        assert config.get("session", {}).get("continue_session") is True

    def test_read_session_section_continue_session_false(self, tmp_path: Path) -> None:
        """read_config returns continue_session=false from [session] section."""
        config_content = """[session]
continue_session = false
"""
        os.chdir(tmp_path)
        (tmp_path / ".ralph-loop.toml").write_text(config_content)

        config = read_config()

        assert config.get("session", {}).get("continue_session") is False

    def test_read_all_sections_including_session(self, tmp_path: Path) -> None:
        """read_config returns all sections including [session]."""
        config_content = """[security]
yolo = true
allow_paths = "src/"

[loop]
max_iterations = 50

[output]
log_file = "loop.log"
verbose = true

[session]
continue_session = true
"""
        os.chdir(tmp_path)
        (tmp_path / ".ralph-loop.toml").write_text(config_content)

        config = read_config()

        assert config.get("security", {}).get("yolo") is True
        assert config.get("loop", {}).get("max_iterations") == 50
        assert config.get("output", {}).get("verbose") is True
        assert config.get("session", {}).get("continue_session") is True


class TestSessionConfigWriting:
    """Tests for writing [session] config to .ralph-loop.toml."""

    def test_write_session_section(self, tmp_path: Path) -> None:
        """write_config writes [session] section to file."""
        os.chdir(tmp_path)

        write_config(
            {
                "security": {"yolo": False, "allow_paths": ""},
                "session": {"continue_session": True},
            }
        )

        content = (tmp_path / ".ralph-loop.toml").read_text()
        assert "[session]" in content
        assert "continue_session = true" in content

    def test_write_session_section_false(self, tmp_path: Path) -> None:
        """write_config writes continue_session=false correctly."""
        os.chdir(tmp_path)

        write_config(
            {
                "security": {"yolo": False},
                "session": {"continue_session": False},
            }
        )

        content = (tmp_path / ".ralph-loop.toml").read_text()
        assert "[session]" in content
        assert "continue_session = false" in content

    def test_write_all_sections_including_session(self, tmp_path: Path) -> None:
        """write_config writes all sections together including [session]."""
        os.chdir(tmp_path)

        write_config(
            {
                "security": {"yolo": True, "allow_paths": "src/"},
                "loop": {"max_iterations": 20},
                "output": {"log_file": "loop.log", "verbose": True},
                "session": {"continue_session": True},
            }
        )

        content = (tmp_path / ".ralph-loop.toml").read_text()
        assert "[security]" in content
        assert "[loop]" in content
        assert "[output]" in content
        assert "[session]" in content
        assert "continue_session = true" in content


class TestSessionConfigRunCommand:
    """Tests for applying [session] config in run command."""

    def test_continue_session_from_config(self, tmp_path: Path) -> None:
        """run uses continue_session from config when CLI flag not provided."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n- [ ] task2\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text("[session]\ncontinue_session = true\n")

        call_count = 0

        def mock_subprocess_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            # Complete tasks to stop the loop
            if call_count == 1:
                tasks_file.write_text(
                    "# Tasks\n\n## Todo\n\n- [ ] task2\n\n## Done\n\n- [x] task1\n"
                )
            elif call_count == 2:
                tasks_file.write_text(
                    "# Tasks\n\n## Done\n\n- [x] task1\n- [x] task2\n"
                )
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch(
            "wiggum.agents_claude.subprocess.run", side_effect=mock_subprocess_run
        ) as mock_run:
            result = runner.invoke(app, ["run"])

        assert result.exit_code == 0
        assert call_count == 2

        # Second call should have -c flag because config has continue_session=true
        second_call_args = mock_run.call_args_list[1][0][0]
        assert "-c" in second_call_args

    def test_continue_flag_overrides_config_false(self, tmp_path: Path) -> None:
        """CLI --continue flag overrides continue_session=false in config."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n- [ ] task2\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text("[session]\ncontinue_session = false\n")

        call_count = 0

        def mock_subprocess_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                tasks_file.write_text(
                    "# Tasks\n\n## Todo\n\n- [ ] task2\n\n## Done\n\n- [x] task1\n"
                )
            elif call_count == 2:
                tasks_file.write_text(
                    "# Tasks\n\n## Done\n\n- [x] task1\n- [x] task2\n"
                )
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch(
            "wiggum.agents_claude.subprocess.run", side_effect=mock_subprocess_run
        ) as mock_run:
            result = runner.invoke(app, ["run", "--continue"])

        assert result.exit_code == 0
        # CLI flag should override config - second call should have -c
        second_call_args = mock_run.call_args_list[1][0][0]
        assert "-c" in second_call_args

    def test_reset_flag_overrides_config_true(self, tmp_path: Path) -> None:
        """CLI --reset flag overrides continue_session=true in config."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n- [ ] task2\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text("[session]\ncontinue_session = true\n")

        call_count = 0

        def mock_subprocess_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                tasks_file.write_text(
                    "# Tasks\n\n## Todo\n\n- [ ] task2\n\n## Done\n\n- [x] task1\n"
                )
            elif call_count == 2:
                tasks_file.write_text(
                    "# Tasks\n\n## Done\n\n- [x] task1\n- [x] task2\n"
                )
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch(
            "wiggum.agents_claude.subprocess.run", side_effect=mock_subprocess_run
        ) as mock_run:
            result = runner.invoke(app, ["run", "--reset"])

        assert result.exit_code == 0
        # CLI --reset should override config - NO call should have -c
        for call_args in mock_run.call_args_list:
            args = call_args[0][0]
            assert "-c" not in args

    def test_defaults_used_when_no_session_config(self, tmp_path: Path) -> None:
        """run uses default (reset) when no [session] section in config."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n- [ ] task2\n")
        # Config without [session] section
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text("[security]\nyolo = false\n")

        call_count = 0

        def mock_subprocess_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                tasks_file.write_text(
                    "# Tasks\n\n## Todo\n\n- [ ] task2\n\n## Done\n\n- [x] task1\n"
                )
            elif call_count == 2:
                tasks_file.write_text(
                    "# Tasks\n\n## Done\n\n- [x] task1\n- [x] task2\n"
                )
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch(
            "wiggum.agents_claude.subprocess.run", side_effect=mock_subprocess_run
        ) as mock_run:
            result = runner.invoke(app, ["run"])

        assert result.exit_code == 0
        # Default behavior - no -c flag
        for call_args in mock_run.call_args_list:
            args = call_args[0][0]
            assert "-c" not in args

    def test_dry_run_shows_session_mode_from_config(self, tmp_path: Path) -> None:
        """Dry run shows continue mode when config has continue_session=true."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text("[session]\ncontinue_session = true\n")

        result = runner.invoke(app, ["run", "--dry-run"])

        assert result.exit_code == 0
        # Should show that session will be continued
        assert "continue" in result.output.lower()
