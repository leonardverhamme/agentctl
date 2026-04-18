<!-- agentctl:auto-generated -->
# Autonomous deep runs

- Key: `autonomous-deep-runs`
- Group: `control-plane`
- Status: `ok`
- Front door: `$autonomous-deep-runs-capability`

## Summary

Use for launching, resuming, and diagnosing unattended deep workflows through the shared runner.

## Navigation Skills

- `autonomous-deep-runs-capability`

## Entry Points

- `$autonomous-deep-runs-capability`
- `agentctl capability autonomous-deep-runs`
- `agentctl run <workflow>`
- `CODEX_WORKFLOW_WORKER_COMMAND`
- `AGENTCTL_CODEX_WORKER_TEMPLATE`

## Routing Notes

- Start with the capability skill, then route into `agentctl run <workflow>`.
- A real worker command or `AGENTCTL_CODEX_WORKER_TEMPLATE` is still required for unattended execution.

## Advisory

- Default Codex runtime is not callable in this environment. Use `--worker-command` or configure `AGENTCTL_CODEX_WORKER_TEMPLATE` for unattended deep runs.

## Backing Interfaces

- `skill` `autonomous-deep-runs-capability` [ok]
- `tool` `codex` [degraded]

## Overlap Policy

- The outer execute-until-done loop must use a real worker command, not chat memory. Prefer Codex runtime when it is callable or explicitly templated.
