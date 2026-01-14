# ralph-loop

A minimal, opinionated tool for running agent loops.

```bash
while true; do cat PROMPT.md | claude --print; done
```

This is the "Ralph Wiggum loop" - the simplest possible agent loop. ralph-loop adds just enough guardrails to make it practical.

## Philosophy

- **Simple** - prefer simplicity whenever possible
- **Minimal** - does one thing well: run a prompt in a loop until tasks are done
- **Opinionated** - sensible defaults, few options
- **Task-driven** - stops when TASKS.md has no unchecked items
- **Test-driven** - write tests first, implement after

## Quick Start

```bash
uv add ralph-loop

# Set up (Claude helps plan your tasks)
ralph-loop init

# Run the loop
ralph-loop run --yolo
```

## How It Works

1. `init` creates `LOOP-PROMPT.md` (workflow) and `TASKS.md` (task list)
2. `run` executes Claude with the prompt, checks TASKS.md after each iteration
3. Loop stops when all tasks are checked off (`- [x]`)

## Options

```bash
ralph-loop run                    # Run with defaults
ralph-loop run --yolo             # Skip permission prompts
ralph-loop run -n 5               # Max 5 iterations
ralph-loop run --continue         # Keep context between iterations
```

## License

MIT
