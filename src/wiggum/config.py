"""Configuration handling for ralph-loop."""

from pathlib import Path

CONFIG_FILE = ".wiggum.toml"


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
