"""Tests to verify README.md accuracy against the CLI implementation."""

from pathlib import Path


def test_readme_documents_all_commands() -> None:
    """README should document all CLI commands."""
    readme = Path("README.md").read_text()

    # All commands that should be documented
    commands = ["init", "run", "add"]

    for cmd in commands:
        assert f"ralph-loop {cmd}" in readme, (
            f"README should document 'ralph-loop {cmd}'"
        )


def test_readme_documents_security_toml_config() -> None:
    """README should document .ralph-loop.toml security configuration."""
    readme = Path("README.md").read_text()

    # Should document toml file
    assert ".ralph-loop.toml" in readme
    assert "[security]" in readme
    assert "yolo" in readme
    assert "allow_paths" in readme


def test_readme_documents_key_cli_flags() -> None:
    """README should document key CLI flags."""
    readme = Path("README.md").read_text()

    # Key flags for run command
    key_flags = [
        "--max-iterations",
        "--continue",
        "--reset",
        "--log-file",
        "--verbose",
        "--tasks",
    ]

    for flag in key_flags:
        assert flag in readme, f"README should document '{flag}' flag"


def test_readme_documents_security_modes() -> None:
    """README should document all three security modes."""
    readme = Path("README.md").read_text()

    # Three security modes from init
    assert "Conservative" in readme
    assert "Path-restricted" in readme
    assert "YOLO" in readme
