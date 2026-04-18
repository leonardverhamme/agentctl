<!-- agentctl:auto-generated -->
# Autonomous deep runs

- Key: `autonomous-deep-runs`
- Group: `control-plane`
- Status: `ok`
- Front door: `agentctl run`

## Summary

Autonomous deep runs

## Entry Points

- `agentctl run <workflow>`
- `CODEX_WORKFLOW_WORKER_COMMAND`
- `AGENTCTL_CODEX_WORKER_TEMPLATE`

## Advisory

- Default Codex runtime is not callable in this environment. Use `--worker-command` or configure `AGENTCTL_CODEX_WORKER_TEMPLATE` for unattended deep runs.

## Backing Interfaces

- `tool` `codex` [degraded]

## Overlap Policy

- The outer execute-until-done loop must use a real worker command, not chat memory. Prefer Codex runtime when it is callable or explicitly templated.
