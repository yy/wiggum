"""Tests for [output] section in .ralph-loop.toml configuration."""

import os
from pathlib import Path

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


class TestOutputConfigReading:
    """Tests for reading [output] config from .ralph-loop.toml."""

    def test_read_output_section_log_file(self, tmp_path: Path) -> None:
        """read_config returns log_file from [output] section."""
        config_content = """[security]
yolo = false

[output]
log_file = "loop.log"
"""
        os.chdir(tmp_path)
        (tmp_path / ".ralph-loop.toml").write_text(config_content)

        config = read_config()

        assert config.get("output", {}).get("log_file") == "loop.log"

    def test_read_output_section_verbose(self, tmp_path: Path) -> None:
        """read_config returns verbose from [output] section."""
        config_content = """[output]
verbose = true
"""
        os.chdir(tmp_path)
        (tmp_path / ".ralph-loop.toml").write_text(config_content)

        config = read_config()

        assert config.get("output", {}).get("verbose") is True

    def test_read_output_section_verbose_false(self, tmp_path: Path) -> None:
        """read_config returns verbose=false from [output] section."""
        config_content = """[output]
verbose = false
"""
        os.chdir(tmp_path)
        (tmp_path / ".ralph-loop.toml").write_text(config_content)

        config = read_config()

        assert config.get("output", {}).get("verbose") is False

    def test_read_output_section_all_fields(self, tmp_path: Path) -> None:
        """read_config returns all [output] fields when present."""
        config_content = """[security]
yolo = true
allow_paths = "src/"

[loop]
max_iterations = 50

[output]
log_file = "my-loop.log"
verbose = true
"""
        os.chdir(tmp_path)
        (tmp_path / ".ralph-loop.toml").write_text(config_content)

        config = read_config()

        assert config.get("output", {}).get("log_file") == "my-loop.log"
        assert config.get("output", {}).get("verbose") is True


class TestOutputConfigWriting:
    """Tests for writing [output] config to .ralph-loop.toml."""

    def test_write_output_section(self, tmp_path: Path) -> None:
        """write_config writes [output] section to file."""
        os.chdir(tmp_path)

        write_config(
            {
                "security": {"yolo": False, "allow_paths": ""},
                "output": {
                    "log_file": "output.log",
                    "verbose": True,
                },
            }
        )

        content = (tmp_path / ".ralph-loop.toml").read_text()
        assert "[output]" in content
        assert 'log_file = "output.log"' in content
        assert "verbose = true" in content

    def test_write_output_section_only_set_fields(self, tmp_path: Path) -> None:
        """write_config only includes fields that are set."""
        os.chdir(tmp_path)

        write_config(
            {
                "security": {"yolo": False},
                "output": {"verbose": True},
            }
        )

        content = (tmp_path / ".ralph-loop.toml").read_text()
        assert "[output]" in content
        assert "verbose = true" in content
        # Should not include fields that weren't set
        assert "log_file" not in content

    def test_write_all_sections(self, tmp_path: Path) -> None:
        """write_config writes all sections together."""
        os.chdir(tmp_path)

        write_config(
            {
                "security": {"yolo": True, "allow_paths": "src/"},
                "loop": {"max_iterations": 20},
                "output": {"log_file": "loop.log", "verbose": True},
            }
        )

        content = (tmp_path / ".ralph-loop.toml").read_text()
        assert "[security]" in content
        assert "[loop]" in content
        assert "[output]" in content
        assert "yolo = true" in content
        assert "max_iterations = 20" in content
        assert 'log_file = "loop.log"' in content
        assert "verbose = true" in content


class TestOutputConfigRunCommand:
    """Tests for applying [output] config in run command."""

    def test_log_file_from_config(self, tmp_path: Path) -> None:
        """run uses log_file from config when CLI flag not provided."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text('[output]\nlog_file = "loop.log"\n')

        result = runner.invoke(app, ["run", "--dry-run"])

        assert "loop.log" in result.output
        assert result.exit_code == 0

    def test_cli_flag_overrides_config_log_file(self, tmp_path: Path) -> None:
        """CLI --log-file flag overrides config file value."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text('[output]\nlog_file = "config.log"\n')

        result = runner.invoke(app, ["run", "--dry-run", "--log-file", "cli.log"])

        # CLI flag (cli.log) should override config (config.log)
        assert "cli.log" in result.output
        assert result.exit_code == 0

    def test_verbose_from_config(self, tmp_path: Path) -> None:
        """run uses verbose from config when CLI flag not provided."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text("[output]\nverbose = true\n")

        result = runner.invoke(app, ["run", "--dry-run"])

        # Should show progress tracking is enabled from config
        assert "Progress tracking: enabled" in result.output
        assert result.exit_code == 0

    def test_cli_flag_overrides_config_verbose(self, tmp_path: Path) -> None:
        """CLI -v/--verbose flag overrides config file value."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text("[output]\nverbose = false\n")

        result = runner.invoke(app, ["run", "--dry-run", "-v"])

        # CLI flag should override config - verbose enabled
        assert "Progress tracking: enabled" in result.output
        assert result.exit_code == 0

    def test_defaults_used_when_no_output_config(self, tmp_path: Path) -> None:
        """run uses defaults when no [output] section in config."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] done\n")
        # Config without [output] section
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text("[security]\nyolo = false\n")

        result = runner.invoke(app, ["run", "--dry-run"])

        # Should not show log file or progress tracking by default
        assert "Log file:" not in result.output
        assert "Progress tracking:" not in result.output
        assert result.exit_code == 0
