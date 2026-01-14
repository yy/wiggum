# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ralph-loop is a Python package for setting up and running "Ralph Wiggum loops" for Claude Code and similar AI agent tools. The package provides:

1. **Setup Assistant**: An interactive helper that guides users through configuring loop parameters including prompts, conditions, and security settings
2. **Loop Runner**: Executes loops with configurable parameters like iteration count (stops when all tasks in TASKS.md are complete)

## Development

This is a Python project. Use `uv` for package management:

```bash
# Install dependencies
uv sync

# Run the package
uv run python -m ralph_loop

# Run tests
uv run pytest

# Run a single test
uv run pytest tests/test_file.py::test_name -v
```

## Architecture

### CLI Commands
- `ralph-loop init`: Interactive setup that creates `LOOP-PROMPT.md`, `TASKS.md`, and `.ralph-loop.toml`
- `ralph-loop run`: Executes the loop, reading prompt from file and iterating until all tasks in TASKS.md are complete (or max iterations reached)
- `ralph-loop add`: Adds tasks to `TASKS.md`

### Configuration
Security settings are stored in `.ralph-loop.toml` and read by the `run` command:
- `yolo`: Skip all permission prompts
- `allow_paths`: Comma-separated paths to allow writing

CLI flags (`--yolo`, `--allow-paths`) override config file settings.
