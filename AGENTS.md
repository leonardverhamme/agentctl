# Agent CLI OS Repo Guidance

- Keep this file short. It is a routing map, not the system of record. Put detail in `docs/agent-cli-os/`, generated pages, and `agentcli capability <key>`.
- Use `agentcli capabilities` as the default front door. Use `agentcli inventory show` only when the raw installed or autodetected surface matters.
- Keep the default surface compact: no flat dumps, no automatic promotion from detected tools into front-door capabilities, and no bloated capability skills.
- Prefer `agentcli run <workflow>` for named deep workflows. Use `$loopsmith` with `agentcli loop <name>` for durable large tasks that need disk-backed state.
- When a curated front-door skill is actually being used, mention it once in chat with the literal `$skill-name` so the human can see the highlighted route. This applies to local skills and plugin-backed front doors.
- After routing, prefer the healthiest authoritative interface that `agentcli` reports. Vendor CLIs remain authoritative for their own systems.
- Require a real Playwright verification pass for runnable UI or browser-facing work.
- When asked to add tests, use `$test-skill` and choose the materially needed layers.
- Never edit `skills/` or `plugins/*/skills/` unless the user explicitly asks for skill work and explicitly opens `$editskill`.
- After changing control-plane behavior or routing surface, follow `docs/agent-cli-os/maintainer-guide.md` and run `agentcli maintenance audit --json`.
