<!-- agentctl:auto-generated -->
# CI/CD workflows

- Key: `cicd-workflows`
- Group: `workflow-skills`
- Status: `ok`
- Front door: `$cicd-skill / $cicd-deep-audit`

## Summary

CI/CD workflows

## Navigation Skills

- `cicd-skill`
- `cicd-deep-audit`

## Entry Points

- `$cicd-skill`
- `$cicd-deep-audit`
- `agentctl run cicd-deep-audit`

## Backing Interfaces

- `skill` `cicd-deep-audit` [ok]
- `skill` `cicd-skill` [ok]

## Overlap Policy

- Surface CI/CD by workflow, not by whether GitHub or Vercel provides the underlying route.
