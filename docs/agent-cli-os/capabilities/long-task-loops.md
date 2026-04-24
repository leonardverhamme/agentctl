<!-- agent-cli-os:auto-generated -->
# Long task loops

- Key: `long-task-loops`
- Group: `core`
- Status: `ok`
- Front door: `$loopsmith`

## Summary

Use for oversized or novel tasks that need a durable checklist, state file, and one-batch-at-a-time loop until the queue is truly empty.

## Navigation Skills

- `loopsmith`

## Entry Points

- `$loopsmith`
- `agentcli capability long-task-loops`
- `agentcli loop <name>`
- `agentcli status --repo <path>`
- `agentcli self-check`

## Routing Notes

- Start with `$loopsmith`, then launch the durable loop with `agentcli loop <name>`.
- Prefer `agentcli run <workflow>` when a dedicated deep workflow already exists, such as UI, docs, test, refactor, or CI/CD audits.
- If `agentcli` or `loopsmith` is not on PATH, repair the launcher with the bundle-local `agentctl.py doctor --fix` path before continuing; do not replace the loop with docs-only tracking.
- Store the task brief on disk and let the outer runner own `.codex-workflows/<name>/state.json`, the checklist, and the progress notes.

## Backing Interfaces

- `skill` `loopsmith` [ok]

## Overlap Policy

- Use named deep workflows first. Use the generic durable loop only when the task is large, multi-step, and does not already fit a dedicated workflow skill.
