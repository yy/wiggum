"""Tests for metaprompt constraint suggestions during init.

This tests that the metaprompt asks Claude to suggest security constraints
based on the project context, and that the init command parses and uses
these suggestions.
"""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from wiggum.cli import app, parse_markdown_from_output

runner = CliRunner()


class TestParseConstraintsFromMarkdown:
    """Tests for parsing constraints from Claude's markdown output."""

    def test_parses_constraints_section(self) -> None:
        """Should extract constraints from ## Constraints section."""
        output = """```markdown
## Goal

Build a CLI tool

## Tasks

- [ ] Set up project structure

## Constraints

security_mode: yolo
allow_paths: src/,tests/
internet_access: true
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert "constraints" in result
        assert result["constraints"]["security_mode"] == "yolo"
        assert result["constraints"]["allow_paths"] == "src/,tests/"
        assert result["constraints"]["internet_access"] is True

    def test_parses_conservative_security_mode(self) -> None:
        """Should parse conservative security mode."""
        output = """```markdown
## Goal

Build a testing framework

## Tasks

- [ ] Create tests

## Constraints

security_mode: conservative
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["constraints"]["security_mode"] == "conservative"

    def test_parses_path_restricted_security_mode(self) -> None:
        """Should parse path-restricted security mode with paths."""
        output = """```markdown
## Goal

Build an API

## Tasks

- [ ] Create endpoints

## Constraints

security_mode: path_restricted
allow_paths: api/,models/,tests/
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["constraints"]["security_mode"] == "path_restricted"
        assert result["constraints"]["allow_paths"] == "api/,models/,tests/"

    def test_handles_missing_constraints_section(self) -> None:
        """Should return empty constraints when section is missing."""
        output = """```markdown
## Goal

Build something

## Tasks

- [ ] First task
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        # Should still parse goal and tasks even without constraints
        assert result["goal"] == "Build something"
        assert "constraints" in result
        assert result["constraints"] == {}

    def test_parses_internet_access_false(self) -> None:
        """Should parse internet_access: false."""
        output = """```markdown
## Goal

Offline tool

## Tasks

- [ ] Build it

## Constraints

security_mode: conservative
internet_access: false
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["constraints"]["internet_access"] is False

    def test_handles_various_boolean_formats(self) -> None:
        """Should handle different boolean formats for internet_access."""
        # Test 'yes' as true
        output = """```markdown
## Goal

Test

## Tasks

- [ ] Task

## Constraints

