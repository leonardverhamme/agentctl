<!-- agentctl:auto-generated -->
# Supabase data

- Key: `supabase-data`
- Group: `integrations`
- Status: `ok`
- Front door: `$supabase-capability`

## Summary

Use for local Supabase stacks, migrations, database workflows, platform deploy steps, and Supabase project operations.

## Navigation Skills

- `supabase-capability`

## Entry Points

- `$supabase-capability`
- `agentctl capability supabase-data`
- `supabase`
- `Supabase MCP`

## Routing Notes

- CLI-first: `supabase init` and `supabase start` are the default local-development path.
- Do not rely on `npm install -g supabase`; prefer Scoop, Homebrew, standalone binaries, or `npx supabase`.
- If running via `npx`, require Node.js 20 or later.
- Local Supabase development expects a Docker-compatible container runtime.

## Backing Interfaces

- `skill` `supabase-capability` [ok]
- `tool` `supabase` [ok]
- `mcp` `supabase` [missing] (configured=false)
- `mcp` `supabase-remote` [missing] (configured=false)

## Overlap Policy

- Prefer the Supabase CLI for local stack, schema, migrations, and CI/CD. Use MCP when structured project access adds value beyond the CLI.
