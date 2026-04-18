<!-- agentctl:auto-generated -->
# GitHub workflows

- Key: `github-workflows`
- Group: `integrations`
- Status: `ok`
- Front door: `$github-capability`

## Summary

Use for repositories, pull requests, issues, release history, and Actions triage.

## Navigation Skills

- `github-capability`

## Entry Points

- `$github-capability`
- `agentctl capability github-workflows`
- `$github:github`
- `$github:gh-fix-ci`
- `$github:gh-address-comments`
- `gh`

## Routing Notes

- Prefer the GitHub capability skill when you need a quick route decision before acting.
- Use the GitHub plugin skills when they cover the task directly; use `gh` for direct CLI workflows and gaps in plugin coverage.

## Backing Interfaces

- `skill` `github-capability` [ok]
- `tool` `gh` [ok]
- `plugin` `github@openai-curated` [missing] (enabled=false)

## Overlap Policy

- Collapse GitHub plugin skills and gh into one capability entry instead of separate transport menus.
