"""Tests for [loop] section in .ralph-loop.toml configuration."""

import os
from pathlib import Path
from unittest.mock import patch

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


class TestLoopConfigReading:
    """Tests for reading [loop] config from .ralph-loop.toml."""

    def test_read_loop_section_max_iterations(self, tmp_path: Path) -> None:
        """read_config returns max_iterations from [loop] section."""
        config_content = """[security]
yolo = false

[loop]
max_iterations = 25
"""
        os.chdir(tmp_path)
        (tmp_path / ".ralph-loop.toml").write_text(config_content)

        config = read_config()

        assert config.get("loop", {}).get("max_iterations") == 25

    def test_read_loop_section_tasks_file(self, tmp_path: Path) -> None:
        """read_config returns tasks_file from [loop] section."""
        config_content = """[loop]
tasks_file = "CUSTOM_TASKS.md"
"""
        os.chdir(tmp_path)
        (tmp_path / ".ralph-loop.toml").write_text(config_content)

        config = read_config()

        assert config.get("loop", {}).get("tasks_file") == "CUSTOM_TASKS.md"

    def test_read_loop_section_prompt_file(self, tmp_path: Path) -> None:
        """read_config returns prompt_file from [loop] section."""
        config_content = """[loop]
prompt_file = "MY-PROMPT.md"
"""
        os.chdir(tmp_path)
        (tmp_path / ".ralph-loop.toml").write_text(config_content)

        config = read_config()

        assert config.get("loop", {}).get("prompt_file") == "MY-PROMPT.md"

    def test_read_loop_section_all_fields(self, tmp_path: Path) -> None:
        """read_config returns all [loop] fields when present."""
        config_content = """[security]
yolo = true
allow_paths = "src/"

[loop]
max_iterations = 50
tasks_file = "TODO.md"
prompt_file = "AGENT-PROMPT.md"
"""
        os.chdir(tmp_path)
        (tmp_path / ".ralph-loop.toml").write_text(config_content)

        config = read_config()

        assert config.get("loop", {}).get("max_iterations") == 50
        assert config.get("loop", {}).get("tasks_file") == "TODO.md"
        assert config.get("loop", {}).get("prompt_file") == "AGENT-PROMPT.md"


class TestLoopConfigWriting:
    """Tests for writing [loop] config to .ralph-loop.toml."""

    def test_write_loop_section(self, tmp_path: Path) -> None:
        """write_config writes [loop] section to file."""
        os.chdir(tmp_path)

        write_config(
            {
                "security": {"yolo": False, "allow_paths": ""},
                "loop": {
                    "max_iterations": 15,
                    "tasks_file": "TASKS.md",
                    "prompt_file": "LOOP-PROMPT.md",
                },
            }
        )

        content = (tmp_path / ".ralph-loop.toml").read_text()
        assert "[loop]" in content
        assert "max_iterations = 15" in content
        assert 'tasks_file = "TASKS.md"' in content
        assert 'prompt_file = "LOOP-PROMPT.md"' in content

    def test_write_loop_section_only_set_fields(self, tmp_path: Path) -> None:
        """write_config only includes fields that are set."""
        os.chdir(tmp_path)

        write_config(
            {
                "security": {"yolo": False},
                "loop": {"max_iterations": 20},
            }
        )

        content = (tmp_path / ".ralph-loop.toml").read_text()
        assert "[loop]" in content
        assert "max_iterations = 20" in content
        # Should not include fields that weren't set
        assert "tasks_file" not in content
        assert "prompt_file" not in content


class TestLoopConfigRunCommand:
    """Tests for applying [loop] config in run command."""

    def test_max_iterations_from_config(self, tmp_path: Path) -> None:
        """run uses max_iterations from config when CLI flag not provided."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text("[loop]\nmax_iterations = 3\n")

        with patch("wiggum.agents_claude.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "output"
            mock_run.return_value.stderr = ""
            mock_run.return_value.returncode = 0

            result = runner.invoke(app, ["run", "--dry-run"])

        assert "3 iterations" in result.output
        assert result.exit_code == 0

    def test_cli_flag_overrides_config_max_iterations(self, tmp_path: Path) -> None:
        """CLI --max-iterations flag overrides config file value."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text("[loop]\nmax_iterations = 100\n")

        result = runner.invoke(app, ["run", "--dry-run", "-n", "5"])

        # CLI flag (5) should override config (100)
        assert "5 iterations" in result.output
        assert result.exit_code == 0

    def test_tasks_file_from_config(self, tmp_path: Path) -> None:
        """run uses tasks_file from config when CLI flag not provided."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        # Only create the custom tasks file from config
        custom_tasks = tmp_path / "CUSTOM_TASKS.md"
        custom_tasks.write_text("# Tasks\n\n## Done\n\n- [x] done\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text('[loop]\ntasks_file = "CUSTOM_TASKS.md"\n')

        result = runner.invoke(app, ["run", "--dry-run"])

        # Should reference CUSTOM_TASKS.md from config
        assert "CUSTOM_TASKS.md" in result.output
        assert result.exit_code == 0

    def test_cli_flag_overrides_config_tasks_file(self, tmp_path: Path) -> None:
        """CLI --tasks flag overrides config file value."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        cli_tasks = tmp_path / "CLI_TASKS.md"
        cli_tasks.write_text("# Tasks\n\n## Done\n\n- [x] done\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text('[loop]\ntasks_file = "CONFIG_TASKS.md"\n')

        result = runner.invoke(app, ["run", "--dry-run", "--tasks", str(cli_tasks)])

        # CLI flag should override config
        assert "CLI_TASKS.md" in result.output
        assert result.exit_code == 0

    def test_prompt_file_from_config(self, tmp_path: Path) -> None:
        """run uses prompt_file from config when CLI flag not provided."""
        os.chdir(tmp_path)
        # Create the prompt file that config references
        custom_prompt = tmp_path / "MY-PROMPT.md"
        custom_prompt.write_text("custom prompt content")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] done\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text('[loop]\nprompt_file = "MY-PROMPT.md"\n')

        result = runner.invoke(app, ["run", "--dry-run"])

        # Should use prompt from MY-PROMPT.md
        assert "custom prompt content" in result.output
        assert result.exit_code == 0

    def test_cli_flag_overrides_config_prompt_file(self, tmp_path: Path) -> None:
        """CLI -f flag overrides config file prompt_file value."""
        os.chdir(tmp_path)
        cli_prompt = tmp_path / "cli-prompt.md"
        cli_prompt.write_text("cli prompt content")
        config_prompt = tmp_path / "config-prompt.md"
        config_prompt.write_text("config prompt content")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] done\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text('[loop]\nprompt_file = "config-prompt.md"\n')

        result = runner.invoke(app, ["run", "--dry-run", "-f", str(cli_prompt)])

        # CLI flag should override config - should see CLI prompt content
        assert "cli prompt content" in result.output
        assert result.exit_code == 0

    def test_defaults_used_when_no_config(self, tmp_path: Path) -> None:
        """run uses defaults when no config file exists."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] done\n")
        # No config file

        result = runner.invoke(app, ["run", "--dry-run"])

        # Should use default of 10 iterations
        assert "10 iterations" in result.output
        # Should use default TASKS.md
        assert "TASKS.md" in result.output
        assert result.exit_code == 0
