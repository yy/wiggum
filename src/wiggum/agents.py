"""Agent abstraction layer for wiggum.

This module defines the interface for running different coding agents
(Claude, Codex, Gemini, etc.) with a common input/output contract.
"""

import shutil
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


# Error messages for known CLIs with installation instructions
_CLI_ERROR_MESSAGES: dict[str, str] = {
    "claude": (
        "Error: 'claude' command not found. "
        "Is Claude Code installed? Visit: https://claude.ai/code"
    ),
    "codex": (
        "Error: 'codex' command not found. "
        "Is OpenAI Codex CLI installed? Run: npm install -g @openai/codex"
    ),
    "gemini": (
        "Error: 'gemini' command not found. "
        "Is Gemini CLI installed? Visit: https://github.com/google-gemini/gemini-cli"
    ),
    "gh": (
        "Error: 'gh' command not found. "
        "Is GitHub CLI installed? Visit: https://cli.github.com/"
    ),
}


def check_cli_available(cli_name: str) -> bool:
    """Check if a CLI command is available in PATH.

    Args:
        cli_name: The name of the CLI to check (e.g., 'claude', 'gh').

    Returns:
        True if the CLI is found in PATH, False otherwise.
    """
    return shutil.which(cli_name) is not None


def get_cli_error_message(cli_name: str) -> str:
    """Get a helpful error message for a missing CLI.

    Args:
        cli_name: The name of the CLI that's missing.

    Returns:
        A user-friendly error message with installation hints.
    """
    if cli_name in _CLI_ERROR_MESSAGES:
        return _CLI_ERROR_MESSAGES[cli_name]
    return f"Error: '{cli_name}' command not found. Please install it and try again."


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
