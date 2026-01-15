"""Tests for the Codex agent implementation.

These tests verify the CodexAgent:
1. Implements the Agent protocol correctly
2. Builds the correct CLI commands based on configuration
3. Handles errors appropriately (e.g., missing codex command)
"""

from unittest.mock import MagicMock, patch


from wiggum.agents import Agent, AgentConfig, AgentResult, get_agent


class TestCodexAgentImplementation:
    """Tests that CodexAgent correctly implements the Agent protocol."""

    def test_codex_agent_implements_agent_protocol(self):
        """CodexAgent should implement the Agent protocol."""
        from wiggum.agents_codex import CodexAgent

        agent = CodexAgent()
        assert isinstance(agent, Agent)

    def test_codex_agent_name_is_codex(self):
        """CodexAgent should have name 'codex'."""
        from wiggum.agents_codex import CodexAgent

        agent = CodexAgent()
        assert agent.name == "codex"

    def test_codex_agent_is_registered(self):
        """CodexAgent should be registered in the agent registry."""
        # Ensure the module is imported to trigger registration
        import wiggum.agents_codex  # noqa: F401

        agent = get_agent("codex")
        assert agent.name == "codex"

    def test_codex_agent_available_in_list(self):
        """CodexAgent should appear in available agents list."""
        from wiggum.agents import get_available_agents

        agents = get_available_agents()
        assert "codex" in agents


class TestCodexAgentCommandBuilding:
    """Tests that CodexAgent builds the correct CLI commands."""

    @patch("wiggum.agents_codex.subprocess.run")
    def test_basic_command(self, mock_run: MagicMock):
        """Basic config should build 'codex <prompt>'."""
        from wiggum.agents_codex import CodexAgent

        mock_run.return_value = MagicMock(stdout="output", stderr="", returncode=0)

        agent = CodexAgent()
        config = AgentConfig(prompt="test prompt")
        agent.run(config)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        # Codex takes the prompt as a positional argument
        assert cmd[0] == "codex"
        assert "test prompt" in cmd

    @patch("wiggum.agents_codex.subprocess.run")
    def test_yolo_mode_adds_flag(self, mock_run: MagicMock):
        """yolo=True should add --yolo flag."""
        from wiggum.agents_codex import CodexAgent

        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = CodexAgent()
        config = AgentConfig(prompt="test", yolo=True)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--yolo" in cmd

    @patch("wiggum.agents_codex.subprocess.run")
    def test_yolo_false_no_flag(self, mock_run: MagicMock):
        """yolo=False should not add --yolo flag."""
        from wiggum.agents_codex import CodexAgent

        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = CodexAgent()
        config = AgentConfig(prompt="test", yolo=False)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--yolo" not in cmd

    @patch("wiggum.agents_codex.subprocess.run")
    def test_allow_paths_adds_add_dir(self, mock_run: MagicMock):
        """allow_paths should add --add-dir flags for each path."""
        from wiggum.agents_codex import CodexAgent

        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = CodexAgent()
        config = AgentConfig(prompt="test", allow_paths="src/,tests/")
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        # Should have --add-dir for each path
        assert "--add-dir" in cmd
        assert "src/" in cmd
        assert "tests/" in cmd

    @patch("wiggum.agents_codex.subprocess.run")
    def test_allow_paths_none_no_add_dir(self, mock_run: MagicMock):
        """allow_paths=None should not add --add-dir flags."""
        from wiggum.agents_codex import CodexAgent

        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        agent = CodexAgent()
        config = AgentConfig(prompt="test", allow_paths=None)
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--add-dir" not in cmd

    @patch("wiggum.agents_codex.subprocess.run")
    def test_uses_json_output(self, mock_run: MagicMock):
        """Codex should use --json flag for machine-readable output."""
        from wiggum.agents_codex import CodexAgent

        mock_run.return_value = MagicMock(stdout="output", stderr="", returncode=0)

        agent = CodexAgent()
        config = AgentConfig(prompt="test")
        agent.run(config)

        cmd = mock_run.call_args[0][0]
        assert "--json" in cmd


class TestCodexAgentResult:
    """Tests that CodexAgent returns correct results."""

    @patch("wiggum.agents_codex.subprocess.run")
    def test_returns_agent_result(self, mock_run: MagicMock):
        """run() should return an AgentResult."""
        from wiggum.agents_codex import CodexAgent

        mock_run.return_value = MagicMock(stdout="output", stderr="err", returncode=0)

        agent = CodexAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert isinstance(result, AgentResult)

    @patch("wiggum.agents_codex.subprocess.run")
    def test_captures_stdout(self, mock_run: MagicMock):
        """Result should contain stdout from subprocess."""
        from wiggum.agents_codex import CodexAgent

        mock_run.return_value = MagicMock(stdout="hello world", stderr="", returncode=0)

        agent = CodexAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.stdout == "hello world"

    @patch("wiggum.agents_codex.subprocess.run")
    def test_captures_stderr(self, mock_run: MagicMock):
        """Result should contain stderr from subprocess."""
        from wiggum.agents_codex import CodexAgent

        mock_run.return_value = MagicMock(stdout="", stderr="error msg", returncode=1)

        agent = CodexAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.stderr == "error msg"

    @patch("wiggum.agents_codex.subprocess.run")
    def test_captures_return_code(self, mock_run: MagicMock):
        """Result should contain return code from subprocess."""
        from wiggum.agents_codex import CodexAgent

        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=42)

        agent = CodexAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.return_code == 42

    @patch("wiggum.agents_codex.subprocess.run")
    def test_handles_none_stdout(self, mock_run: MagicMock):
        """Result should handle None stdout gracefully."""
        from wiggum.agents_codex import CodexAgent

        mock_run.return_value = MagicMock(stdout=None, stderr="", returncode=0)

        agent = CodexAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.stdout == ""

    @patch("wiggum.agents_codex.subprocess.run")
    def test_handles_none_stderr(self, mock_run: MagicMock):
        """Result should handle None stderr gracefully."""
        from wiggum.agents_codex import CodexAgent

        mock_run.return_value = MagicMock(stdout="", stderr=None, returncode=0)

        agent = CodexAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.stderr == ""


class TestCodexAgentErrorHandling:
    """Tests that CodexAgent handles errors appropriately."""

    @patch("wiggum.agents_codex.subprocess.run")
    def test_handles_missing_codex_command(self, mock_run: MagicMock):
        """Should return error result when codex command is not found."""
        from wiggum.agents_codex import CodexAgent

        mock_run.side_effect = FileNotFoundError("No such file or directory: 'codex'")

        agent = CodexAgent()
        result = agent.run(AgentConfig(prompt="test"))

        assert result.return_code == 1
        assert "not found" in result.stderr.lower()
        assert result.stdout == ""
