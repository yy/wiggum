"""Tests for agent-agnostic templates.

Templates should use generic agent terminology instead of Claude-specific
language to support multiple coding agents (Claude, Codex, Gemini, etc.).
"""

from pathlib import Path

from wiggum.config import get_templates_dir


def _get_template_path(filename: str) -> Path:
    """Get the path to a template file, checking local templates/ first."""
    local_path = Path("templates") / filename
    if local_path.exists():
        return local_path
    return get_templates_dir() / filename


class TestLoopPromptAgentAgnostic:
    """Tests that LOOP-PROMPT.md is agent-agnostic."""

    def test_loop_prompt_does_not_mention_claude(self) -> None:
        """LOOP-PROMPT.md should not contain Claude-specific references."""
        template_path = _get_template_path("LOOP-PROMPT.md")
        content = template_path.read_text()

        # The template should not reference Claude specifically
        # (case-insensitive check to catch "Claude", "claude", etc.)
        assert "claude" not in content.lower(), (
            "LOOP-PROMPT.md should not reference Claude specifically"
        )

    def test_loop_prompt_does_not_mention_anthropic(self) -> None:
        """LOOP-PROMPT.md should not contain Anthropic-specific references."""
        template_path = _get_template_path("LOOP-PROMPT.md")
        content = template_path.read_text()

        assert "anthropic" not in content.lower(), (
            "LOOP-PROMPT.md should not reference Anthropic"
        )


class TestMetaPromptAgentAgnostic:
    """Tests that META-PROMPT.md is agent-agnostic."""

    def test_meta_prompt_does_not_mention_claude(self) -> None:
        """META-PROMPT.md should not contain Claude-specific references."""
        template_path = _get_template_path("META-PROMPT.md")
        content = template_path.read_text()

        # The template should not reference Claude specifically
        assert "claude" not in content.lower(), (
            "META-PROMPT.md should not reference Claude specifically"
        )

    def test_meta_prompt_does_not_mention_anthropic(self) -> None:
        """META-PROMPT.md should not contain Anthropic-specific references."""
        template_path = _get_template_path("META-PROMPT.md")
        content = template_path.read_text()

        assert "anthropic" not in content.lower(), (
            "META-PROMPT.md should not reference Anthropic"
        )

    def test_meta_prompt_uses_generic_agent_term(self) -> None:
        """META-PROMPT.md should use generic 'agent' terminology."""
        template_path = _get_template_path("META-PROMPT.md")
        content = template_path.read_text()

        # The template should use generic agent terminology
        assert "agent" in content.lower(), (
            "META-PROMPT.md should use generic 'agent' terminology"
        )


class TestTasksTemplateAgentAgnostic:
    """Tests that TASKS.md template is agent-agnostic."""

    def test_tasks_template_does_not_mention_claude(self) -> None:
        """TASKS.md should not contain Claude-specific references."""
        template_path = _get_template_path("TASKS.md")
        content = template_path.read_text()

        assert "claude" not in content.lower(), (
            "TASKS.md should not reference Claude specifically"
        )
