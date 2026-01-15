"""Tests for the Claude agent implementation.

These tests verify the ClaudeAgent:
1. Implements the Agent protocol correctly
2. Builds the correct CLI commands based on configuration
3. Handles errors appropriately (e.g., missing claude command)
"""

from unittest.mock import MagicMock, patch


from wiggum.agents import Agent, AgentConfig, AgentResult, get_agent
from wiggum.agents_claude import ClaudeAgent


class TestClaudeAgentImplementation:
    """Tests that ClaudeAgent correctly implements the Agent protocol."""

    def test_claude_agent_implements_agent_protocol(self):
        """ClaudeAgent should implement the Agent protocol."""
        agent = ClaudeAgent()
        assert isinstance(agent, Agent)

    def test_claude_agent_name_is_claude(self):
        """ClaudeAgent should have name 'claude'."""
        agent = ClaudeAgent()
        assert agent.name == "claude"

    def test_claude_agent_is_registered(self):
        """ClaudeAgent should be registered in the agent registry."""
        agent = get_agent("claude")
        assert agent.name == "claude"
        assert isinstance(agent, ClaudeAgent)

    def test_claude_agent_is_default(self):
        """ClaudeAgent should be the default agent."""
        agent = get_agent()
        assert agent.name == "claude"


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


class TestClaudeAgentResult:
    """Tests that ClaudeAgent returns correct results."""

    @patch("wiggum.agents_claude.subprocess.run")
    def test_returns_agent_result(self, mock_run: MagicMock):
        """run() should return an AgentResult."""
        mock_run.return_value = MagicMock(stdout="output", stderr="err", returncode=0)

        agent = ClaudeAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert isinstance(result, AgentResult)

    @patch("wiggum.agents_claude.subprocess.run")
    def test_captures_stdout(self, mock_run: MagicMock):
        """Result should contain stdout from subprocess."""
        mock_run.return_value = MagicMock(stdout="hello world", stderr="", returncode=0)

        agent = ClaudeAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.stdout == "hello world"

    @patch("wiggum.agents_claude.subprocess.run")
    def test_captures_stderr(self, mock_run: MagicMock):
        """Result should contain stderr from subprocess."""
        mock_run.return_value = MagicMock(stdout="", stderr="error msg", returncode=1)

        agent = ClaudeAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.stderr == "error msg"

    @patch("wiggum.agents_claude.subprocess.run")
    def test_captures_return_code(self, mock_run: MagicMock):
        """Result should contain return code from subprocess."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=42)

        agent = ClaudeAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.return_code == 42

    @patch("wiggum.agents_claude.subprocess.run")
    def test_handles_none_stdout(self, mock_run: MagicMock):
        """Result should handle None stdout gracefully."""
        mock_run.return_value = MagicMock(stdout=None, stderr="", returncode=0)

        agent = ClaudeAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.stdout == ""

    @patch("wiggum.agents_claude.subprocess.run")
    def test_handles_none_stderr(self, mock_run: MagicMock):
        """Result should handle None stderr gracefully."""
        mock_run.return_value = MagicMock(stdout="", stderr=None, returncode=0)

        agent = ClaudeAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.stderr == ""


class TestClaudeAgentErrorHandling:
    """Tests that ClaudeAgent handles errors appropriately."""

    @patch("wiggum.agents_claude.subprocess.run")
    def test_handles_missing_claude_command(self, mock_run: MagicMock):
        """Should return error result when claude command is not found."""
        mock_run.side_effect = FileNotFoundError("No such file or directory: 'claude'")

        agent = ClaudeAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.return_code == 1
        assert "not found" in result.stderr.lower()
        assert result.stdout == ""
