# Testing Guide

## Running tests

```bash
uv run pytest                                   # All tests
uv run pytest tests/test_file.py::test_name -v  # Single test
uv run pytest tests/init/ -v                    # Test directory
uv run pytest -k "test_pattern" -v              # Pattern match
```

## Test organization

Tests are organized by feature, mirroring the module structure:

```
tests/
├── agents/           # Agent protocol, registry, individual agents
├── config/           # Config loading, validation, schema
├── init/             # Init command (security, tasks, metaprompt)
├── parsing/          # Markdown output parsing, fallback chains
├── run/              # Run command (stop conditions, progress, sessions)
├── test_add_command.py
├── test_changelog_command.py
├── test_clean_command.py
├── test_git.py
├── test_git_workflow.py
├── test_learning.py
├── test_list_command.py
├── test_prune_command.py
├── test_suggest_command.py
└── test_upgrade_command.py
```

## Testing patterns

### CLI testing with typer

All CLI commands are tested through `typer.testing.CliRunner`:

```python
from typer.testing import CliRunner
from wiggum.cli import app

runner = CliRunner()

def test_something(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Set up files...
        result = runner.invoke(app, ["command", "--flag"])
        assert result.exit_code == 0
        assert "expected output" in result.output
```

Use `runner.isolated_filesystem()` to avoid touching real files.

### Mocking subprocess calls

Agent calls and Claude planning calls use `subprocess.run`. Mock them to avoid real CLI invocations:

```python
from unittest.mock import patch

# Mock the planning function (used by init, suggest, identify-tasks)
with patch("wiggum.runner.run_claude_for_planning", return_value=("output", None)):
    result = runner.invoke(app, ["init"])

# Mock an agent's subprocess call
with patch("subprocess.run") as mock_run:
    mock_run.return_value = Mock(stdout="output", stderr="", returncode=0)
    result = runner.invoke(app, ["run", "-n", "1"])
```

### File-based tests

Many tests create temporary TASKS.md or .wiggum.toml files:

```python
def test_tasks(tmp_path):
    tasks_file = tmp_path / "TASKS.md"
    tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] Do something\n")

    assert tasks_remaining(tasks_file) is True
    assert get_current_task(tasks_file) == "Do something"
```

### Parsing tests

Parsing tests verify the progressive fallback chain by providing output in various formats:

```python
def test_parses_markdown_fence():
    output = '```markdown\n## Tasks\n- [ ] Task 1\n```'
    result = parse_markdown_from_output(output)
    assert result["tasks"] == ["Task 1"]

def test_parses_unfenced():
    output = 'Here are some tasks:\n## Tasks\n- [ ] Task 1'
    result = parse_markdown_from_output(output)
    assert result["tasks"] == ["Task 1"]
```

## When to write tests

Write tests for:
- New behavior or logic
- Bug fixes (test the fix)
- API changes
- Parsing edge cases

Do NOT write tests for:
- String/label changes
- Renames
- Config value changes
- Anything where the "test" would just assert a string is present

Rule of thumb: if you can't describe what behavior would regress without the test, skip it.
