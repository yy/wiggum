"""Tests for the Gemini agent implementation.

These tests verify the GeminiAgent:
1. Implements the Agent protocol correctly
2. Builds the correct CLI commands based on configuration
3. Handles errors appropriately (e.g., missing gemini command)
"""

from unittest.mock import MagicMock, patch


from wiggum.agents import Agent, AgentConfig, AgentResult, get_agent


class TestGeminiAgentImplementation:
    """Tests that GeminiAgent correctly implements the Agent protocol."""

    def test_gemini_agent_implements_agent_protocol(self):
        """GeminiAgent should implement the Agent protocol."""
        from wiggum.agents_gemini import GeminiAgent

        agent = GeminiAgent()
        assert isinstance(agent, Agent)

    def test_gemini_agent_name_is_gemini(self):
        """GeminiAgent should have name 'gemini'."""
        from wiggum.agents_gemini import GeminiAgent

        agent = GeminiAgent()
        assert agent.name == "gemini"

    def test_gemini_agent_is_registered(self):
        """GeminiAgent should be registered in the agent registry."""
        # Ensure the module is imported to trigger registration
        import wiggum.agents_gemini  # noqa: F401

        agent = get_agent("gemini")
        assert agent.name == "gemini"

    def test_gemini_agent_available_in_list(self):
        """GeminiAgent should appear in available agents list."""
        from wiggum.agents import get_available_agents

        agents = get_available_agents()
        assert "gemini" in agents


class TestGeminiAgentCommandBuilding:
    """Tests that GeminiAgent builds the correct CLI commands."""

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_basic_command(self, mock_run: MagicMock):
        """Basic config should build 'gemini -p <prompt>'."""
        from wiggum.agents_gemini import GeminiAgent

        mock_run.return_value = MagicMock(stdout="output", stderr="", returncode=0)

        agent = GeminiAgent()
        config = AgentConfig(prompt="test prompt")
        agent.run(config)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "gemini"
        assert "-p" in cmd
        assert "test prompt" in cmd

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_yolo_mode_adds_flag(self, mock_run: MagicMock):
        """yolo=True should add --yolo flag."""
        from wiggum.agents_gemini import GeminiAgent

        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = GeminiAgent()
        config = AgentConfig(prompt="test", yolo=True)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--yolo" in cmd

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_yolo_false_no_flag(self, mock_run: MagicMock):
        """yolo=False should not add --yolo flag."""
        from wiggum.agents_gemini import GeminiAgent

        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = GeminiAgent()
        config = AgentConfig(prompt="test", yolo=False)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--yolo" not in cmd

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_allow_paths_adds_include_directories(self, mock_run: MagicMock):
        """allow_paths should add --include-directories flag with paths."""
        from wiggum.agents_gemini import GeminiAgent

        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = GeminiAgent()
        config = AgentConfig(prompt="test", allow_paths="src/,tests/")
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--include-directories" in cmd
        # The paths should be comma-separated after --include-directories
        idx = cmd.index("--include-directories")
        assert "src/" in cmd[idx + 1]
        assert "tests/" in cmd[idx + 1]

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_allow_paths_none_no_include_directories(self, mock_run: MagicMock):
        """allow_paths=None should not add --include-directories flag."""
        from wiggum.agents_gemini import GeminiAgent

        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = GeminiAgent()
        config = AgentConfig(prompt="test", allow_paths=None)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--include-directories" not in cmd


class TestGeminiAgentResult:
    """Tests that GeminiAgent returns correct results."""

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_returns_agent_result(self, mock_run: MagicMock):
        """run() should return an AgentResult."""
        from wiggum.agents_gemini import GeminiAgent

        mock_run.return_value = MagicMock(stdout="output", stderr="err", returncode=0)

        agent = GeminiAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert isinstance(result, AgentResult)

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_captures_stdout(self, mock_run: MagicMock):
        """Result should contain stdout from subprocess."""
        from wiggum.agents_gemini import GeminiAgent

        mock_run.return_value = MagicMock(stdout="hello world", stderr="", returncode=0)

        agent = GeminiAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.stdout == "hello world"

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_captures_stderr(self, mock_run: MagicMock):
        """Result should contain stderr from subprocess."""
        from wiggum.agents_gemini import GeminiAgent

        mock_run.return_value = MagicMock(stdout="", stderr="error msg", returncode=1)

        agent = GeminiAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.stderr == "error msg"

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_captures_return_code(self, mock_run: MagicMock):
        """Result should contain return code from subprocess."""
        from wiggum.agents_gemini import GeminiAgent

        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=42)

        agent = GeminiAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.return_code == 42

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_handles_none_stdout(self, mock_run: MagicMock):
        """Result should handle None stdout gracefully."""
        from wiggum.agents_gemini import GeminiAgent

        mock_run.return_value = MagicMock(stdout=None, stderr="", returncode=0)

        agent = GeminiAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.stdout == ""

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_handles_none_stderr(self, mock_run: MagicMock):
        """Result should handle None stderr gracefully."""
        from wiggum.agents_gemini import GeminiAgent

        mock_run.return_value = MagicMock(stdout="", stderr=None, returncode=0)

        agent = GeminiAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.stderr == ""


class TestGeminiAgentErrorHandling:
    """Tests that GeminiAgent handles errors appropriately."""

    @patch("wiggum.agents_gemini.subprocess.run")
    def test_handles_missing_gemini_command(self, mock_run: MagicMock):
        """Should return error result when gemini command is not found."""
        from wiggum.agents_gemini import GeminiAgent

        mock_run.side_effect = FileNotFoundError("No such file or directory: 'gemini'")

        agent = GeminiAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.return_code == 1
        assert "not found" in result.stderr.lower()
        assert result.stdout == ""
