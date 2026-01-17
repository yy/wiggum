"""Agent abstraction layer for wiggum.

This module defines the interface for running different coding agents
(Claude, Codex, Gemini, etc.) with a common input/output contract.
"""

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@dataclass
class AgentResult:
    """Result from running an agent."""

    stdout: str
    stderr: str
    return_code: int


@dataclass
class AgentConfig:
    """Configuration for running an agent."""

    prompt: str
    yolo: bool = False
    allow_paths: Optional[str] = None
    continue_session: bool = False


@runtime_checkable
class Agent(Protocol):
    """Protocol defining the interface for coding agents."""

    @property
    def name(self) -> str:
        """The name of the agent (e.g., 'claude', 'codex', 'gemini')."""
        ...

    def run(self, config: AgentConfig) -> AgentResult:
        """Run the agent with the given configuration.

        Args:
            config: Configuration including prompt, security settings, etc.

        Returns:
            AgentResult containing stdout, stderr, and return code.
        """
        ...


from wiggum.agents_claude import ClaudeAgent
from wiggum.agents_codex import CodexAgent
from wiggum.agents_gemini import GeminiAgent

# Registry mapping agent names to their classes
_agents: dict[str, type] = {
    "claude": ClaudeAgent,
    "codex": CodexAgent,
    "gemini": GeminiAgent,
}


def get_agent(name: Optional[str] = None) -> Agent:
    """Get an agent instance by name.

    Args:
        name: The agent name. If None, returns the default agent (claude).

    Returns:
        An Agent instance.

    Raises:
        ValueError: If the agent name is not found.
    """
    if name is None:
        name = "claude"

    if name not in _agents:
        available = ", ".join(_agents.keys()) if _agents else "none"
        raise ValueError(f"Unknown agent: '{name}'. Available agents: {available}")

    return _agents[name]()


def get_available_agents() -> list[str]:
    """Get a list of available agent names.

    Returns:
        List of registered agent names.
    """
    return list(_agents.keys())
