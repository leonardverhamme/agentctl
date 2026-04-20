<!-- agent-cli-os:auto-generated -->
# Code review

- Key: `code-review`
- Group: `workflows`
- Status: `missing`
- Front door: `$coderabbit:coderabbit-review`

## Summary

Use for AI-powered review of the current diff, structured findings, and follow-up fix guidance.

## Navigation Skills

- `coderabbit:coderabbit-review`

## Entry Points

- `$coderabbit:coderabbit-review`
- `agentcli capability code-review`
- `coderabbit review --agent`

## Routing Notes

- Start with `$coderabbit:coderabbit-review` when you want a real AI review of the current changes rather than an ad hoc chat review.
- Keep CodeRabbit findings separate from human findings and do not claim manual review output came from CodeRabbit.
- If the CodeRabbit CLI is not callable, keep the capability visible but marked degraded until the runtime is installed or linked.

## Backing Interfaces

- `plugin` `coderabbit@openai-curated` [missing] (enabled=false)
- `skill` `coderabbit:coderabbit-review` [missing]
- `tool` `coderabbit` [missing]

## Overlap Policy

- Keep AI-powered code review under one explicit route: the CodeRabbit plugin skill plus a callable CodeRabbit runtime.
