## Principles

**Verify everything.** Never assume code works—prove it. Write tests for behavior, run them continuously, and define clear acceptance criteria before implementation. If you can't verify it, you don't know it works.

**Leave the code better than you found it.** Refactor as you go. Fix code smells, remove duplication, and simplify complexity. Good code is easy to read, easy to change, and easy to delete. Technical debt compounds—pay it down constantly.

**Aim for simplicity.** The best code is code that doesn't exist. Before adding anything, ask: is this necessary? After implementing, ask: what can be removed?

## Using Subagents

This workflow is designed to leverage specialized subagents at key phases. If you have subagents available for these capabilities, use them:

- **Codebase analysis**: Understanding code structure, finding bugs, identifying issues
- **Code refactoring**: Detecting code smells, simplifying, improving maintainability
- **Security auditing**: Finding vulnerabilities, checking for data leakage risks

For trivial tasks (string changes, renames, config tweaks), you may skip the subagent phases.

## Workflow

### Phase 0: Orientation
*Use a codebase analysis subagent if available.*

1. Explore and understand the current state of the codebase
2. Run the test suite to verify a "green light" state
3. If tests fail: prioritize fixing them (add as blocking task in TASKS.md)

### Phase 1: Task Selection & Verification Design
4. Read TASKS.md to see the current task list
5. Choose the most important task
6. **If task references a spec file** (e.g., `see specs/feature.md`), read it first
7. Define verification criteria: What tests or checks will prove this task is complete?

### Phase 2: Test-First Implementation
8. **Decide if this task needs tests**:
   - YES: New behavior, logic, APIs, bug fixes → write tests first
   - NO: String changes, renames, config tweaks → skip to implementation
9. Write failing tests that define the expected behavior
10. Implement the task to make tests pass
11. Run tests continuously during implementation

### Phase 3: Refactoring & Simplification
*Use a code refactoring subagent if available.*

12. Review the code you changed and ask:
    - What can be removed? (dead code, unused imports, unnecessary features)
    - Is this over-engineered? (remove abstractions that aren't earning their keep)
    - Are there code smells? (duplication, long methods, tight coupling)
    - Can this be simpler?
13. Run tests again after any refactoring

### Phase 4: Security Review
*Use a security auditing subagent if available.*

14. **If your changes touch any of these areas**, perform a security review:
    - Authentication or authorization logic
    - Input validation or user data handling
    - File operations or external API calls
    - Cryptographic implementations
    - Environment variables or secrets handling
15. Skip this phase for clearly non-security-relevant changes

### Phase 5: Completion
16. **Update docs**: Ensure documentation ({{doc_files}}) matches the implementation
17. Update TASKS.md: mark task as `[x]` and move it to the `## Done` section

## When tests are NOT needed

Don't write tests for:
- String/message/label changes
- Renames or config changes
- Anything where the "test" would just check that a string exists

If you can't describe what behavior would regress without the test, you don't need a test.

## Rules

- Only work on ONE task per session
- If blocked, update TASKS.md and work on the blocker first

<!-- wiggum-template: 0.5.0 -->
