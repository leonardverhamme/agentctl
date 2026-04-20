<!-- agent-cli-os:auto-generated -->
# Plugin evaluation

- Key: `plugin-evaluation`
- Group: `core`
- Status: `missing`
- Front door: `$plugin-eval:plugin-eval`

## Summary

Use for evaluating skills and plugins, explaining token budgets, and planning or running local benchmark workflows.

## Navigation Skills

- `plugin-eval:plugin-eval`

## Entry Points

- `$plugin-eval:plugin-eval`
- `$plugin-eval:evaluate-plugin`
- `$plugin-eval:evaluate-skill`
- `agentcli capability plugin-evaluation`
- `plugin-eval start <path> --request "<natural request>"`

## Routing Notes

- Start with `$plugin-eval:plugin-eval` for chat-first evaluation requests such as score explanations, fix-first prioritization, and benchmark planning.
- Use the local `plugin-eval` command when you want the exact analyze, explain-budget, measurement-plan, or benchmark workflow on disk.
- Fixture skills bundled with the Plugin Eval repo are test data and stay hidden from the curated capability surface.

## Backing Interfaces

- `tool` `plugin-eval` [ok]
- `plugin` `plugin-eval@openai-curated` [missing] (enabled=false)
- `skill` `plugin-eval:plugin-eval` [missing]

## Overlap Policy

- Keep plugin and skill evaluation behind one chat-first route instead of scattering analysis, budget, and benchmark commands through the default menu.
