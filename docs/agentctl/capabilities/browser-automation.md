<!-- agentctl:auto-generated -->
# Browser automation

- Key: `browser-automation`
- Group: `research-and-verification`
- Status: `ok`
- Front door: `$browser-capability`

## Summary

Use for real browser automation, screenshots, runtime UI verification, and dynamic-site inspection.

## Navigation Skills

- `browser-capability`
- `playwright`

## Entry Points

- `$browser-capability`
- `agentctl capability browser-automation`
- `$playwright`
- `playwright.cmd`
- `Playwright MCP`

## Routing Notes

- Prefer Playwright CLI when a terminal-driven browser route is enough.
- Use Playwright MCP when the structured MCP browser path gives a better interface for the task.

## Backing Interfaces

- `skill` `browser-capability` [ok]
- `skill` `playwright` [ok]
- `tool` `playwright` [ok]
- `mcp` `playwright` [missing] (configured=false)
- `plugin` `vercel@openai-curated` [missing] (enabled=false)

## Overlap Policy

- Treat Playwright CLI and MCP as peer browser backends behind one browser capability.
