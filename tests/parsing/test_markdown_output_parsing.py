"""Tests for parsing markdown output from Claude during init."""

from wiggum.parsing import parse_markdown_from_output


class TestParseMarkdownFromOutput:
    """Tests for parse_markdown_from_output function."""

    def test_parses_tasks_from_markdown_block(self) -> None:
        """Should extract tasks from ## Tasks section."""
        output = """```markdown
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

    def test_handles_tasks_with_extra_whitespace(self) -> None:
        """Should handle tasks with extra whitespace."""
        output = """```markdown
## Tasks

- [ ]   Set up project structure
- [ ]Implement login
- [ ] Add tests
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert "Set up project structure" in result["tasks"]
        assert "Implement login" in result["tasks"]
        assert "Add tests" in result["tasks"]

    def test_returns_none_when_tasks_missing(self) -> None:
        """Should return None when Tasks section is missing."""
        output = """```markdown
## Constraints

security_mode: conservative
```"""
        result = parse_markdown_from_output(output)
        assert result is None

    def test_handles_text_before_and_after_markdown(self) -> None:
        """Should extract from markdown even with surrounding text."""
        output = """I've analyzed the codebase and here's what I suggest:

```markdown
## Tasks

- [ ] Create test runner
- [ ] Add assertions library
```

These tasks should get you started!"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert len(result["tasks"]) == 2

    def test_ignores_checked_tasks(self) -> None:
        """Should only include unchecked tasks."""
        output = """```markdown
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

    def test_parses_constraints(self) -> None:
        """Should extract constraints from ## Constraints section."""
        output = """```markdown
## Tasks

- [ ] Task 1

## Constraints

security_mode: path_restricted
allow_paths: src/,tests/
internet_access: true
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["constraints"]["security_mode"] == "path_restricted"
        assert result["constraints"]["allow_paths"] == "src/,tests/"
        assert result["constraints"]["internet_access"] is True

    def test_handles_missing_constraints(self) -> None:
        """Should return empty constraints dict when section is missing."""
        output = """```markdown
## Tasks

- [ ] Task 1
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["constraints"] == {}
