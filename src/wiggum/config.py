"""Configuration handling for wiggum."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

CONFIG_FILE = ".wiggum.toml"

# Config schema with type information
# Format: {section: {key: (default_value, expected_type)}}
CONFIG_SCHEMA: dict[str, dict[str, tuple]] = {
    "security": {
        "yolo": (False, bool),
        "allow_paths": ("", str),
    },
    "loop": {
        "max_iterations": (10, int),
        "agent": ("claude", str),
        "keep_running": (False, bool),
        "tasks_file": ("TASKS.md", str),
        "prompt_file": ("LOOP-PROMPT.md", str),
    },
    "git": {
        "enabled": (False, bool),
        "branch_prefix": ("wiggum", str),
        "auto_pr": (False, bool),
    },
    "output": {
        "verbose": (False, bool),
        "log_file": ("", str),
    },
    "session": {
        "continue_session": (False, bool),
    },
}


@dataclass
class ConfigValidationResult:
    """Result of config validation."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Returns True if there are no errors."""
        return len(self.errors) == 0


def _find_similar_key(key: str, valid_keys: list[str]) -> Optional[str]:
    """Find a similar key from valid_keys (simple typo detection).

    Uses basic edit distance heuristic: if keys share a prefix/suffix
    or differ by just a character, they're likely typos.
    """
    for valid_key in valid_keys:
        # Exact match minus one char (e.g., max_iteration vs max_iterations)
        if (
            key in valid_key
            or valid_key in key
            or (len(key) > 3 and len(valid_key) > 3 and key[:4] == valid_key[:4])
        ):
            return valid_key
    return None


def validate_config(config: dict) -> ConfigValidationResult:
    """Validate configuration against the schema.

    Checks for:
    - Unknown sections (warning)
    - Unknown keys in known sections (warning with suggestions)
    - Wrong types for known keys (error)
    - Invalid agent names (error)

    Args:
        config: Configuration dict to validate.

    Returns:
        ConfigValidationResult with errors and warnings.
    """
    result = ConfigValidationResult()

    # Import here to avoid circular dependency
    from wiggum.agents import get_available_agents

    known_sections = set(CONFIG_SCHEMA.keys())

    for section, options in config.items():
        # Check for unknown sections
        if section not in known_sections:
            result.warnings.append(f"Unknown config section: [{section}]")
            continue

        if not isinstance(options, dict):
            result.errors.append(
                f"Section [{section}] should be a table, got {type(options).__name__}"
            )
            continue

        known_keys = set(CONFIG_SCHEMA[section].keys())

        for key, value in options.items():
            # Check for unknown keys in known sections
            if key not in known_keys:
                similar = _find_similar_key(key, list(known_keys))
                if similar:
                    result.warnings.append(
                        f"Unknown key '{key}' in [{section}]. Did you mean '{similar}'?"
                    )
                else:
                    result.warnings.append(f"Unknown key '{key}' in [{section}]")
                continue

            # Type validation
            _default, expected_type = CONFIG_SCHEMA[section][key]
            if not isinstance(value, expected_type):
                result.errors.append(
                    f"Config [{section}].{key} should be {expected_type.__name__}, "
                    f"got {type(value).__name__} ({value!r})"
                )
                continue

            # Special validation for agent name
            if section == "loop" and key == "agent":
                available = get_available_agents()
                if value not in available:
                    result.errors.append(
                        f"Invalid agent '{value}' in config. "
                        f"Available agents: {', '.join(available)}"
                    )

    return result


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
    create_pr: bool
    no_branch: bool
    force: bool
    branch_prefix: str


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
    create_pr: bool = False,
    no_branch: bool = False,
    force: bool = False,
    branch_prefix: Optional[str] = None,
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
        create_pr: CLI --pr flag
        no_branch: CLI --no-branch flag
        force: CLI --force flag
        branch_prefix: CLI --branch-prefix value

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

    # Resolve git config
    git_config = config.get("git", {})
    resolved_create_pr = create_pr
    if not create_pr and git_config.get("auto_pr", False):
        resolved_create_pr = True
    resolved_no_branch = no_branch
    resolved_force = force
    resolved_branch_prefix = branch_prefix
    if branch_prefix is None:
        resolved_branch_prefix = git_config.get("branch_prefix", "wiggum")

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
        create_pr=resolved_create_pr,
        no_branch=resolved_no_branch,
        force=resolved_force,
        branch_prefix=resolved_branch_prefix,
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
        Templates directory path. Checks for local 'templates/' first
        (only if it contains wiggum templates), then falls back to package templates.
    """
    if override is not None:
        return override
    # Only use local templates/ if it contains wiggum templates
    local_templates = Path("templates")
    if local_templates.is_dir() and (local_templates / "LOOP-PROMPT.md").exists():
        return local_templates
    return get_templates_dir()
