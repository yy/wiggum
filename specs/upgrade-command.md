# Upgrade Command

## Overview

Add a `wiggum upgrade` command that updates wiggum-managed files to the latest version without requiring users to delete files and re-run `wiggum init`.

## Files Managed by Wiggum

| File | Upgrade Behavior |
|------|------------------|
| `LOOP-PROMPT.md` | Replace with latest template (backup old) |
| `.wiggum.toml` | Merge new config options (preserve existing values) |
| `TASKS.md` | Add missing sections only (preserve user tasks) |

## Behavior

### Basic usage:

```
wiggum upgrade
```

Checks all managed files and shows what would be updated:

```
$ wiggum upgrade
Checking wiggum files...

LOOP-PROMPT.md: v0.4.1 → v0.5.0
  - Added "Using Subagents" section
  - Restructured workflow into 6 phases
  - Added verification and clean code principles

.wiggum.toml: 2 new options available
  - [loop] agent = "claude" (default)
  - [git] branch_prefix = "wiggum" (default)

TASKS.md: up to date

Upgrade? [y/N] y
✓ Backed up LOOP-PROMPT.md → LOOP-PROMPT.md.bak
✓ LOOP-PROMPT.md upgraded to v0.5.0
✓ .wiggum.toml updated with new options
```

### Selective upgrade:

```
wiggum upgrade prompt      # Only upgrade LOOP-PROMPT.md
wiggum upgrade config      # Only upgrade .wiggum.toml
wiggum upgrade tasks       # Only upgrade TASKS.md structure
wiggum upgrade --all       # Upgrade all (default)
```

### Flags:

| Flag | Behavior |
|------|----------|
| `--diff` | Show diff of changes without applying |
| `--force` / `-f` | Skip confirmation prompt |
| `--no-backup` | Don't create .bak file for LOOP-PROMPT.md |
| `--dry-run` | Show what would change without modifying files |

## File-Specific Upgrade Logic

### LOOP-PROMPT.md

1. Check for version tag: `<!-- wiggum-template: X.Y.Z -->`
2. Compare with bundled template version
3. If outdated or no version tag:
   - Backup to `LOOP-PROMPT.md.bak`
   - Extract `{{doc_files}}` value from existing file (if customized)
   - Write new template with preserved `{{doc_files}}` substitution
   - Add version tag

### .wiggum.toml

1. Load existing config
2. Compare with current schema (all known config options)
3. For each missing option:
   - Add with default value
   - Add comment explaining the option
4. Never remove or modify existing user values
5. Preserve comments if possible (use tomlkit for round-trip parsing)

Example upgrade:
```toml
# Before
[security]
yolo = true

[loop]
max_iterations = 10

# After
[security]
yolo = true
allow_paths = ""  # NEW: Comma-separated paths to allow writing

[loop]
max_iterations = 10
agent = "claude"  # NEW: Agent to use (claude, codex, gemini)

[git]  # NEW SECTION
enabled = false
branch_prefix = "wiggum"
```

### TASKS.md

1. Check for required sections: `## Todo`, `## Done`
2. Add missing sections without touching existing tasks
3. Don't modify task content

## Template Versioning

Add version tags to templates:

```markdown
<!-- wiggum-template: 0.5.0 -->
```

For `.wiggum.toml`, track schema version in config module:

```python
WIGGUM_CONFIG_SCHEMA_VERSION = "0.5.0"
WIGGUM_CONFIG_DEFAULTS = {
    "security": {"yolo": False, "allow_paths": ""},
    "loop": {"max_iterations": 10, "agent": "claude"},
    "git": {"enabled": False, "branch_prefix": "wiggum"},
}
```

## Edge Cases

1. **File doesn't exist**: Suggest running `wiggum init`
2. **User heavily customized LOOP-PROMPT.md**: Warn, suggest `--diff` first
3. **Backup already exists**: Use numbered backups (`.bak`, `.bak.1`, `.bak.2`)
4. **Config has unknown sections**: Preserve them (user extensions)
5. **Malformed TOML**: Error with helpful message, don't corrupt file

## Implementation

### Files to modify/create:

- `src/wiggum/upgrade.py` - New module with upgrade logic
- `src/wiggum/cli.py` - Add `upgrade` command
- `src/wiggum/config.py` - Add schema version and defaults
- `src/wiggum/templates/LOOP-PROMPT.md` - Add version tag (done)

### Dependencies:

- Consider `tomlkit` for round-trip TOML parsing (preserves comments)
- Or use simple append-based approach for new config options

## Out of Scope

- Downgrading to older versions
- Three-way merge of customized LOOP-PROMPT.md
- Upgrading spec files in `specs/`
- Auto-migration of deprecated config options (handle in future version)
