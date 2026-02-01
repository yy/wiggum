"""Learning diary operations for wiggum sessions."""

from pathlib import Path
from typing import Optional

from wiggum.agents import AgentConfig, get_agent
from wiggum.config import resolve_templates_dir

DIARY_DIR = Path(".wiggum")
DIARY_PATH = DIARY_DIR / "session-diary.md"


def ensure_diary_dir() -> None:
    """Create .wiggum/ directory if needed."""
    DIARY_DIR.mkdir(exist_ok=True)


def has_diary_content() -> bool:
    """Check if diary exists and has learnings.

    Returns:
        True if diary file exists and contains content beyond whitespace.
    """
    if not DIARY_PATH.exists():
        return False
    try:
        content = DIARY_PATH.read_text().strip()
        return len(content) > 0
    except OSError:
        return False


def read_diary() -> str:
    """Read diary content.

    Returns:
        Diary content as string, or empty string if no diary exists or on error.
    """
    if not DIARY_PATH.exists():
        return ""
    try:
        return DIARY_PATH.read_text()
    except OSError:
        return ""


def clear_diary() -> None:
    """Delete diary file."""
    if DIARY_PATH.exists():
        DIARY_PATH.unlink()


def consolidate_learnings(agent_name: Optional[str], yolo: bool) -> bool:
    """Run agent to consolidate diary into CLAUDE.md.

    Args:
        agent_name: Name of agent to use (None for default).
        yolo: Whether to skip permission prompts.

    Returns:
        True if consolidation was successful, False otherwise.
    """
    if not has_diary_content():
        return False

    # Read diary content
    diary_content = read_diary()

    # Read existing CLAUDE.md (if any)
    claude_md_path = Path("CLAUDE.md")
    claude_md_content = ""
    if claude_md_path.exists():
        claude_md_content = claude_md_path.read_text()

    # Read consolidation prompt template
    templates_dir = resolve_templates_dir()
    consolidate_template_path = templates_dir / "CONSOLIDATE-PROMPT.md"

    if not consolidate_template_path.exists():
        return False

    # Build the consolidation prompt
    prompt_template = consolidate_template_path.read_text()
    prompt = prompt_template.replace("{diary_content}", diary_content)
    prompt = prompt.replace(
        "{claude_md_content}", claude_md_content or "(No CLAUDE.md exists)"
    )

    # Run the agent
    agent = get_agent(agent_name)
    agent_config = AgentConfig(
        prompt=prompt,
        yolo=yolo,
        allow_paths=None,
        continue_session=False,
    )

    result = agent.run(agent_config)
    return result.return_code == 0
