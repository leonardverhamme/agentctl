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

<!-- agentcli:repo-intel:start -->
## Repo Intelligence

- Treat the current repo as the default working universe; use `agentcli computer-intel ...` only when the target repo is unknown or the task is explicitly cross-repo.
- On repo entry or before broad raw-file search, run `agentcli repo-intel status`; if repo-intel is missing, stale, or broken for a trusted repo, run `agentcli repo-intel ensure`.
- If `graphify-out/GRAPH_REPORT.md` exists and repo-intel is healthy, read it before broad raw-file search.
- Prefer `agentcli repo-intel query "<question>"` or `agentcli repo-intel serve` for architecture and path questions before wide grep; open targeted raw files only after graph routing.
- If `agentcli` or `loopsmith` is not available on PATH, repair the public launcher with the bundle-local `agentctl.py doctor --fix` path before continuing; do not replace requested loops with docs-only tracking.
- Treat the current local branch as the canonical place for normal solo work; do not create or switch branches just to preserve agent changes.
- Treat Codex-managed worktrees as temporary isolation only; if work should be kept and pushed, continue from the local checkout so local commits and pushes do not require merging a worktree branch back.
- Create a separate branch only when explicitly requested or when a real PR flow or parallel-agent workflow needs branch isolation.
<!-- agentcli:repo-intel:end -->
