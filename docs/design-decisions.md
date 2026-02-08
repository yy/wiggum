# Design Decisions

Decisions that have been made and should not be re-litigated unless the context changes.

## No agent-specific path handling abstraction

**Decision**: Each agent handles `allow_paths` differently in its own file. No shared helper.

**Rationale**: Claude uses `--allowedTools Edit:/path* Write:/path*`, Codex uses `--add-dir`, Gemini passes raw strings. Only 2 lines are common between any pair. Three similar lines of code is better than a premature abstraction.

## Precompiled regex at module level

**Decision**: All regex patterns are compiled once at module level with `_PATTERN_NAME` convention.

**Rationale**: These patterns are used in hot paths (task checking runs every iteration). Compiling once avoids repeated compilation overhead.

## Progressive fallback parsing

**Decision**: The markdown parser tries increasingly loose strategies rather than failing on the first mismatch.

**Rationale**: LLM output is unpredictable. Claude sometimes wraps in `` ```markdown ``, sometimes `` ``` ``, sometimes no fences at all. The fallback chain handles all observed variations. Combined with retry logic (up to 3 attempts), this makes the system robust to output format drift.

## Config schema as data, not code

**Decision**: `CONFIG_SCHEMA` in config.py is a dict of `{section: {key: (default, type)}}`. Validation, upgrade detection, and default resolution all derive from this single source.

**Rationale**: Adding a new config option means adding one line to the schema dict. The upgrade command automatically detects missing options by diffing against the schema.

## TASKS.md merge on init (not overwrite)

**Decision**: `wiggum init` merges new tasks into existing TASKS.md rather than overwriting.

**Rationale**: Users may have manually added tasks. Overwriting would lose their work. The `--force` flag exists for when overwrite is intentional.

## Stop condition: regex, not structured parsing

**Decision**: `tasks_remaining()` just does a regex search for `- [ ]` in the file. It doesn't parse sections or validate structure.

**Rationale**: The agent writes to TASKS.md directly. We need to handle any valid markdown checkbox, regardless of what section it's in. A regex search is simpler and more robust than trying to parse the document structure.

## Yolo defaults to True

**Decision**: The `--yolo` flag defaults to True (skip permission prompts).

**Rationale**: wiggum is designed for automated loops where the agent runs unattended. Requiring permission prompts would defeat the purpose. Users who want safety use `--no-yolo` or `allow_paths`.

## Single task per loop iteration

**Decision**: The LOOP-PROMPT.md workflow instructs the agent to work on exactly one task per iteration.

**Rationale**: This gives wiggum clear checkpoints. After each iteration, it can check if the task was completed and report progress. Working on multiple tasks would make it harder to track what was done.

## Git branch creation by default

**Decision**: In git repos, `wiggum run` creates a new branch unless `--no-branch` or `--force` is passed.

**Rationale**: This prevents the agent from modifying the main branch directly. All changes are isolated on a wiggum branch, making it easy to review, merge, or discard. The branch name includes a timestamp for uniqueness.

## Learning diary is opt-out, not opt-in

**Decision**: Learning diary is enabled by default (`learning.enabled = true`).

**Rationale**: The diary captures useful patterns for future sessions. Most users benefit from it. The diary file is auto-cleaned after consolidation, so it doesn't accumulate.

## No interactive inputs during the loop

**Decision**: The agent loop runs without interactive prompts. All configuration is resolved before the loop starts.

**Rationale**: The loop is designed to run unattended. Any interactive prompt would block execution. Git safety checks, security mode, and all other decisions happen before the first iteration.
