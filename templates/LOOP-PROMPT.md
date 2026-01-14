## Goal

{{goal}}

## Workflow

1. Read TASKS.md to see the current task list
2. Identify the highest priority incomplete task
3. Define what "done" looks like for this task (acceptance criteria)
4. Write tests FIRST that verify the acceptance criteria
5. Run tests - they should fail (red)
6. Implement the task
7. Run tests - they must pass (green)
8. Only after tests pass: Update TASKS.md to mark the task complete
9. Update documentation ({{doc_files}}) to reflect changes
10. If you discover new tasks while working, add them to TASKS.md

## Rules

- Only work on ONE task per session
- NEVER mark a task complete unless tests pass
- If blocked, add a note to TASKS.md and move to the next task
- Keep documentation in sync with implementation
- New tasks go in the Todo section with clear descriptions

## Test Requirements

- Every task must have tests before implementation
- Tests must be runnable with a single command
- Tests must pass before a task can be marked done
- If existing tests break, fix them before proceeding
