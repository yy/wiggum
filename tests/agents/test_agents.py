"""Parameterized tests for all agent implementations.

These tests verify that all agents (claude, codex, gemini):
1. Implement the Agent protocol correctly
2. Are registered in the agent registry
3. Return correct AgentResult from run()
4. Handle errors appropriately
"""

import json
import subprocess
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
        """Result should reflect the agent message from subprocess stdout.

        Codex emits JSONL events which the agent compacts into a summary, so
        it needs valid JSONL input; other agents pass stdout through verbatim.
        """
        raw_stdout = {
            "codex": json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "hello world"},
                }
            )
        }.get(name, "hello world")

        with patch(subprocess_path) as mock_run:
            mock_run.return_value = MagicMock(
                stdout=raw_stdout, stderr="", returncode=0
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

    def test_passes_timeout_to_subprocess(
        self, name: str, agent_class: type, subprocess_path: str
    ):
        """run() should pass timeout_seconds to subprocess.run."""
        with patch(subprocess_path) as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
            agent = agent_class()
            agent.run(AgentConfig(prompt="test", timeout_seconds=42))
            assert mock_run.call_args.kwargs["timeout"] == 42


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

    def test_handles_timeout(self, name: str, agent_class: type, subprocess_path: str):
        """Should return timeout error result when subprocess exceeds timeout."""
        with patch(subprocess_path) as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=name, timeout=5)
            agent = agent_class()
            result = agent.run(AgentConfig(prompt="test", timeout_seconds=5))
            assert result.return_code == 124
            assert "timed out" in result.stderr.lower()


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


class TestCheckCliAvailable:
    """Tests for the check_cli_available function."""

    def test_returns_true_for_existing_cli(self):
        """Should return True for a CLI that exists (e.g., python)."""
        from wiggum.agents import check_cli_available

        # 'python' should always be available in test environment
        assert check_cli_available("python") is True

    def test_returns_false_for_nonexistent_cli(self):
        """Should return False for a CLI that doesn't exist."""
        from wiggum.agents import check_cli_available

        assert (
            check_cli_available("nonexistent_cli_that_surely_does_not_exist") is False
        )

    def test_returns_cli_specific_error_message(self):
        """Should return helpful error message for known CLIs."""
        from wiggum.agents import get_cli_error_message

        # Test known CLIs have specific messages
        assert "Claude Code" in get_cli_error_message("claude")
        assert "OpenAI Codex" in get_cli_error_message("codex")
        assert "Gemini CLI" in get_cli_error_message("gemini")
        assert "GitHub CLI" in get_cli_error_message("gh")

    def test_returns_generic_message_for_unknown_cli(self):
        """Should return generic message for unknown CLIs."""
        from wiggum.agents import get_cli_error_message

        msg = get_cli_error_message("some_random_cli")
        assert "some_random_cli" in msg
        assert "not found" in msg.lower()
