"""Codex agent implementation."""

import subprocess

from wiggum.agents import AgentConfig, AgentResult, register_agent


@register_agent
class CodexAgent:
    """Agent implementation for OpenAI Codex CLI."""

    @property
    def name(self) -> str:
        """The name of the agent."""
        return "codex"

    def run(self, config: AgentConfig) -> AgentResult:
        """Run Codex with the given configuration.

        Args:
            config: Configuration including prompt, security settings, etc.

        Returns:
            AgentResult containing stdout, stderr, and return code.
        """
        cmd = ["codex", "--json", config.prompt]

        if config.yolo:
            cmd.insert(1, "--yolo")

        if config.allow_paths:
            for path in config.allow_paths.split(","):
                cmd.insert(1, path.strip())
                cmd.insert(1, "--add-dir")

        try:
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            return AgentResult(
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                return_code=result.returncode,
            )
        except FileNotFoundError:
            return AgentResult(
                stdout="",
                stderr="Error: 'codex' command not found. Is OpenAI Codex CLI installed?",
                return_code=1,
            )
