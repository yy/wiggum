"""Claude agent implementation."""

import subprocess

from wiggum.agents import AgentConfig, AgentResult, register_agent


@register_agent
class ClaudeAgent:
    """Agent implementation for Claude Code CLI."""

    @property
    def name(self) -> str:
        """The name of the agent."""
        return "claude"

    def run(self, config: AgentConfig) -> AgentResult:
        """Run Claude with the given configuration.

        Args:
            config: Configuration including prompt, security settings, etc.

        Returns:
            AgentResult containing stdout, stderr, and return code.
        """
        cmd = ["claude", "--print", "-p", config.prompt]

        if config.continue_session:
            cmd.append("-c")

        if config.yolo:
            cmd.append("--dangerously-skip-permissions")

        if config.allow_paths:
            for path in config.allow_paths.split(","):
                cmd.extend(["--allowedTools", f"Edit:{path.strip()}*"])
                cmd.extend(["--allowedTools", f"Write:{path.strip()}*"])

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
                stderr="Error: 'claude' command not found. Is Claude Code installed?",
                return_code=1,
            )
