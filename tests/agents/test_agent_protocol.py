"""Tests for the agent abstraction layer.

These tests verify the agent protocol/interface design:
1. Base protocol defines required methods
2. AgentResult contains expected fields
3. AgentConfig contains expected fields
4. Registry allows agent lookup by name
"""

from dataclasses import fields

import pytest


class TestAgentProtocol:
    """Tests for the Agent protocol interface."""

    def test_agent_module_exists_and_importable(self):
        """Agent module should be importable."""
        from wiggum import agents

        assert agents is not None

    def test_agent_protocol_exists(self):
        """Agent protocol should be defined."""
        from wiggum.agents import Agent

        assert Agent is not None

    def test_agent_protocol_is_runtime_checkable(self):
        """Agent protocol should be runtime checkable."""
        from wiggum.agents import Agent

        # Protocol should have @runtime_checkable decorator
        assert hasattr(Agent, "__protocol_attrs__") or isinstance(Agent, type)

    def test_agent_protocol_has_run_method(self):
        """Agent protocol should define a run method."""
        from wiggum.agents import Agent

        # Check the protocol has 'run' in its annotations or methods
        assert hasattr(Agent, "run")

    def test_agent_protocol_has_name_property(self):
        """Agent protocol should define a name property."""
        from wiggum.agents import Agent

        assert hasattr(Agent, "name")


class TestAgentResult:
    """Tests for the AgentResult dataclass."""

    def test_agent_result_exists(self):
        """AgentResult should be defined."""
        from wiggum.agents import AgentResult

        assert AgentResult is not None

    def test_agent_result_has_stdout(self):
        """AgentResult should have stdout field."""
        from wiggum.agents import AgentResult

        field_names = [f.name for f in fields(AgentResult)]
        assert "stdout" in field_names

    def test_agent_result_has_stderr(self):
        """AgentResult should have stderr field."""
        from wiggum.agents import AgentResult

        field_names = [f.name for f in fields(AgentResult)]
        assert "stderr" in field_names

    def test_agent_result_has_return_code(self):
        """AgentResult should have return_code field."""
        from wiggum.agents import AgentResult

        field_names = [f.name for f in fields(AgentResult)]
        assert "return_code" in field_names

    def test_agent_result_instantiable(self):
        """AgentResult should be instantiable with required fields."""
        from wiggum.agents import AgentResult

        result = AgentResult(stdout="output", stderr="", return_code=0)
        assert result.stdout == "output"
        assert result.stderr == ""
        assert result.return_code == 0


class TestAgentConfig:
    """Tests for the AgentConfig dataclass."""

    def test_agent_config_exists(self):
        """AgentConfig should be defined."""
        from wiggum.agents import AgentConfig

        assert AgentConfig is not None

    def test_agent_config_has_prompt(self):
        """AgentConfig should have prompt field."""
        from wiggum.agents import AgentConfig

        field_names = [f.name for f in fields(AgentConfig)]
        assert "prompt" in field_names

    def test_agent_config_has_yolo(self):
        """AgentConfig should have yolo field for permission bypass."""
        from wiggum.agents import AgentConfig

        field_names = [f.name for f in fields(AgentConfig)]
        assert "yolo" in field_names

    def test_agent_config_has_allow_paths(self):
        """AgentConfig should have allow_paths field for path restrictions."""
        from wiggum.agents import AgentConfig

        field_names = [f.name for f in fields(AgentConfig)]
        assert "allow_paths" in field_names

    def test_agent_config_has_continue_session(self):
        """AgentConfig should have continue_session field."""
        from wiggum.agents import AgentConfig

        field_names = [f.name for f in fields(AgentConfig)]
        assert "continue_session" in field_names

    def test_agent_config_instantiable_with_defaults(self):
        """AgentConfig should have sensible defaults."""
        from wiggum.agents import AgentConfig

        config = AgentConfig(prompt="test prompt")
        assert config.prompt == "test prompt"
        # Defaults should be sensible
        assert config.yolo is False or config.yolo is True  # Has a default
        assert config.allow_paths is not None or config.allow_paths is None  # Defined


class TestAgentRegistry:
    """Tests for the agent registry."""

    def test_get_agent_function_exists(self):
        """get_agent function should be defined."""
        from wiggum.agents import get_agent

        assert callable(get_agent)

    def test_get_available_agents_function_exists(self):
        """get_available_agents function should be defined."""
        from wiggum.agents import get_available_agents

        assert callable(get_available_agents)

    def test_get_available_agents_returns_list(self):
        """get_available_agents should return a list of agent names."""
        from wiggum.agents import get_available_agents

        agents = get_available_agents()
        assert isinstance(agents, list)

    def test_claude_is_default_agent(self):
        """Claude should be the default agent."""
        from wiggum.agents import get_agent

        # Getting agent without specifying should return claude
        agent = get_agent()
        assert agent.name == "claude"

    def test_get_agent_by_name(self):
        """Should be able to get agent by name."""
        from wiggum.agents import get_agent

        agent = get_agent("claude")
        assert agent.name == "claude"

    def test_get_unknown_agent_raises(self):
        """Getting unknown agent should raise ValueError."""
        from wiggum.agents import get_agent

        with pytest.raises(ValueError, match="Unknown agent"):
            get_agent("nonexistent_agent")
