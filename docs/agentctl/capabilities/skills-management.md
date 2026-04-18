<!-- agentctl:auto-generated -->
# Skills management

- Key: `skills-management`
- Group: `control-plane`
- Status: `ok`
- Front door: `agentctl skills`

## Summary

Skills management

## Entry Points

- `agentctl skills list`
- `agentctl skills add`
- `agentctl skills check`
- `agentctl skills update`

## Backing Interfaces

- `tool` `npx` [ok]
- `tool` `skills` [ok]

## Overlap Policy

- Wrap official skills tooling rather than reimplementing it.
