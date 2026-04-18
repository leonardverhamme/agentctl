# Global Codex Guidance

- Use `agentctl` first for capability discovery, maintenance checks, research routing, and deep workflow launch.
- Prefer `agentctl run <workflow>` over repeating the same deep-skill prompt to force progress.
- Prefer `agentctl research web|github|scout` when external evidence is needed before implementation.
- Keep vendor CLIs authoritative for their own systems; use `agentctl` to route to them, not to replace them.
- Keep Playwright authoritative for browser automation; use the browser route that `agentctl` reports as healthiest.
- Treat `.codex-workflows/<workflow>/state.json` as the source of truth for deep workflow progress and completion.
- After changing `agentctl`, its plugin, or its contracts, run `agentctl maintenance audit` or use `$agentctl-maintenance-engineer`.
- Treat `skills/` and `plugins/*/skills/` as stable infrastructure during normal work.
- Never create, edit, rename, move, or delete a skill unless the user explicitly asks to change the skill system itself and explicitly confirms that `skill-edit-mode` should open.
- Use `$skill-edit-mode` for intentional skill creation or skill maintenance only after that confirmation is present.
