"""Gemini agent implementation."""

import subprocess

from wiggum.agents import AgentConfig, AgentResult, register_agent


@register_agent
class GeminiAgent:
    """Agent implementation for Google Gemini CLI."""

    @property
    def name(self) -> str:
        """The name of the agent."""
        return "gemini"

    def run(self, config: AgentConfig) -> AgentResult:
        """Run Gemini with the given configuration.

        Args:
            config: Configuration including prompt, security settings, etc.

        Returns:
            AgentResult containing stdout, stderr, and return code.
        """
        cmd = ["gemini", "-p", config.prompt]

        if config.yolo:
            cmd.append("--yolo")

        if config.allow_paths:
            # Gemini uses --include-directories with comma-separated paths
            cmd.extend(["--include-directories", config.allow_paths])

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
                stderr="Error: 'gemini' command not found. Is Gemini CLI installed?",
                return_code=1,
            )
