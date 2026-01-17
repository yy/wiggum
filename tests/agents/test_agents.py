"""Parameterized tests for all agent implementations.

These tests verify that all agents (claude, codex, gemini):
1. Implement the Agent protocol correctly
2. Are registered in the agent registry
3. Return correct AgentResult from run()
4. Handle errors appropriately
"""

from unittest.mock import MagicMock, patch

import pytest

from wiggum.agents import (
    Agent,
    AgentConfig,
    AgentResult,
    get_agent,
    get_available_agents,
)
from wiggum.agents_claude import ClaudeAgent
from wiggum.agents_codex import CodexAgent
from wiggum.agents_gemini import GeminiAgent


# Map agent names to their classes and subprocess module paths
AGENT_TEST_DATA = [
    ("claude", ClaudeAgent, "wiggum.agents_claude.subprocess.run"),
    ("codex", CodexAgent, "wiggum.agents_codex.subprocess.run"),
    ("gemini", GeminiAgent, "wiggum.agents_gemini.subprocess.run"),
]


@pytest.mark.parametrize(
    "name,agent_class,_", AGENT_TEST_DATA, ids=["claude", "codex", "gemini"]
)
class TestAgentProtocol:
    """Tests that all agents correctly implement the Agent protocol."""

    def test_implements_agent_protocol(self, name: str, agent_class: type, _: str):
        """Agent should implement the Agent protocol."""
        agent = agent_class()
        assert isinstance(agent, Agent)

    def test_agent_name_matches(self, name: str, agent_class: type, _: str):
        """Agent.name should match expected name."""
        agent = agent_class()
        assert agent.name == name

    def test_agent_is_registered(self, name: str, agent_class: type, _: str):
        """Agent should be registered in the agent registry."""
        agent = get_agent(name)
        assert agent.name == name
        assert isinstance(agent, agent_class)


@pytest.mark.parametrize(
    "name,agent_class,subprocess_path",
    AGENT_TEST_DATA,
    ids=["claude", "codex", "gemini"],
)
class TestAgentResult:
    """Tests that all agents return correct AgentResult from run()."""

    def test_returns_agent_result(
        self, name: str, agent_class: type, subprocess_path: str
    ):
        """run() should return an AgentResult."""
        with patch(subprocess_path) as mock_run:
            mock_run.return_value = MagicMock(
                stdout="output", stderr="err", returncode=0
            )
            agent = agent_class()
            result = agent.run(AgentConfig(prompt="test"))
            assert isinstance(result, AgentResult)

    def test_captures_stdout(self, name: str, agent_class: type, subprocess_path: str):
        """Result should contain stdout from subprocess."""
        with patch(subprocess_path) as mock_run:
            mock_run.return_value = MagicMock(
                stdout="hello world", stderr="", returncode=0
            )
            agent = agent_class()
            result = agent.run(AgentConfig(prompt="test"))
            assert result.stdout == "hello world"

    def test_captures_stderr(self, name: str, agent_class: type, subprocess_path: str):
        """Result should contain stderr from subprocess."""
        with patch(subprocess_path) as mock_run:
            mock_run.return_value = MagicMock(
                stdout="", stderr="error msg", returncode=1
            )
            agent = agent_class()
            result = agent.run(AgentConfig(prompt="test"))
            assert result.stderr == "error msg"

    def test_captures_return_code(
        self, name: str, agent_class: type, subprocess_path: str
    ):
        """Result should contain return code from subprocess."""
        with patch(subprocess_path) as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=42)
            agent = agent_class()
            result = agent.run(AgentConfig(prompt="test"))
            assert result.return_code == 42

    def test_handles_none_stdout(
        self, name: str, agent_class: type, subprocess_path: str
    ):
        """Result should handle None stdout gracefully."""
        with patch(subprocess_path) as mock_run:
            mock_run.return_value = MagicMock(stdout=None, stderr="", returncode=0)
            agent = agent_class()
            result = agent.run(AgentConfig(prompt="test"))
            assert result.stdout == ""

    def test_handles_none_stderr(
        self, name: str, agent_class: type, subprocess_path: str
    ):
        """Result should handle None stderr gracefully."""
        with patch(subprocess_path) as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr=None, returncode=0)
            agent = agent_class()
            result = agent.run(AgentConfig(prompt="test"))
            assert result.stderr == ""


@pytest.mark.parametrize(
    "name,agent_class,subprocess_path",
    AGENT_TEST_DATA,
    ids=["claude", "codex", "gemini"],
)
class TestAgentErrorHandling:
    """Tests that all agents handle errors appropriately."""

    def test_handles_missing_command(
        self, name: str, agent_class: type, subprocess_path: str
    ):
        """Should return error result when command is not found."""
        with patch(subprocess_path) as mock_run:
            mock_run.side_effect = FileNotFoundError(
                f"No such file or directory: '{name}'"
            )
            agent = agent_class()
            result = agent.run(AgentConfig(prompt="test"))
            assert result.return_code == 1
            assert "not found" in result.stderr.lower()
            assert result.stdout == ""


class TestAgentRegistry:
    """Tests for the agent registry."""

    def test_get_available_agents_returns_all(self):
        """get_available_agents should return all registered agent names."""
        agents = get_available_agents()
        assert "claude" in agents
        assert "codex" in agents
        assert "gemini" in agents

    def test_claude_is_default_agent(self):
        """Claude should be the default agent."""
        agent = get_agent()
        assert agent.name == "claude"

    def test_unknown_agent_raises_error(self):
        """get_agent should raise ValueError for unknown agent."""
        with pytest.raises(ValueError, match="Unknown agent"):
            get_agent("unknown_agent")
