"""Codex agent implementation."""

import json
import subprocess

from wiggum.agents import AgentConfig, AgentResult


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
        cmd = ["codex", "exec", "--json"]

        if config.model:
            cmd.extend(["--model", config.model])
        if config.yolo:
            cmd.append("--dangerously-bypass-approvals-and-sandbox")
        if config.allow_paths:
            for path in config.allow_paths.split(","):
                cmd.extend(["--add-dir", path.strip()])

        cmd.append(config.prompt)

        try:
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=config.timeout_seconds,
            )
            stdout = result.stdout or ""
            compact_stdout = _compact_codex_jsonl(stdout) if stdout else ""
            return AgentResult(
                stdout=compact_stdout,
                stderr=result.stderr or "",
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            timeout = (
                f"{config.timeout_seconds}s"
                if config.timeout_seconds is not None
                else "the configured limit"
            )
            return AgentResult(
                stdout="",
                stderr=f"Error: Codex command timed out after {timeout}",
                return_code=124,
            )
        except FileNotFoundError:
            return AgentResult(
                stdout="",
                stderr="Error: 'codex' command not found. Is OpenAI Codex CLI installed?",
                return_code=1,
            )


def _compact_codex_jsonl(stdout: str) -> str:
    """Return a concise human-readable summary from Codex --json output."""
    messages: list[str] = []
    errors: list[str] = []
    usage: str | None = None
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_type = event.get("type")
        if event_type == "item.completed":
            item = event.get("item", {})
            if item.get("type") == "agent_message":
                text = (item.get("text") or "").strip()
                if text:
                    messages.append(text)
        elif event_type in {"error", "turn.failed"}:
            errors.append(str(event.get("message") or event.get("error") or event))
        elif event_type == "turn.completed" and event.get("usage"):
            u = event["usage"]
            usage = (
                f"tokens in={u.get('input_tokens')}, cached={u.get('cached_input_tokens')}, "
                f"out={u.get('output_tokens')}, reasoning={u.get('reasoning_output_tokens')}"
            )

    parts: list[str] = []
    if messages:
        parts.append(messages[-1])
    if errors:
        parts.append("Errors: " + " | ".join(errors[-3:]))
    if usage:
        parts.append("Usage: " + usage)
    return "\n\n".join(parts) or "(Codex produced no agent message.)"
