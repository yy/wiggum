# Tasks

## In Progress

## Todo

- [ ] Implement the 'ralph-loop run' command that executes the loop with configurable max_iterations, reads prompt from file, and invokes 'claude --print'
- [ ] Implement stop conditions: file_exists (exit when target file exists), task_complete (agent signals done), and iteration limit
- [ ] Add session management: --continue flag to maintain context between iterations vs --reset to start fresh each time
- [ ] Implement logging: write each iteration's output to a log file with timestamps and iteration numbers
- [ ] Show progress during loop: track and display file changes (via git status or filesystem) after each iteration
- [ ] Display current task at iteration start: parse TASKS.md to show which task the agent identified and is working on
- [x] Configure permissions during init to avoid blocking prompts: set up allowlist paths or --dangerously-skip-permissions, pass to claude during run so loop runs autonomously
- [ ] Support runtime overrides: --max-iterations, --prompt, and --stop-condition flags for 'ralph-loop run'

## Done
