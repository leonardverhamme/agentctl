<!-- agentctl:auto-generated -->
# Figma design

- Key: `figma-design`
- Group: `integrations`
- Status: `missing`
- Front door: `$figma-capability`

## Summary

Use for Figma design context, code-connect, design system search, and direct Figma edits via MCP.

## Navigation Skills

- `figma-capability`

## Entry Points

- `$figma-capability`
- `agentctl capability figma-design`
- `Figma MCP`

## Routing Notes

- Figma is MCP-backed here; use the capability page to see the supported operations before editing design files.

## Backing Interfaces

- `skill` `figma-capability` [ok]
- `mcp` `figma` [missing] (configured=false)

## Overlap Policy

- No plugin overlap here, so MCP remains the single capability entry.
