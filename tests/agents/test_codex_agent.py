"""Tests for Codex-specific command building.

These tests verify the CodexAgent builds the correct CLI commands
based on configuration. Common agent behavior (protocol compliance,
result handling, error handling) is tested in test_agents.py.
"""

from unittest.mock import MagicMock, patch

from wiggum.agents import AgentConfig
from wiggum.agents_codex import CodexAgent


class TestCodexAgentCommandBuilding:
    """Tests that CodexAgent builds the correct CLI commands."""

    @patch("wiggum.agents_codex.subprocess.run")
    def test_basic_command(self, mock_run: MagicMock):
        """Basic config should build 'codex --json <prompt>'."""
        mock_run.return_value = MagicMock(stdout="output", stderr="", returncode=0)

        agent = CodexAgent()
        config = AgentConfig(prompt="test prompt")
        agent.run(config)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd == ["codex", "--json", "test prompt"]

    @patch("wiggum.agents_codex.subprocess.run")
    def test_yolo_mode_adds_flag(self, mock_run: MagicMock):
        """yolo=True should add --yolo flag."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = CodexAgent()
        config = AgentConfig(prompt="test", yolo=True)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--yolo" in cmd

    @patch("wiggum.agents_codex.subprocess.run")
    def test_yolo_false_no_flag(self, mock_run: MagicMock):
        """yolo=False should not add --yolo flag."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = CodexAgent()
        config = AgentConfig(prompt="test", yolo=False)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--yolo" not in cmd

    @patch("wiggum.agents_codex.subprocess.run")
    def test_allow_paths_adds_add_dir_flags(self, mock_run: MagicMock):
        """allow_paths should add --add-dir flags for each path."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = CodexAgent()
        config = AgentConfig(prompt="test", allow_paths="src/,tests/")
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--add-dir" in cmd
        assert "src/" in cmd
        assert "tests/" in cmd

    @patch("wiggum.agents_codex.subprocess.run")
    def test_allow_paths_none_no_add_dir(self, mock_run: MagicMock):
        """allow_paths=None should not add --add-dir flags."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = CodexAgent()
        config = AgentConfig(prompt="test", allow_paths=None)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--add-dir" not in cmd
