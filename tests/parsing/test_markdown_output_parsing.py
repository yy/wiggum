"""Tests for parsing markdown output from Claude during init.

This tests that the init command correctly parses markdown output
from Claude instead of TOML format.
"""

from wiggum.cli import parse_markdown_from_output


class TestParseMarkdownFromOutput:
    """Tests for parse_markdown_from_output function."""

    def test_parses_goal_from_markdown_block(self) -> None:
        """Should extract goal from ## Goal section."""
        output = """Here's my analysis:

```markdown
## Goal

Build a REST API for user management

## Tasks

- [ ] Set up project structure
- [ ] Implement user endpoints
```
"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["goal"] == "Build a REST API for user management"

    def test_parses_tasks_from_markdown_block(self) -> None:
        """Should extract tasks from ## Tasks section."""
        output = """```markdown
## Goal

Build a CLI tool

## Tasks

- [ ] Set up project structure
- [ ] Implement login
- [ ] Add tests
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert len(result["tasks"]) == 3
        assert result["tasks"][0] == "Set up project structure"
        assert result["tasks"][1] == "Implement login"
        assert result["tasks"][2] == "Add tests"

    def test_returns_none_for_no_markdown_block(self) -> None:
        """Should return None when no markdown block is found."""
        output = "I couldn't analyze the codebase properly."
        result = parse_markdown_from_output(output)
        assert result is None

    def test_returns_none_for_empty_markdown_block(self) -> None:
        """Should return None for empty markdown block."""
        output = """```markdown
```"""
        result = parse_markdown_from_output(output)
        assert result is None

    def test_handles_multiline_goal(self) -> None:
        """Should handle single-line goal (ignore additional lines)."""
        output = """```markdown
## Goal

Build a comprehensive REST API

## Tasks

- [ ] First task
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["goal"] == "Build a comprehensive REST API"

    def test_handles_tasks_with_extra_whitespace(self) -> None:
        """Should handle tasks with extra whitespace."""
        output = """```markdown
## Goal

Test project

## Tasks

- [ ]   Set up project structure
- [ ]Implement login
- [ ] Add tests
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        # Should strip whitespace from tasks
        assert "Set up project structure" in result["tasks"]
        assert "Implement login" in result["tasks"]
        assert "Add tests" in result["tasks"]

    def test_returns_none_when_goal_missing(self) -> None:
        """Should return None when Goal section is missing."""
        output = """```markdown
## Tasks

- [ ] Task 1
```"""
        result = parse_markdown_from_output(output)
        assert result is None

    def test_returns_none_when_tasks_missing(self) -> None:
        """Should return None when Tasks section is missing."""
        output = """```markdown
## Goal

Build something
```"""
        result = parse_markdown_from_output(output)
        assert result is None

    def test_handles_text_before_and_after_markdown(self) -> None:
        """Should extract from markdown even with surrounding text."""
        output = """I've analyzed the codebase and here's what I suggest:

```markdown
## Goal

Build a testing framework

## Tasks

- [ ] Create test runner
- [ ] Add assertions library
```

These tasks should get you started!"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["goal"] == "Build a testing framework"
        assert len(result["tasks"]) == 2

    def test_ignores_checked_tasks(self) -> None:
        """Should only include unchecked tasks."""
        output = """```markdown
## Goal

Continue project

## Tasks

- [ ] New task
- [x] Already done
- [ ] Another new task
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert len(result["tasks"]) == 2
        assert "New task" in result["tasks"]
        assert "Another new task" in result["tasks"]
        assert "Already done" not in result["tasks"]

    def test_handles_lowercase_markdown_fence(self) -> None:
        """Should handle lowercase markdown in fence."""
        output = """```markdown
## Goal

Test goal

## Tasks

- [ ] Task 1
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["goal"] == "Test goal"