internet_access: yes
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["constraints"]["internet_access"] is True

        # Test 'no' as false
        output = """```markdown
## Goal

Test

## Tasks

- [ ] Task

## Constraints

internet_access: no
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["constraints"]["internet_access"] is False


class TestMetapromptIncludesConstraintGuidance:
    """Tests that META-PROMPT.md asks Claude about constraints."""

    def test_metaprompt_mentions_security_constraints(self) -> None:
        """META-PROMPT.md should mention security constraints."""
        metaprompt_path = Path("templates/META-PROMPT.md")
        if not metaprompt_path.exists():
            # Try package location
            from wiggum.cli import get_templates_dir

            metaprompt_path = get_templates_dir() / "META-PROMPT.md"

        content = metaprompt_path.read_text()
        assert "constraints" in content.lower() or "Constraints" in content

    def test_metaprompt_mentions_yolo_option(self) -> None:
        """META-PROMPT.md should mention yolo as an option."""
        metaprompt_path = Path("templates/META-PROMPT.md")
        if not metaprompt_path.exists():
            from wiggum.cli import get_templates_dir

            metaprompt_path = get_templates_dir() / "META-PROMPT.md"

        content = metaprompt_path.read_text()
        assert "yolo" in content.lower()

    def test_metaprompt_mentions_path_restrictions(self) -> None:
        """META-PROMPT.md should mention path restriction option."""
        metaprompt_path = Path("templates/META-PROMPT.md")
        if not metaprompt_path.exists():
            from wiggum.cli import get_templates_dir

            metaprompt_path = get_templates_dir() / "META-PROMPT.md"

        content = metaprompt_path.read_text()
        assert "path" in content.lower()

    def test_metaprompt_mentions_internet_access(self) -> None:
        """META-PROMPT.md should mention internet access option."""
        metaprompt_path = Path("templates/META-PROMPT.md")
        if not metaprompt_path.exists():
            from wiggum.cli import get_templates_dir

            metaprompt_path = get_templates_dir() / "META-PROMPT.md"

        content = metaprompt_path.read_text()
        assert "internet" in content.lower()


class TestInitUsesConstraintSuggestions:
    """Tests that init command uses constraint suggestions from Claude."""

    def test_init_uses_suggested_yolo_mode(self, tmp_path: Path) -> None:
        """Init should use yolo mode when Claude suggests it."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n{{tasks}}\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text(
                "{{goal}}{{existing_tasks}}"
            )
            # Add README.md so goal is inferred
            Path("README.md").write_text("# Test Project\n\nA test project.")

            # Mock Claude to return yolo constraint suggestion
            claude_output = """```markdown
## Goal

Test project

## Tasks

- [ ] First task

## Constraints

security_mode: yolo
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=claude_output
            ):
                # Accept suggestions (y), confirm yolo mode (y)
                result = runner.invoke(app, ["init"], input="y\ny\n")

            config_file = Path(".ralph-loop.toml")
            assert config_file.exists(), f"Config not created. Output: {result.output}"
            content = config_file.read_text()
            assert "yolo = true" in content

    def test_init_uses_suggested_path_restricted_mode(self, tmp_path: Path) -> None:
        """Init should use path-restricted mode when Claude suggests it."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n{{tasks}}\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text(
                "{{goal}}{{existing_tasks}}"
            )
            # Add README.md so goal is inferred
            Path("README.md").write_text("# API Project\n\nA REST API.")

            claude_output = """```markdown
## Goal

API project

## Tasks

- [ ] Build API

## Constraints

security_mode: path_restricted
allow_paths: src/,tests/
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=claude_output
            ):
                # Accept suggestions (y)
                result = runner.invoke(app, ["init"], input="y\n")

            config_file = Path(".ralph-loop.toml")
            assert config_file.exists(), f"Config not created. Output: {result.output}"
            content = config_file.read_text()
            assert "src/" in content
            assert "tests/" in content

    def test_init_uses_suggested_conservative_mode(self, tmp_path: Path) -> None:
        """Init should use conservative mode when Claude suggests it."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n{{tasks}}\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text(
                "{{goal}}{{existing_tasks}}"
            )
            # Add README.md so goal is inferred
            Path("README.md").write_text("# Sensitive Project\n\nHandles credentials.")

            claude_output = """```markdown
## Goal

Sensitive project

## Tasks

- [ ] Handle credentials

## Constraints

security_mode: conservative
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=claude_output
            ):
                # Accept suggestions (y)
                result = runner.invoke(app, ["init"], input="y\n")

            config_file = Path(".ralph-loop.toml")
            assert config_file.exists(), f"Config not created. Output: {result.output}"
            content = config_file.read_text()
            assert "yolo = false" in content
            assert 'allow_paths = ""' in content

    def test_init_shows_suggested_constraints(self, tmp_path: Path) -> None:
        """Init should display the suggested security constraints."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n{{tasks}}\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text(
                "{{goal}}{{existing_tasks}}"
            )
            # Add README.md so goal is inferred
            Path("README.md").write_text("# Test Project\n\nA test.")

            claude_output = """```markdown
## Goal

Test

## Tasks

- [ ] Task

## Constraints

security_mode: yolo
internet_access: true
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=claude_output
            ):
                result = runner.invoke(app, ["init"], input="y\ny\n")

            # Should show security mode in suggestions
            assert (
                "yolo" in result.output.lower() or "security" in result.output.lower()
            )

    def test_init_falls_back_to_manual_when_no_constraints(
        self, tmp_path: Path
    ) -> None:
        """Init falls back to manual security selection if no constraints suggested."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("templates").mkdir()
            (Path("templates") / "LOOP-PROMPT.md").write_text(
                "## Goal\n\n{{goal}}\n\n{{tasks}}\n"
            )
            (Path("templates") / "TASKS.md").write_text(
                "# Tasks\n\n## Todo\n\n{{tasks}}\n"
            )
            (Path("templates") / "META-PROMPT.md").write_text(
                "{{goal}}{{existing_tasks}}"
            )
            # Add README.md so goal is inferred
            Path("README.md").write_text("# Simple Project\n\nA simple project.")

            # Claude output without constraints section
            claude_output = """```markdown
## Goal

Simple project

## Tasks

- [ ] Build it
```"""
            with patch(
                "wiggum.cli.run_claude_for_planning", return_value=claude_output
            ):
                # Accept suggestions for tasks (y), then manually choose conservative (1)
                result = runner.invoke(app, ["init"], input="y\n1\n")

            # Should still have created config with manual selection
            config_file = Path(".ralph-loop.toml")
            assert config_file.exists()
