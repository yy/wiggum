## Goal

{{goal}}

## Tasks

{{tasks}}

## Workflow

1. Read TASKS.md to see the current task list
2. Choose the most important task - prioritize upstream/blocking tasks and dependencies over file order
3. Determine the appropriate "done" criteria for this task:
   - **New behavior/logic/APIs/bug fixes**: Write tests first, then implement
   - **Renames, config changes, string updates**: Just verify the change works
   - **Documentation**: Review for accuracy and completeness
4. Implement the task with the appropriate approach
5. Cleanup and refactor before completing:
   - Remove dead code and unused imports you introduced
   - Simplify overly complex logic - if a function grew too large, break it up
   - Consolidate duplicates - extract repeated code into shared functions
   - Delete trivial tests that don't verify behavior (e.g., tests that only check string presence or file existence)
   - Ensure the code is production-ready, not just "works"
6. Run tests to verify nothing broke
7. Update TASKS.md to mark the task complete
8. Update documentation ({{doc_files}}) to reflect changes
9. If you discover new tasks while working, add them to TASKS.md

## Rules

- Only work on ONE task per session. If you discover tasks that should be done, add them to TASKS.md.
- If blocked, identify the blocking task, update TASKS.md, and work on the blocker first.
- Keep documentation in sync with implementation
- New tasks go in the Todo section with clear descriptions
