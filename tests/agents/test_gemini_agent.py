"""Tests for Gemini-specific command building.

These tests verify the GeminiAgent builds the correct CLI commands
based on configuration. Common agent behavior (protocol compliance,
result handling, error handling) is tested in test_agents.py.
"""

from unittest.mock import MagicMock, patch

from wiggum.agents import AgentConfig
from wiggum.agents_gemini import GeminiAgent


class TestGeminiAgentCommandBuilding:
    """Tests that GeminiAgent builds the correct CLI commands."""

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_basic_command(self, mock_run: MagicMock):
        """Basic config should build 'gemini -p <prompt>'."""
        mock_run.return_value = MagicMock(stdout="output", stderr="", returncode=0)

        agent = GeminiAgent()
        config = AgentConfig(prompt="test prompt")
        agent.run(config)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd == ["gemini", "-p", "test prompt"]

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_yolo_mode_adds_flag(self, mock_run: MagicMock):
        """yolo=True should add --yolo flag."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = GeminiAgent()
        config = AgentConfig(prompt="test", yolo=True)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--yolo" in cmd

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_yolo_false_no_flag(self, mock_run: MagicMock):
        """yolo=False should not add --yolo flag."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = GeminiAgent()
        config = AgentConfig(prompt="test", yolo=False)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--yolo" not in cmd

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_allow_paths_adds_include_directories(self, mock_run: MagicMock):
        """allow_paths should add --include-directories with paths."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = GeminiAgent()
        config = AgentConfig(prompt="test", allow_paths="src/,tests/")
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--include-directories" in cmd
        assert "src/,tests/" in cmd

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_allow_paths_none_no_include_directories(self, mock_run: MagicMock):
        """allow_paths=None should not add --include-directories flag."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = GeminiAgent()
        config = AgentConfig(prompt="test", allow_paths=None)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--include-directories" not in cmd
