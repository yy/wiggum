# ralph-loop

A Ralph Wiggum loop is the simplest possible agent loop:

```bash
while true; do cat PROMPT.md | claude --print; done
```

This package helps you set up and run these loops with proper guardrails.

## Why ralph-loop?

The raw loop above works, but you probably want:

- **Iteration limits** - stop after N runs
- **Task-based stopping** - exit when all tasks in TASKS.md are checked off
- **Session management** - continue or reset context between runs
- **Security settings** - control what the agent can do
- **Logging** - track what happened across iterations

ralph-loop provides an interactive setup assistant to configure these parameters, and a loop runner to execute with your settings.

## Installation

```bash
uv add ralph-loop
```

## Usage

```bash
# Interactive setup - creates a loop configuration
ralph-loop init

# Run a configured loop
ralph-loop run

# Add a task to TASKS.md
ralph-loop add "Implement feature X"

# Run with overrides
ralph-loop run --max-iterations 10 -f custom-prompt.md

# Use a custom tasks file (default: TASKS.md)
ralph-loop run --tasks CUSTOM_TASKS.md

# Maintain conversation context between iterations
ralph-loop run --continue

# Start fresh each iteration (default)
ralph-loop run --reset

# Log output to a file
ralph-loop run --log-file loop.log

# Show file changes after each iteration (verbose mode)
ralph-loop run -v
ralph-loop run --verbose
ralph-loop run --show-progress  # legacy alias
```

## Configuration

`ralph-loop init` asks about security settings and stores them in `.ralph-loop.toml`:

```toml
[security]
yolo = false
allow_paths = "src/,tests/"
```

Security modes:
- **Conservative** (default): Claude asks permission for each action
- **Path-restricted**: Allows writes to specific paths only
- **YOLO mode**: Skips all permission prompts (dangerous!)

CLI flags (`--yolo`, `--allow-paths`) override the config file settings.

## License

MIT
