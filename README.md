# wiggum

A minimal, opinionated tool for running agent loops.

```bash
while true; do cat PROMPT.md | claude --print; done
```

This is the "Ralph Wiggum loop" - the simplest possible agent loop. wiggum adds just enough guardrails to make it practical.

## Philosophy

- **Simple** - prefer simplicity whenever possible
- **Minimal** - does one thing well: run a prompt in a loop until tasks are done
- **Opinionated** - sensible defaults, few options
- **Unobtrusive** - infer what you can, don't ask obvious questions
- **Task-driven** - stops when TASKS.md has no unchecked items
- **Test-driven** - write tests first, implement after

## Installation

```bash
# Run directly (no install needed)
uvx wiggum init

# Or install globally
uv tool install wiggum

# Upgrade to latest version
uv tool upgrade wiggum
```

## Quick Start

```bash
# Set up (Claude helps plan your tasks)
wiggum init

# Run the loop
wiggum run
```

## How It Works

1. `init` creates `LOOP-PROMPT.md` (workflow) and `TASKS.md` (task list)
2. `run` executes Claude with the prompt, checks TASKS.md after each iteration
3. Loop stops when all tasks are checked off (`- [x]`)

## Options

```bash
wiggum run                    # Run (skips permission prompts by default)
wiggum run --no-yolo          # Ask for permissions
wiggum run -n 5               # Max 5 iterations
wiggum run --continue         # Keep context between iterations
wiggum run --keep-running     # Continue even when tasks complete (agent can add new tasks)
wiggum run --identify-tasks   # Analyze codebase and add refactoring tasks to TASKS.md
wiggum run --agent codex      # Use a different agent (codex, gemini, etc.)
```

## License

MIT
