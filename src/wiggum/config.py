"""Configuration handling for wiggum."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

CONFIG_FILE = ".wiggum.toml"


@dataclass
class ResolvedRunConfig:
    """Resolved configuration for the run command.

    All values are resolved from CLI flags, config file, and defaults.
    CLI flags take precedence over config file values.
    """

    yolo: bool
    allow_paths: Optional[str]
    max_iterations: int
    tasks_file: Path
    prompt_file: Optional[Path]
    agent: Optional[str]
    log_file: Optional[Path]
    show_progress: bool
    continue_session: bool
    keep_running: bool


def resolve_run_config(
    *,
    yolo: bool,
    allow_paths: Optional[str],
    max_iterations: Optional[int],
    tasks_file: Optional[Path],
    prompt_file: Optional[Path],
    agent: Optional[str],
    log_file: Optional[Path],
    show_progress: bool,
    continue_session: bool,
    reset_session: bool,
    keep_running: bool,
    stop_when_done: bool,
) -> ResolvedRunConfig:
    """Resolve run configuration from CLI flags and config file.

    CLI flags take precedence over config file values. Returns a
    ResolvedRunConfig with all values resolved.

    Args:
        yolo: CLI --yolo flag value
        allow_paths: CLI --allow-paths value
        max_iterations: CLI -n/--max-iterations value
        tasks_file: CLI --tasks value
        prompt_file: CLI -f/--file value
        agent: CLI --agent value
        log_file: CLI --log-file value
        show_progress: CLI -v/--verbose value
        continue_session: CLI --continue flag
        reset_session: CLI --reset flag
        keep_running: CLI --keep-running flag
        stop_when_done: CLI --stop-when-done flag

    Returns:
        ResolvedRunConfig with all values resolved.

    Raises:
        ValueError: If mutually exclusive flags are both set.
    """
    config = read_config()
    security_config = config.get("security", {})
    loop_config = config.get("loop", {})
    output_config = config.get("output", {})
    session_config = config.get("session", {})

    # Resolve security config (CLI flags override config)
    resolved_yolo = yolo
    if not yolo and security_config.get("yolo", False):
        resolved_yolo = True
    resolved_allow_paths = allow_paths
    if allow_paths is None and security_config.get("allow_paths"):
        resolved_allow_paths = security_config.get("allow_paths")

    # Resolve loop config
    resolved_max_iterations = max_iterations
    if max_iterations is None:
        resolved_max_iterations = loop_config.get("max_iterations", 10)
    resolved_tasks_file = tasks_file
    if tasks_file is None:
        resolved_tasks_file = Path(loop_config.get("tasks_file", "TASKS.md"))
    resolved_prompt_file = prompt_file
    if prompt_file is None:
        config_prompt_file = loop_config.get("prompt_file")
        if config_prompt_file:
            resolved_prompt_file = Path(config_prompt_file)
    resolved_agent = agent
    if agent is None:
        resolved_agent = loop_config.get("agent")

    # Resolve output config
    resolved_log_file = log_file
    if log_file is None and output_config.get("log_file"):
        resolved_log_file = Path(output_config.get("log_file"))
    resolved_show_progress = show_progress
    if not show_progress and output_config.get("verbose", False):
        resolved_show_progress = True

    # Resolve session config
    resolved_continue_session = continue_session
    if not continue_session and not reset_session:
        if session_config.get("continue_session", False):
            resolved_continue_session = True

    # Check mutually exclusive flags
    if continue_session and reset_session:
        raise ValueError(
            "--continue and --reset are mutually exclusive. Cannot use both."
        )
    if keep_running and stop_when_done:
        raise ValueError(
            "--keep-running and --stop-when-done are mutually exclusive. Cannot use both."
        )

    # Resolve keep_running
    resolved_keep_running = keep_running
    if not keep_running and not stop_when_done:
        if loop_config.get("keep_running", False):
            resolved_keep_running = True

    return ResolvedRunConfig(
        yolo=resolved_yolo,
        allow_paths=resolved_allow_paths,
        max_iterations=resolved_max_iterations,
        tasks_file=resolved_tasks_file,
        prompt_file=resolved_prompt_file,
        agent=resolved_agent,
        log_file=resolved_log_file,
        show_progress=resolved_show_progress,
        continue_session=resolved_continue_session,
        keep_running=resolved_keep_running,
    )


def read_config() -> dict:
    """Read configuration from .wiggum.toml.

    Returns:
        Configuration dict with 'security' section containing 'yolo' and 'allow_paths'.
        Returns empty dict if file doesn't exist.
    """
    config_path = Path(CONFIG_FILE)
    if not config_path.exists():
        return {}

    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        return tomllib.loads(config_path.read_text())
    except Exception:
        return {}


def write_config(config: dict) -> None:
    """Write configuration to .wiggum.toml.

    Args:
        config: Configuration dict to write.
    """
    import tomli_w

    config_path = Path(CONFIG_FILE)
    config_path.write_text(tomli_w.dumps(config))


def get_templates_dir() -> Path:
    """Get the templates directory from the package."""
    import importlib.resources

    return Path(str(importlib.resources.files("wiggum"))) / "templates"


def resolve_templates_dir(override: Path | None = None) -> Path:
    """Resolve the templates directory, with local override support.

    Args:
        override: Explicit templates directory to use. If provided, returns this.

    Returns:
        Templates directory path. Checks for local 'templates/' first,
        then falls back to package templates.
    """
    if override is not None:
        return override
    if Path("templates").is_dir():
        return Path("templates")
    return get_templates_dir()
