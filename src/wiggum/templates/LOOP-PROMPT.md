## Workflow

1. Read TASKS.md to see the current task list
2. Choose the most important task - prioritize upstream/blocking tasks and dependencies over file order
3. **Decide if this task needs tests**:
   - YES: New behavior, logic, APIs, bug fixes - write tests first, then implement
   - NO: String changes, renames, config tweaks, template updates - just implement and verify
4. Implement the task (test-first if tests are needed)
5. Run tests to verify nothing broke
6. **Refactor**: Review code you touched and fix:
   - Dead code, unused imports, unused variables
   - Overly complex logic - break up large functions
   - Duplication - extract repeated code into shared functions
   - Silly tests that don't verify real behavior (delete them)
   - Bloat - remove unnecessary abstractions or over-engineering
   - Run tests again after refactoring
7. **Update docs**: Ensure all documentation ({{doc_files}}) matches the implementation
8. Update TASKS.md: mark task as `[x]` and move it to the `## Done` section

## When tests are NOT needed

Don't write tests for:
- Changing strings, messages, or labels
- Renaming variables, functions, or files
- Config or template changes
- Anything where the "test" would just check that a string exists

If you can't describe what behavior would regress without the test, you don't need a test.

## Rules

- Only work on ONE task per session
- If blocked, update TASKS.md and work on the blocker first
- Delete trivial tests you encounter that don't verify real behavior
