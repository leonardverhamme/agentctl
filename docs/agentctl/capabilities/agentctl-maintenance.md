<!-- agentctl:auto-generated -->
# Agentctl maintenance

- Key: `agentctl-maintenance`
- Group: `control-plane`
- Status: `ok`
- Front door: `$agentctl-maintenance-engineer`

## Summary

Agentctl maintenance

## Navigation Skills

- `agentctl-maintenance-engineer`

## Entry Points

- `agentctl maintenance check`
- `agentctl maintenance audit`
- `agentctl maintenance fix-docs`

## Backing Interfaces

- `plugin` `agentctl` [ok] (enabled=true)
- `skill` `agentctl-maintenance-engineer` [ok]

## Overlap Policy

- Keep maintenance as one capability surface for docs, packaging, registry health, and platform drift.
