<!-- agentctl:auto-generated -->
# Research

- Key: `research`
- Group: `research-and-verification`
- Status: `ok`
- Front door: `$research-capability`

## Summary

Use for routing current web research, GitHub scouting, and mixed evidence briefs through one front door.

## Navigation Skills

- `research-capability`
- `internet-researcher`
- `github-researcher`
- `web-github-scout`

## Entry Points

- `$research-capability`
- `agentctl capability research`
- `agentctl research web`
- `agentctl research github`
- `agentctl research scout`

## Routing Notes

- Use the capability skill first, then pick `$internet-researcher`, `$github-researcher`, or `$web-github-scout` based on the evidence mix you need.
- Keep the shared evidence contract intact instead of inventing ad hoc research output formats.

## Backing Interfaces

- `skill` `github-researcher` [ok]
- `skill` `internet-researcher` [ok]
- `skill` `research-capability` [ok]
- `skill` `web-github-scout` [ok]

## Overlap Policy

- Hide web, GitHub, and browser transport choices behind one research surface and one evidence contract.
