<!-- agentctl:auto-generated -->
# Vercel platform

- Key: `vercel-platform`
- Group: `integrations`
- Status: `ok`
- Front door: `$vercel-capability`

## Summary

Use for deployments, project linking, env vars, logs, domains, and Vercel platform operations.

## Navigation Skills

- `vercel-capability`

## Entry Points

- `$vercel-capability`
- `agentctl capability vercel-platform`
- `$vercel:vercel-cli`
- `$vercel:deployments-cicd`
- `vercel`

## Routing Notes

- Prefer Vercel plugin skills for guided workflows already packaged in Codex.
- Use the Vercel CLI for direct project operations and deployment commands.

## Backing Interfaces

- `skill` `vercel-capability` [ok]
- `tool` `vercel` [ok]
- `mcp` `com-vercel-vercel-mcp` [missing] (configured=false)
- `mcp` `vercel-remote` [missing] (configured=false)
- `plugin` `vercel@openai-curated` [missing] (enabled=false)

## Overlap Policy

- Keep one Vercel capability entry; plugin and CLI are primary, MCP stays background metadata.
