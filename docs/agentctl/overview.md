<!-- agentctl:auto-generated -->
# Agentctl Overview

## Purpose

`agentctl` is the thin Codex-first control plane for discovery, routing, health checks, deep-workflow launch, and machine-readable state.

## Layers

1. Repo guidance in `AGENTS.md` and a small set of stable docs.
2. Skills for repeated workflows such as UI, testing, refactor, docs, research, and maintenance.
3. `agentctl` as the runtime control plane above those skills and above authoritative vendor interfaces.
4. Plugin packaging so the system can be installed and surfaced consistently.

## Current Status

- Maintenance status: `ok`
- Checks passed: 51 / 51
- Open findings: 0
- Blocked findings: 0

## Authoritative Interfaces

- Skill installation and update stay with the official `skills` CLI and `gh skill` when available.
- Vendor CLIs remain authoritative for their own platforms.
- Playwright remains the browser authority.
- Codex remains the execution engine for local and cloud work.

## First Things To Read

- Start with `agentctl doctor` when you need a compact health check.
- Use `agentctl capabilities` when you need the full capability menu and preferred front doors.
- Use `agentctl capability <key>` when you need the drill-down page for a specific capability or vendor surface.
- Use `agentctl status --all` to see which durable deep workflows are active now.
- Use `agentctl maintenance audit` after changing command surface, packaging, state contracts, or docs generators.

## Manual Guides

- [Zero-touch setup](zero-touch-setup.md) for one-command bootstrap and bootstrap-report expectations.
- [Install on another computer](install-on-another-computer.md) for moving the bundle to a new machine.
- [Unattended worker setup](unattended-worker-setup.md) for getting deep workflow loops to keep running with a real worker.
- [Maintainer guide](maintainer-guide.md) for generated-vs-manual docs, release hygiene, and validation expectations.
- [Skill governance](skill-governance.md) for the rules that keep capability skills thin, documented, and low-context.

## Common Agent Flows

- Capability discovery: `agentctl doctor` then `agentctl capabilities` if a broader inventory is needed.
- External research: `agentctl research web|github|scout <query>` and carry the JSON evidence + brief into implementation.
- Deep remediation: `agentctl run <workflow>` and trust `.codex-workflows/<workflow>/state.json` over chat history.
- Autonomous deep remediation only counts when a real worker command exists. The runner loop is deterministic; the worker must be real.
- Control-plane upkeep: `$agentctl-maintenance-engineer` or `agentctl maintenance audit`.

## Verified Workflow Guarantees

- The shared runner is covered for `complete`, `stalled`, and `blocked` terminal states.
- The CLI front door is covered end-to-end with `agentctl run ...` plus `agentctl status --json` in a temp repo.
- Explicit worker-command execution is a supported and tested path for unattended deep runs.
- Registry writes are protected against transient Windows rename contention and against parallel shared-registry updates.
- Fresh bundle installs are smoke-tested and allowed to finish `ok` when only degraded-but-documented capabilities remain.
- The remaining environment-specific limitation is the default local Codex runtime on this machine; if that runtime is unavailable, use an explicit worker command or `AGENTCTL_CODEX_WORKER_TEMPLATE`.

## Capability-First Rule

Agents should choose a capability front door first and ignore transport details unless the capability itself is degraded.

- Good: "use the research capability" or "use the browser capability".
- Bad: "start by choosing between CLI, MCP, or plugin".

The capability registry exists to collapse those overlaps into one stable route.

## Key Files

- Control plane home: `agentctl/`
- Capabilities snapshot: `agentctl/state/capabilities.json`
- Maintenance report: `docs/agentctl/maintenance-report.json`
- Maintenance state: `.codex-workflows/agentctl-maintenance/state.json`

## What Agentctl Does Not Own

- It does not replace the official `skills` CLI or `gh skill`.
- It does not replace vendor CLIs such as `gh`, `vercel`, or `supabase`.
- It does not replace Playwright as the browser runtime.
- It does not replace Codex execution or cloud environments.

## Known Limitations

- `gh skill` is not available locally, so publish/preview wrappers remain disabled.
- The default local Codex runtime is not callable here. Use `agentctl run --worker-command ...` or configure `AGENTCTL_CODEX_WORKER_TEMPLATE` for unattended deep runs.
- `firebase` is detected but intentionally remains detect-only in v1.
- `gcloud` is detected but intentionally remains detect-only in v1.
