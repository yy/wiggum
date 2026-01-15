"""Tests to verify README.md accuracy against the CLI implementation."""

from pathlib import Path


def test_readme_documents_core_workflow() -> None:
    """README should document the core workflow: init and run."""
    readme = Path("README.md").read_text()

    assert "wiggum init" in readme
    assert "wiggum run" in readme


def test_readme_mentions_key_concepts() -> None:
    """README should mention key concepts."""
    readme = Path("README.md").read_text()

    assert "TASKS.md" in readme
    assert "LOOP-PROMPT.md" in readme


def test_readme_documents_yolo_option() -> None:
    """README should document the yolo option."""
    readme = Path("README.md").read_text()

    assert "yolo" in readme.lower()
