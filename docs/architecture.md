# Architecture

## How wiggum works

wiggum runs a coding agent (Claude, Codex, or Gemini) in a loop. Each iteration sends the same prompt. The loop stops when all tasks in TASKS.md are checked off.

```
wiggum run
  → read LOOP-PROMPT.md
  → for each iteration:
      → check TASKS.md (stop if all done)
      → run agent with prompt
      → print output
      → check TASKS.md again
  → consolidate learning diary (if enabled)
  → show git summary / create PR (if enabled)
```

## Module map

```
src/wiggum/
├── cli.py          # All CLI commands (typer). Entry point.
├── config.py       # .wiggum.toml reading, validation, config resolution
├── runner.py       # Subprocess calls to agents, retry logic, log writing
├── tasks.py        # TASKS.md parsing (regex-based)
├── parsing.py      # Claude output parsing (markdown extraction)
├── agents.py       # Agent protocol, registry, CLI availability checks
├── agents_claude.py
├── agents_codex.py
├── agents_gemini.py
├── git.py          # Git operations (branch, commit, PR via gh)
├── learning.py     # Session diary capture and consolidation
├── changelog.py    # CHANGELOG.md generation from completed tasks
├── upgrade.py      # Template version detection and upgrade logic
├── __init__.py     # Package exports and version
└── templates/      # Default templates for init/upgrade
    ├── LOOP-PROMPT.md
    ├── META-PROMPT.md
    ├── CONSOLIDATE-PROMPT.md
    ├── TASKS.md
    └── SPEC.md
```

## Data flow

### `wiggum init`

1. Reads `META-PROMPT.md` template, fills in `{{goal}}` from README.md
2. Sends meta-prompt to Claude via `run_claude_with_retry()` (runner.py)
3. Parses Claude's response with `parse_markdown_from_output()` (parsing.py)
4. Extracts suggested tasks and security constraints
5. Writes `LOOP-PROMPT.md`, `TASKS.md`, `.wiggum.toml`
6. Updates `.gitignore` with wiggum files

### `wiggum run`

1. `read_config()` loads `.wiggum.toml`
2. `validate_config()` checks schema (type errors = fail, unknown keys = warn)
3. `resolve_run_config()` merges CLI flags over config values
4. Git safety: checks dirty state → stash/commit/abort → creates branch
5. Loop: for each iteration:
   - `tasks_remaining()` checks for unchecked `- [ ]` in TASKS.md
   - `get_agent()` returns agent instance from registry
   - `agent.run(AgentConfig)` executes subprocess
   - Output printed, optionally logged
6. Post-loop: consolidate diary, create PR if requested

### Config resolution order

CLI flags > `.wiggum.toml` values > hardcoded defaults (in `CONFIG_SCHEMA`)

## Agent protocol

Every agent implements:
```python
class Agent(Protocol):
    name: str
    def run(self, config: AgentConfig) -> AgentResult: ...
```

`AgentConfig` carries: prompt, yolo, allow_paths, continue_session.
`AgentResult` returns: stdout, stderr, return_code.

Agents are registered in `agents.py` `_agents` dict. Adding a new agent:
1. Create `agents_foo.py` with a class implementing `Agent`
2. Import and add to `_agents` in `agents.py`
3. Add CLI error message to `_CLI_ERROR_MESSAGES`

## Parsing pipeline

Claude's output from the meta-prompt goes through progressive fallback:

1. Try `` ```markdown `` fences (strictest)
2. Try `` ```<any-lang> `` fences
3. Try unfenced content (find first structural line: heading or list item)

Within extracted content, tasks are found via:
1. `## Tasks` heading section → checkboxes → plain list → numbered list
2. If no heading, search entire content with same priority

This is in `parsing.py`. The retry logic in `runner.py` will re-prompt Claude up to 3 times if parsing fails.

## Key patterns

- **Precompiled regex**: Module-level `re.compile()` with `_PATTERN_NAME` naming convention (tasks.py, parsing.py)
- **Lazy imports**: cli.py uses lazy imports for `learning.py`, `git.py`, `upgrade.py` to keep CLI startup fast
- **Config schema as data**: `CONFIG_SCHEMA` dict in config.py defines all valid options with `(default, type)` tuples — used for validation, upgrade detection, and default resolution
- **Runtime-checkable Protocol**: `Agent` uses `@runtime_checkable` for isinstance checks
