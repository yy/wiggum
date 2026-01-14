You are helping set up a ralph-loop (an agent loop that iterates on tasks until done).

## User's Goal

{{goal}}

## Your Task

Analyze this codebase and break down the user's goal into concrete, actionable tasks.

## Output Format

Output ONLY a TOML block with suggested configuration. No other text.

```toml
[project]
goal = "one line summary of the goal"
doc_files = "README.md, CLAUDE.md"

[[tasks]]
description = "First task description"
priority = 1

[[tasks]]
description = "Second task description"
priority = 2
```

## Guidelines

- Break the goal into 3-7 concrete tasks
- Each task should be completable in one agent session
- Order by priority (1 = highest)
- Tasks should be testable (have clear done criteria)
- Consider what already exists in the codebase
- Don't include vague tasks like "improve code quality"
