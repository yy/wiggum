# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

wiggum is a Python package for setting up and running "Ralph Wiggum loops" for Claude Code and similar AI agent tools. The package provides:

1. **Setup Assistant**: An interactive helper that guides users through configuring loop parameters including prompts, conditions, and security settings
2. **Loop Runner**: Executes loops with configurable parameters like iteration count (stops when all tasks in TASKS.md are complete)

## Development

This is a Python project. Use `uv` for package management:

```bash
# Install dependencies
uv sync

# Run the package
uv run python -m wiggum

# Run tests
uv run pytest

# Run a single test
uv run pytest tests/test_file.py::test_name -v

# Build (always remove old dist files first)
rm -rf dist && uv build

# Publish
uv publish --token <token>
```

## Documentation

See `docs/` for deeper reference material:
- `docs/architecture.md` — module map, data flow, key patterns
- `docs/design-decisions.md` — settled decisions with rationale (don't re-litigate)
- `docs/testing.md` — test organization, patterns, when to write tests

## Architecture

### CLI Commands
- `wiggum init`: Interactive setup that creates `LOOP-PROMPT.md`, `TASKS.md`, and `.wiggum.toml`. Claude analyzes the codebase and suggests both tasks and security constraints. If `TASKS.md` already exists, new tasks are merged (without duplicates) rather than overwriting.
- `wiggum run`: Executes the loop, reading prompt from file and iterating until all tasks in TASKS.md are complete (or max iterations reached). Use `--keep-running` to continue even when tasks are complete (agent can add new tasks). Use `--identify-tasks` to analyze the codebase and populate TASKS.md with refactoring/cleanup tasks without running the loop. Use `--git` to enable git workflow (fetch/merge main, create branch, create PR at end).
- `wiggum add`: Adds tasks to `TASKS.md`
- `wiggum list`: Lists all tasks from `TASKS.md` grouped by status (todo/done)
- `wiggum suggest`: Interactively discovers and suggests tasks using Claude's planning mode. Use `-y`/`--yes` to accept all suggestions without prompting.
- `wiggum spec <name>`: Creates a new spec file from template in `specs/` directory. Tasks can reference specs like: `- [ ] Implement feature (see specs/feature.md)`
- `wiggum changelog`: Generates CHANGELOG.md from completed tasks in TASKS.md. Categorizes tasks by prefix (Add→Added, Fix→Fixed, Update→Changed, Remove→Removed). Flags: `--version/-v` for version string, `--dry-run` to preview, `--append` to add to existing file, `--clear-done` to clear Done section after generating.
- `wiggum prune`: Removes completed tasks from TASKS.md. Flags: `--dry-run` to preview, `--force` to skip confirmation, `-f` for custom tasks file.

### Configuration
Settings are stored in `.wiggum.toml` and read by the `run` command:

**[security] section:**
- `yolo`: Skip all permission prompts
- `allow_paths`: Comma-separated paths to allow writing

**[loop] section:**
- `max_iterations`: Default number of loop iterations (default: 10)
- `agent`: Which agent to use (default: "claude"). Options: claude, codex, gemini

**[git] section:**
- `enabled`: Enable git workflow (default: false)
- `branch_prefix`: Prefix for auto-generated branch names (default: "wiggum")

**[learning] section:**
- `enabled`: Enable learning diary capture (default: true)
- `keep_diary`: Keep `.wiggum/session-diary.md` after consolidation (default: false)
- `auto_consolidate`: Auto-consolidate diary into CLAUDE.md at session end (default: true)

CLI flags override config file settings.

### Learning Diary Feature

The learning diary allows the agent to capture insights during loop sessions that get consolidated into CLAUDE.md for long-term memory.

**How it works:**
1. During the loop, the agent can write learnings to `.wiggum/session-diary.md`
2. After the loop completes, learnings are automatically consolidated into CLAUDE.md
3. The diary is kept or deleted based on the `keep_diary` setting

**CLI flags:**
- `--diary` / `--no-diary`: Enable/disable learning diary for this run
- `--no-consolidate`: Skip consolidation after run (diary is preserved)
- `--keep-diary` / `--no-keep-diary`: Override whether to keep diary after consolidation

**Diary entry format:**
```markdown
### Learning: [short title]
**Context**: What situation triggered this
**Insight**: The actual learning
**Recommendation**: What to do in the future
```

### Agent Abstraction Layer
The `agents` module provides a pluggable architecture for different coding agents:

- `Agent`: Protocol (interface) that all agents must implement
- `AgentConfig`: Dataclass for passing configuration (prompt, yolo, allow_paths, continue_session)
- `AgentResult`: Dataclass for agent output (stdout, stderr, return_code)
- `get_agent(name)`: Get an agent by name (default: "claude")
- `get_available_agents()`: List registered agents

Agent implementations live in separate files (e.g., `agents_claude.py`, `agents_codex.py`).

**Available agents:**
- `claude`: Claude Code CLI (default)
- `codex`: OpenAI Codex CLI
- `gemini`: Google Gemini CLI
