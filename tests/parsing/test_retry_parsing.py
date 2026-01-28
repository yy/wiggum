"""Tests for retry logic when Claude returns unparseable markdown."""

from unittest.mock import patch


from wiggum.runner import run_claude_with_retry


class TestRunClaudeWithRetry:
    """Tests for run_claude_with_retry function."""

    def test_success_on_first_try(self) -> None:
        """Should return parsed result on first successful attempt."""
        valid_output = """```markdown
## Tasks

- [ ] Task 1
- [ ] Task 2
```"""
        with patch(
            "wiggum.runner.run_claude_for_planning", return_value=(valid_output, None)
        ):
            result, error = run_claude_with_retry("test prompt")

        assert error is None
        assert result is not None
        assert result["tasks"] == ["Task 1", "Task 2"]

    def test_retries_on_unparseable_output(self) -> None:
        """Should retry when output cannot be parsed."""
        invalid_output = "I couldn't understand the codebase"
        valid_output = """```markdown
## Tasks

- [ ] Task 1
```"""
        with patch(
            "wiggum.runner.run_claude_for_planning",
            side_effect=[
                (invalid_output, None),  # First try - unparseable
                (valid_output, None),  # Second try - valid
            ],
        ) as mock_run:
            result, error = run_claude_with_retry("test prompt")

        assert error is None
        assert result is not None
        assert result["tasks"] == ["Task 1"]
        assert mock_run.call_count == 2

    def test_retry_prompt_includes_format_hint(self) -> None:
        """Should include format hint in retry prompt."""
        invalid_output = "I couldn't understand the codebase"
        valid_output = """```markdown
## Tasks

- [ ] Task 1
```"""
        captured_prompts = []

        def capture_prompt(prompt):
            captured_prompts.append(prompt)
            if len(captured_prompts) == 1:
                return (invalid_output, None)
            return (valid_output, None)

        with patch("wiggum.runner.run_claude_for_planning", side_effect=capture_prompt):
            run_claude_with_retry("test prompt")

        assert len(captured_prompts) == 2
        # Second prompt should contain retry hint
        assert "```markdown" in captured_prompts[1]
        assert "## Tasks" in captured_prompts[1]
        assert "- [ ]" in captured_prompts[1]

    def test_gives_up_after_max_retries(self) -> None:
        """Should return error after max retries exceeded."""
        invalid_output = "I couldn't understand the codebase"

        with patch(
            "wiggum.runner.run_claude_for_planning",
            return_value=(invalid_output, None),
        ) as mock_run:
            result, error = run_claude_with_retry("test prompt", max_retries=3)

        assert result is None
        assert error is not None
        assert "Could not parse" in error
        assert mock_run.call_count == 3

    def test_returns_error_if_claude_fails(self) -> None:
        """Should return error immediately if Claude returns an error."""
        with patch(
            "wiggum.runner.run_claude_for_planning",
            return_value=(None, "Claude CLI not found"),
        ):
            result, error = run_claude_with_retry("test prompt")

        assert result is None
        assert error == "Claude CLI not found"

    def test_returns_error_if_claude_returns_no_output(self) -> None:
        """Should return error immediately if Claude returns empty output."""
        with patch(
            "wiggum.runner.run_claude_for_planning",
            return_value=(None, None),
        ):
            result, error = run_claude_with_retry("test prompt")

        assert result is None
        assert error is not None
        assert "no output" in error.lower()

    def test_default_max_retries_is_three(self) -> None:
        """Should default to 3 retries."""
        invalid_output = "I couldn't understand the codebase"

        with patch(
            "wiggum.runner.run_claude_for_planning",
            return_value=(invalid_output, None),
        ) as mock_run:
            run_claude_with_retry("test prompt")

        assert mock_run.call_count == 3

    def test_custom_max_retries(self) -> None:
        """Should respect custom max_retries parameter."""
        invalid_output = "I couldn't understand the codebase"

        with patch(
            "wiggum.runner.run_claude_for_planning",
            return_value=(invalid_output, None),
        ) as mock_run:
            run_claude_with_retry("test prompt", max_retries=5)

        assert mock_run.call_count == 5

    def test_includes_original_output_in_retry(self) -> None:
        """Should include Claude's previous response in retry prompt."""
        invalid_output = "Here are some ideas but not in markdown"
        valid_output = """```markdown
## Tasks

- [ ] Task 1
```"""
        captured_prompts = []

        def capture_prompt(prompt):
            captured_prompts.append(prompt)
            if len(captured_prompts) == 1:
                return (invalid_output, None)
            return (valid_output, None)

        with patch("wiggum.runner.run_claude_for_planning", side_effect=capture_prompt):
            run_claude_with_retry("test prompt")

        # Second prompt should reference the previous output
        assert "Here are some ideas but not in markdown" in captured_prompts[1]

    def test_preserves_constraints_on_success(self) -> None:
        """Should include constraints in successful parse result."""
        valid_output = """```markdown
## Tasks

- [ ] Task 1

## Constraints

security_mode: yolo
allow_paths: src/
```"""
        with patch(
            "wiggum.runner.run_claude_for_planning", return_value=(valid_output, None)
        ):
            result, error = run_claude_with_retry("test prompt")

        assert error is None
        assert result is not None
        assert result["constraints"]["security_mode"] == "yolo"
        assert result["constraints"]["allow_paths"] == "src/"
