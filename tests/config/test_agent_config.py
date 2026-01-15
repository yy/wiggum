"""Tests for agent selection in config and CLI.

Tests verify:
1. --agent CLI flag selects the agent to use
2. agent setting in .ralph-loop.toml [loop] section
3. CLI flag overrides config file setting
4. Default to "claude" when no agent specified
5. Error message for unknown agents
6. Dry-run shows which agent will be used
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from wiggum.agents import AgentResult, get_available_agents
from wiggum.cli import app
from wiggum.config import read_config, write_config

runner = CliRunner()


@pytest.fixture(autouse=True)
def restore_cwd():
    """Restore working directory after each test."""
    original_cwd = os.getcwd()
    yield
    os.chdir(original_cwd)


class TestAgentConfigReading:
    """Tests for reading agent config from .ralph-loop.toml."""

    def test_read_agent_from_loop_section(self, tmp_path: Path) -> None:
        """read_config returns agent from [loop] section."""
        config_content = """[loop]
agent = "codex"
"""
        os.chdir(tmp_path)
        (tmp_path / ".ralph-loop.toml").write_text(config_content)

        config = read_config()

        assert config.get("loop", {}).get("agent") == "codex"

    def test_read_agent_with_other_settings(self, tmp_path: Path) -> None:
        """read_config returns agent along with other loop settings."""
        config_content = """[security]
yolo = true

[loop]
max_iterations = 25
agent = "gemini"
"""
        os.chdir(tmp_path)
        (tmp_path / ".ralph-loop.toml").write_text(config_content)

        config = read_config()

        assert config.get("loop", {}).get("agent") == "gemini"
        assert config.get("loop", {}).get("max_iterations") == 25


class TestAgentConfigWriting:
    """Tests for writing agent config to .ralph-loop.toml."""

    def test_write_agent_to_loop_section(self, tmp_path: Path) -> None:
        """write_config writes agent to [loop] section."""
        os.chdir(tmp_path)

        write_config(
            {
                "security": {"yolo": False},
                "loop": {"agent": "codex"},
            }
        )

        content = (tmp_path / ".ralph-loop.toml").read_text()
        assert "[loop]" in content
        assert 'agent = "codex"' in content


class TestAgentCliFlag:
    """Tests for --agent CLI flag."""

    def test_agent_flag_selects_agent(self, tmp_path: Path) -> None:
        """The --agent flag should select the specified agent."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        mock_agent = MagicMock()
        mock_agent.name = "codex"

        def complete_task(config):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return AgentResult(stdout="done", stderr="", return_code=0)

        mock_agent.run.side_effect = complete_task

        with patch(
            "wiggum.cli.get_agent", return_value=mock_agent
        ) as mock_get_agent:
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "-n",
                    "1",
                    "--agent",
                    "codex",
                ],
            )

        assert result.exit_code == 0
        mock_get_agent.assert_called_with("codex")

    def test_default_agent_is_claude(self, tmp_path: Path) -> None:
        """When no --agent flag provided, default to claude."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        mock_agent = MagicMock()
        mock_agent.name = "claude"

        def complete_task(config):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return AgentResult(stdout="done", stderr="", return_code=0)

        mock_agent.run.side_effect = complete_task

        with patch(
            "wiggum.cli.get_agent", return_value=mock_agent
        ) as mock_get_agent:
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "-n",
                    "1",
                ],
            )

        assert result.exit_code == 0
        # Should be called with None (which defaults to claude in get_agent)
        mock_get_agent.assert_called_with(None)


class TestAgentConfigFromFile:
    """Tests for agent selection from config file."""

    def test_agent_from_config_file(self, tmp_path: Path) -> None:
        """Agent should be read from config file when not specified on CLI."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text('[loop]\nagent = "gemini"\n')

        mock_agent = MagicMock()
        mock_agent.name = "gemini"

        def complete_task(config):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return AgentResult(stdout="done", stderr="", return_code=0)

        mock_agent.run.side_effect = complete_task

        with patch(
            "wiggum.cli.get_agent", return_value=mock_agent
        ) as mock_get_agent:
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "-n",
                    "1",
                ],
            )

        assert result.exit_code == 0
        mock_get_agent.assert_called_with("gemini")

    def test_cli_agent_overrides_config(self, tmp_path: Path) -> None:
        """CLI --agent flag should override config file setting."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text('[loop]\nagent = "gemini"\n')

        mock_agent = MagicMock()
        mock_agent.name = "codex"

        def complete_task(config):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return AgentResult(stdout="done", stderr="", return_code=0)

        mock_agent.run.side_effect = complete_task

        with patch(
            "wiggum.cli.get_agent", return_value=mock_agent
        ) as mock_get_agent:
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "-n",
                    "1",
                    "--agent",
                    "codex",
                ],
            )

        assert result.exit_code == 0
        # CLI flag (codex) should override config (gemini)
        mock_get_agent.assert_called_with("codex")


class TestAgentDryRun:
    """Tests for --dry-run with agent selection."""

    def test_dry_run_shows_default_agent(self, tmp_path: Path) -> None:
        """Dry run should show the default agent (claude)."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        result = runner.invoke(
            app,
            [
                "run",
                "-f",
                str(prompt_file),
                "--tasks",
                str(tasks_file),
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "Agent: claude" in result.output

    def test_dry_run_shows_selected_agent(self, tmp_path: Path) -> None:
        """Dry run should show the selected agent."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        result = runner.invoke(
            app,
            [
                "run",
                "-f",
                str(prompt_file),
                "--tasks",
                str(tasks_file),
                "--dry-run",
                "--agent",
                "codex",
            ],
        )

        assert result.exit_code == 0
        assert "Agent: codex" in result.output

    def test_dry_run_shows_agent_from_config(self, tmp_path: Path) -> None:
        """Dry run should show agent from config file."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        config_file = tmp_path / ".ralph-loop.toml"
        config_file.write_text('[loop]\nagent = "gemini"\n')

        result = runner.invoke(
            app,
            [
                "run",
                "-f",
                str(prompt_file),
                "--tasks",
                str(tasks_file),
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "Agent: gemini" in result.output


class TestAgentErrorHandling:
    """Tests for error handling with invalid agent names."""

    def test_unknown_agent_shows_error(self, tmp_path: Path) -> None:
        """Unknown agent name should show error with available agents."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        result = runner.invoke(
            app,
            [
                "run",
                "-f",
                str(prompt_file),
                "--tasks",
                str(tasks_file),
                "-n",
                "1",
                "--agent",
                "unknown_agent",
            ],
        )

        assert result.exit_code == 1
        assert "Unknown agent" in result.output or "unknown_agent" in result.output


class TestAvailableAgents:
    """Tests for listing available agents."""

    def test_get_available_agents_returns_registered(self) -> None:
        """get_available_agents should return list of registered agent names."""
        agents = get_available_agents()

        assert isinstance(agents, list)
        # These agents should be registered from their respective modules
        assert "claude" in agents
        assert "codex" in agents
        assert "gemini" in agents
