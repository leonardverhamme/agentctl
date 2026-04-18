# Global Codex Guidance

- Use `agentctl` first for capability discovery, maintenance checks, research routing, and deep workflow launch.
- Use `agentctl capability <key>` when a task clearly belongs to one capability or vendor surface and the agent needs the drill-down page before picking concrete tools.
- Prefer thin capability skills such as `$github-capability`, `$vercel-capability`, `$supabase-capability`, `$browser-capability`, `$stripe-capability`, `$sentry-capability`, `$figma-capability`, and `$nextjs-runtime-capability` when that makes the route explicit and easier to follow in chat.
- Prefer `agentctl run <workflow>` over repeating the same deep-skill prompt to force progress.
- Prefer `agentctl research web|github|scout` when external evidence is needed before implementation.
- Keep vendor CLIs authoritative for their own systems; use `agentctl` to route to them, not to replace them.
- Choose interfaces by capability first, then use the healthiest authoritative path that `agentctl` reports instead of reasoning from transport type alone.
- Keep Playwright authoritative for browser automation; use the browser route that `agentctl` reports as healthiest.
- When a task needs a new helper script, create it in the target repo being worked on, not in `$CODEX_HOME`, not in the `agentctl` bundle repo unless that repo itself is the target, and never inside a skill directory.
- Treat `.codex-workflows/<workflow>/state.json` as the source of truth for deep workflow progress and completion.
- After changing `agentctl`, its plugin, or its contracts, run `agentctl maintenance audit` or use `$agentctl-maintenance-engineer`.
- Treat `skills/` and `plugins/*/skills/` as stable infrastructure during normal work.
- Never create, edit, rename, move, or delete a skill unless the user explicitly asks to change the skill system itself and explicitly confirms that `skill-edit-mode` should open.
- Use `$skill-edit-mode` for intentional skill creation or skill maintenance only after that confirmation is present.
