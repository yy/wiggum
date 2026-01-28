# Clean Command

## Overview

Add a `wiggum clean` command that removes wiggum-managed files from the current directory, useful for starting fresh or removing wiggum from a project.

## Files Managed by Wiggum

| File | Default Behavior |
|------|------------------|
| `LOOP-PROMPT.md` | Remove |
| `.wiggum.toml` | Remove |
| `TASKS.md` | Keep (ask user) |

## Behavior

### Basic usage:

```
wiggum clean
```

```
$ wiggum clean
This will remove wiggum configuration files:
  - LOOP-PROMPT.md
  - .wiggum.toml

TASKS.md contains your task list. Remove it too? [y/N] n

Remove these files? [y/N] y
✓ Removed LOOP-PROMPT.md
✓ Removed .wiggum.toml
  Kept TASKS.md
```

### Flags:

| Flag | Behavior |
|------|----------|
| `--all` | Also remove TASKS.md without prompting |
| `--keep-tasks` | Explicitly keep TASKS.md (no prompt) |
| `--force` / `-f` | Skip confirmation prompts |
| `--dry-run` | Show what would be removed without deleting |

### Examples:

```bash
# Interactive (default)
wiggum clean

# Remove everything including tasks
wiggum clean --all

# Remove config only, keep tasks (no prompt)
wiggum clean --keep-tasks

# Non-interactive removal of config files
wiggum clean --keep-tasks --force

# Preview what would be removed
wiggum clean --dry-run
```

## Output Examples

### Nothing to clean:

```
$ wiggum clean
No wiggum files found in current directory.
```

### Partial files exist:

```
$ wiggum clean
This will remove wiggum configuration files:
  - .wiggum.toml

LOOP-PROMPT.md not found (already removed or never created)
TASKS.md not found

Remove these files? [y/N] y
✓ Removed .wiggum.toml
```

### Dry run:

```
$ wiggum clean --dry-run
Would remove:
  - LOOP-PROMPT.md
  - .wiggum.toml
Would keep:
  - TASKS.md (use --all to remove)
```

### Force mode:

```
$ wiggum clean --force
✓ Removed LOOP-PROMPT.md
✓ Removed .wiggum.toml
  Kept TASKS.md (use --all to include)
```

## Edge Cases

1. **No files exist**: Print message and exit cleanly
2. **Permission denied**: Show error for each file that fails
3. **Running in wrong directory**: Warn if no wiggum files found
4. **Backup files exist** (`.bak`): Don't remove them (user's responsibility)

## Implementation

### Files to modify:

- `src/wiggum/cli.py` - Add `clean` command

### Logic:

```python
MANAGED_FILES = ["LOOP-PROMPT.md", ".wiggum.toml"]
TASK_FILE = "TASKS.md"

def clean(all: bool, keep_tasks: bool, force: bool, dry_run: bool):
    files_to_remove = [f for f in MANAGED_FILES if Path(f).exists()]

    # Handle TASKS.md
    if Path(TASK_FILE).exists() and not keep_tasks:
        if all:
            files_to_remove.append(TASK_FILE)
        elif not force:
            # Prompt user about TASKS.md
            ...

    # Confirm and remove
    ...
```

## Out of Scope

- Removing `specs/` directory (user content)
- Removing backup files (`.bak`)
- Recursive cleaning in subdirectories
- Git-related cleanup (branches, stashes)
