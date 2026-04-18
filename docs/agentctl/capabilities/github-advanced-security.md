<!-- agentctl:auto-generated -->
# GitHub Advanced Security

- Key: `github-advanced-security`
- Group: `integrations`
- Status: `ok`
- Front door: `$github-security-capability`

## Summary

Use for GHAS rollout, CodeQL, code scanning alerts, secret scanning alerts, Dependabot alerts, dependency review, security overview, and organization-scale security automation.

## Navigation Skills

- `github-security-capability`

## Entry Points

- `$github-security-capability`
- `agentctl capability github-advanced-security`
- `ghas-cli`
- `gh codeql`
- `gh api`

## Routing Notes

- Prefer `ghas-cli` for GHAS enablement and rollout work across many repositories when it is callable.
- Prefer `gh codeql` for local CodeQL CLI management, version pinning, and query workflows.
- Prefer `gh api` for alert inspection and targeted automation against code scanning, secret scanning, Dependabot, and dependency review endpoints.
- No installed GitHub plugin skill currently provides GHAS-specific workflow coverage, so route security work through this capability instead of generic GitHub skills.
- Useful community extensions exist, such as `advanced-security/gh-codeql-scan`, `GitHubSecurityLab/gh-mrva`, `CallMeGreg/gh-secret-scanning`, and `securesauce/gh-alerts`, but they are optional extras rather than agentctl defaults.

## Backing Interfaces

- `skill` `github-security-capability` [ok]
- `tool` `gh` [ok]
- `tool` `gh-codeql` [ok]
- `tool` `ghas-cli` [degraded]
- `plugin` `github@openai-curated` [missing] (enabled=false)

## Overlap Policy

- Use `gh api` and `gh codeql` as the authoritative GitHub security routes, with `ghas-cli` as the rollout-at-scale helper when it is healthy. Do not assume generic GitHub plugin skills cover GHAS-specific work.
