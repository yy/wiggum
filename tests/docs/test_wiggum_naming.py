"""Tests to verify documentation uses 'wiggum' consistently, not 'ralph-loop'."""

from pathlib import Path


class TestWiggumNaming:
    """Tests for consistent wiggum naming in documentation."""

    def test_readme_uses_wiggum_not_ralph_loop(self) -> None:
        """README.md should use 'wiggum' commands, not 'ralph-loop'."""
        readme = Path("README.md").read_text()

        # Should not contain ralph-loop command references
        assert "ralph-loop init" not in readme
        assert "ralph-loop run" not in readme
        assert "ralph-loop add" not in readme

        # Should contain wiggum command references
        assert "wiggum init" in readme
        assert "wiggum run" in readme

    def test_claude_md_uses_wiggum_not_ralph_loop(self) -> None:
        """CLAUDE.md should use 'wiggum' commands, not 'ralph-loop'."""
        claude_md = Path("CLAUDE.md").read_text()

        # Should not contain ralph-loop command references
        assert "ralph-loop init" not in claude_md
        assert "ralph-loop run" not in claude_md
        assert "ralph-loop add" not in claude_md

        # Should contain wiggum command references
        assert "wiggum init" in claude_md
        assert "wiggum run" in claude_md

    def test_claude_md_project_description_uses_wiggum(self) -> None:
        """CLAUDE.md project description should reference 'wiggum', not 'ralph-loop'."""
        claude_md = Path("CLAUDE.md").read_text()

        # Project description should use wiggum
        # The first line after "## Project Overview" should mention wiggum
        assert "ralph-loop is a Python package" not in claude_md
        assert "wiggum is a Python package" in claude_md

    def test_claude_md_module_reference_uses_wiggum(self) -> None:
        """CLAUDE.md should reference 'wiggum' module, not 'ralph_loop'."""
        claude_md = Path("CLAUDE.md").read_text()

        # Module reference in run command
        assert "python -m ralph_loop" not in claude_md
        assert "python -m wiggum" in claude_md
