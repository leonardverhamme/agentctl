<!-- agentctl:auto-generated -->
# Next.js runtime

- Key: `nextjs-runtime`
- Group: `integrations`
- Status: `missing`
- Front door: `$nextjs-runtime-capability`

## Summary

Use for live Next.js dev-server diagnostics, route introspection, and runtime/build error inspection.

## Navigation Skills

- `nextjs-runtime-capability`

## Entry Points

- `$nextjs-runtime-capability`
- `agentctl capability nextjs-runtime`
- `Next DevTools MCP`

## Routing Notes

- Prefer Next DevTools MCP over generic browser logs when the task is specifically about a running Next.js app.

## Backing Interfaces

- `skill` `nextjs-runtime-capability` [ok]
- `mcp` `next-devtools` [missing] (configured=false)

## Overlap Policy

- Keep Next.js runtime tooling as one capability entry backed by Next DevTools MCP.
