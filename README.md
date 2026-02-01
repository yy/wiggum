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
- **Test-driven** - write tests first for new behavior; skip tests for trivial changes (renames, constants, config)

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

## Commands

### init

Initialize a new loop with `LOOP-PROMPT.md`, `TASKS.md`, and `.wiggum.toml`.

```bash
wiggum init           # Interactive setup with Claude
wiggum init --force   # Overwrite existing files
```

### run

Execute the agent loop until all tasks are complete.

```bash
wiggum run                    # Run with defaults
wiggum run -n 5               # Max 5 iterations
wiggum run --continue         # Keep context between iterations
wiggum run --keep-running     # Continue when tasks complete (agent can add new)
wiggum run --identify-tasks   # Analyze codebase, populate TASKS.md, then exit
wiggum run --no-yolo          # Ask for permissions
wiggum run -v                 # Show git status after each iteration
```

### add

Add tasks directly from the command line.

```bash
wiggum add "Fix the login bug"
wiggum add "Refactor auth module" -f my-tasks.md
```

### list

Show all tasks grouped by status.

```bash
wiggum list
```

### suggest

Use Claude to discover and suggest tasks interactively.

```bash
wiggum suggest       # Interactive prompts
wiggum suggest -y    # Accept all suggestions
```

### spec

Create detailed spec files for complex features.

```bash
wiggum spec user-auth    # Creates specs/user-auth.md
```

Tasks can reference specs: `- [ ] Implement auth (see specs/user-auth.md)`

### upgrade

Upgrade wiggum-managed files to the latest template versions.

```bash
wiggum upgrade            # Upgrade all files
wiggum upgrade prompt     # Only LOOP-PROMPT.md
wiggum upgrade config     # Only .wiggum.toml
wiggum upgrade --dry-run  # Preview changes
```

### clean

Remove wiggum-managed files.

```bash
wiggum clean              # Interactive removal
wiggum clean --keep-tasks # Remove config, keep TASKS.md
wiggum clean --all        # Remove everything
```

## Configuration

Settings are stored in `.wiggum.toml`:

```toml
[security]
yolo = true           # Skip permission prompts (default: true)
allow_paths = ""      # Comma-separated paths to allow writing

[loop]
max_iterations = 10   # Default iteration limit

[git]
enabled = false       # Enable git workflow
branch_prefix = "wiggum"  # Prefix for auto-generated branches
```

CLI flags override config file settings.

## Git Workflow

Create branches and PRs automatically:

```bash
wiggum run --pr           # Create branch, run loop, open PR when done
wiggum run --pr --no-branch  # Use current branch, still create PR
```

The `--pr` flag:
1. Fetches and merges from main
2. Creates a new branch (e.g., `wiggum/fix-auth-bug`)
3. Runs the loop
4. Opens a PR when complete

## Multi-Agent Support

wiggum supports multiple coding agents:

```bash
wiggum run --agent claude   # Claude Code (default)
wiggum run --agent codex    # OpenAI Codex CLI
wiggum run --agent gemini   # Google Gemini CLI
```

## Learning Diary

wiggum automatically captures learnings during each session in `.wiggum/session-diary.md`. After the loop completes, it consolidates these into your `CLAUDE.md` for future sessions.

```bash
wiggum run --no-diary        # Disable diary for this run
wiggum run --no-consolidate  # Skip consolidation after run
```

## License

MIT
