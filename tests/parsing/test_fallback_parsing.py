"""Tests for fallback parsing scenarios."""

from wiggum.parsing import parse_markdown_from_output


class TestFencedFallbacks:
    """Tests for non-markdown fence types."""

    def test_plain_backtick_fences(self) -> None:
        """Should parse tasks from plain ``` fences."""
        output = """Here are the tasks:

```
## Tasks

- [ ] Set up CI pipeline
- [ ] Add linting
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == ["Set up CI pipeline", "Add linting"]

    def test_text_fences(self) -> None:
        """Should parse tasks from ```text fences."""
        output = """```text
## Tasks

- [ ] Write documentation
- [ ] Add examples
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == ["Write documentation", "Add examples"]

    def test_md_fences(self) -> None:
        """Should parse tasks from ```md fences."""
        output = """```md
## Tasks

- [ ] Refactor module
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == ["Refactor module"]

    def test_markdown_fence_preferred_over_other_fences(self) -> None:
        """Should prefer ```markdown fences when both exist."""
        output = """```text
## Tasks

- [ ] Wrong task
```

```markdown
## Tasks

- [ ] Correct task
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == ["Correct task"]


class TestUnfencedContent:
    """Tests for content without code fences."""

    def test_unfenced_with_tasks_heading(self) -> None:
        """Should parse unfenced output with ## Tasks heading."""
        output = """## Tasks

- [ ] Implement auth
- [ ] Add rate limiting
"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == ["Implement auth", "Add rate limiting"]

    def test_prose_before_heading_ignored(self) -> None:
        """Should ignore prose before the first structural line."""
        output = """I've analyzed the codebase and here are my suggestions:

## Tasks

- [ ] Fix broken tests
- [ ] Update dependencies
"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == ["Fix broken tests", "Update dependencies"]

    def test_pure_prose_returns_none(self) -> None:
        """Should return None for pure prose with no structure."""
        output = "I analyzed the codebase but couldn't determine specific tasks."
        result = parse_markdown_from_output(output)
        assert result is None


class TestHeadingLevels:
    """Tests for different heading levels."""

    def test_h1_tasks_heading(self) -> None:
        """Should match # Tasks heading."""
        output = """# Tasks

- [ ] Task from h1
"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == ["Task from h1"]

    def test_h3_tasks_heading(self) -> None:
        """Should match ### Tasks heading."""
        output = """### Tasks

- [ ] Task from h3
"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == ["Task from h3"]

    def test_h3_tasks_heading_in_fences(self) -> None:
        """Should match ### Tasks heading inside fences."""
        output = """```markdown
### Tasks

- [ ] Fenced h3 task
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == ["Fenced h3 task"]


class TestPlainListItems:
    """Tests for plain list items without checkboxes."""

    def test_plain_list_under_tasks_heading(self) -> None:
        """Should extract plain list items when no checkboxes present."""
        output = """## Tasks

- Implement user auth
- Add unit tests
- Deploy to staging
"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == [
            "Implement user auth",
            "Add unit tests",
            "Deploy to staging",
        ]

    def test_checkboxes_preferred_over_plain_list(self) -> None:
        """Should prefer checkboxes when mixed with plain items."""
        output = """## Tasks

- [ ] Checkbox task
- Plain task
"""
        result = parse_markdown_from_output(output)
        assert result is not None
        # Checkbox mode detected, plain items are ignored
        assert result["tasks"] == ["Checkbox task"]

    def test_plain_list_in_fences(self) -> None:
        """Should extract plain list items from fenced content."""
        output = """```markdown
## Tasks

- Fix the login bug
- Update the README
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == ["Fix the login bug", "Update the README"]


class TestNumberedListItems:
    """Tests for numbered list items."""

    def test_numbered_list_under_tasks_heading(self) -> None:
        """Should extract numbered list items."""
        output = """## Tasks

1. Set up database
2. Create API endpoints
3. Write integration tests
"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == [
            "Set up database",
            "Create API endpoints",
            "Write integration tests",
        ]

    def test_plain_list_preferred_over_numbered(self) -> None:
        """Should prefer plain list items over numbered when both exist."""
        output = """## Tasks

- Plain task one
- Plain task two
1. Numbered task
"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == ["Plain task one", "Plain task two"]


class TestBareListNoHeading:
    """Tests for bare lists without any heading."""

    def test_bare_checkbox_list(self) -> None:
        """Should extract tasks from bare checkbox list without heading."""
        output = """- [ ] First task
- [ ] Second task
- [ ] Third task
"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == ["First task", "Second task", "Third task"]

    def test_bare_plain_list(self) -> None:
        """Should extract tasks from bare plain list without heading."""
        output = """- Refactor auth module
- Add error handling
"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == ["Refactor auth module", "Add error handling"]

    def test_bare_numbered_list(self) -> None:
        """Should extract tasks from bare numbered list without heading."""
        output = """1. First thing
2. Second thing
"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == ["First thing", "Second thing"]


class TestConstraintsFallback:
    """Tests for flexible constraints heading."""

    def test_h3_constraints_heading(self) -> None:
        """Should match ### Constraints heading."""
        output = """### Tasks

- [ ] Task 1

### Constraints

security_mode: yolo
allow_paths: src/
"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["constraints"]["security_mode"] == "yolo"
        assert result["constraints"]["allow_paths"] == "src/"

    def test_h1_constraints_heading(self) -> None:
        """Should match # Constraints heading."""
        output = """# Tasks

- [ ] Task 1

# Constraints

internet_access: true
"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["constraints"]["internet_access"] is True

    def test_constraints_in_fenced_h3(self) -> None:
        """Should extract constraints from ### heading in fences."""
        output = """```
### Tasks

- [ ] Task 1

### Constraints

security_mode: conservative
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["constraints"]["security_mode"] == "conservative"

    def test_no_constraints_returns_empty_dict(self) -> None:
        """Should return empty constraints when section missing."""
        output = """## Tasks

- [ ] Task 1
"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["constraints"] == {}


class TestStrictFormatPreferred:
    """Verify strict format is still preferred when available."""

    def test_strict_format_still_works(self) -> None:
        """The original strict format should work identically."""
        output = """```markdown
## Tasks

- [ ] Set up project structure
- [ ] Implement login
- [ ] Add tests

## Constraints

security_mode: path_restricted
allow_paths: src/,tests/
internet_access: true
```"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert result["tasks"] == [
            "Set up project structure",
            "Implement login",
            "Add tests",
        ]
        assert result["constraints"]["security_mode"] == "path_restricted"
        assert result["constraints"]["allow_paths"] == "src/,tests/"
        assert result["constraints"]["internet_access"] is True

    def test_strict_format_with_surrounding_text(self) -> None:
        """Strict format should work with surrounding prose."""
        output = """Here's my analysis:

```markdown
## Tasks

- [ ] Create test runner
- [ ] Add assertions library

## Constraints

security_mode: conservative
```

These tasks should get you started!"""
        result = parse_markdown_from_output(output)
        assert result is not None
        assert len(result["tasks"]) == 2
        assert result["constraints"]["security_mode"] == "conservative"
