"""Tests for Claude-specific command building.

These tests verify the ClaudeAgent builds the correct CLI commands
based on configuration. Common agent behavior (protocol compliance,
result handling, error handling) is tested in test_agents.py.
"""

from unittest.mock import MagicMock, patch

from wiggum.agents import AgentConfig
from wiggum.agents_claude import ClaudeAgent


class TestClaudeAgentCommandBuilding:
    """Tests that ClaudeAgent builds the correct CLI commands."""

    @patch("wiggum.agents_claude.subprocess.run")
    def test_basic_command(self, mock_run: MagicMock):
        """Basic config should build 'claude --print -p <prompt>'."""
        mock_run.return_value = MagicMock(stdout="output", stderr="", returncode=0)

        agent = ClaudeAgent()
        config = AgentConfig(prompt="test prompt")
        agent.run(config)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[:4] == ["claude", "--print", "-p", "test prompt"]

    @patch("wiggum.agents_claude.subprocess.run")
    def test_yolo_mode_adds_flag(self, mock_run: MagicMock):
        """yolo=True should add --dangerously-skip-permissions."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = ClaudeAgent()
        config = AgentConfig(prompt="test", yolo=True)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--dangerously-skip-permissions" in cmd

    @patch("wiggum.agents_claude.subprocess.run")
    def test_yolo_false_no_flag(self, mock_run: MagicMock):
        """yolo=False should not add --dangerously-skip-permissions."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = ClaudeAgent()
        config = AgentConfig(prompt="test", yolo=False)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--dangerously-skip-permissions" not in cmd

    @patch("wiggum.agents_claude.subprocess.run")
    def test_continue_session_adds_flag(self, mock_run: MagicMock):
        """continue_session=True should add -c flag."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = ClaudeAgent()
        config = AgentConfig(prompt="test", continue_session=True)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "-c" in cmd

    @patch("wiggum.agents_claude.subprocess.run")
    def test_continue_session_false_no_flag(self, mock_run: MagicMock):
        """continue_session=False should not add -c flag."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = ClaudeAgent()
        config = AgentConfig(prompt="test", continue_session=False)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "-c" not in cmd

    @patch("wiggum.agents_claude.subprocess.run")
    def test_allow_paths_adds_allowed_tools(self, mock_run: MagicMock):
        """allow_paths should add --allowedTools flags for Edit and Write."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = ClaudeAgent()
        config = AgentConfig(prompt="test", allow_paths="src/,tests/")
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        # Should have Edit and Write permissions for each path
        assert "--allowedTools" in cmd
        assert "Edit:src/*" in cmd
        assert "Write:src/*" in cmd
        assert "Edit:tests/*" in cmd
        assert "Write:tests/*" in cmd

    @patch("wiggum.agents_claude.subprocess.run")
    def test_allow_paths_none_no_allowed_tools(self, mock_run: MagicMock):
        """allow_paths=None should not add --allowedTools flags."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = ClaudeAgent()
        config = AgentConfig(prompt="test", allow_paths=None)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--allowedTools" not in cmd
