<!-- agent-cli-os:auto-generated -->
# Agent CLI OS Overview

## Purpose

`agentcli` is the thin Codex-first control plane for capability discovery, routing, health checks, deep-workflow launch, and machine-readable state.

## Layers

1. Repo guidance in `AGENTS.md` and a small set of stable docs.
2. Skills for repeated workflows such as UI, testing, refactor, docs, research, and maintenance.
3. `agentcli` as the runtime control plane above those skills and above authoritative vendor interfaces.
4. Plugin packaging so the system can be installed and surfaced consistently.

## Current Status

- Maintenance status: `ok`
- Checks passed: 88 / 88
- Open findings: 0
- Blocked findings: 0

## First Things To Read

- `agentcli doctor` for a compact health check.
- `agentcli capabilities` for the grouped top-level capability menu.
- `agentcli capability <key>` for a group page or a single capability drill-down page.
- `agentcli skill-map` for the human one-page map of menu groups and local skills.
- `agentcli inventory show` when you need the raw autodetected inventory behind the curated menu.
- `agentcli status --all` for durable workflow state across repos.
- `agentcli maintenance audit` after command, packaging, config, or contract changes.

## Guides And Maps

- [Zero-touch setup](zero-touch-setup.md)
- [Install on another computer](install-on-another-computer.md)
- [Unattended worker setup](unattended-worker-setup.md)
- [Maintainer guide](maintainer-guide.md)
- [Control-plane governance](skill-governance.md)
- [Inventory model](inventory.md)
- [Skill map](skill-map.md)

## Common Flows

- Capability discovery: `agentcli doctor` then `agentcli capabilities`.
- Human-facing map: `agentcli skill-map` or `docs/agent-cli-os/skill-map.md`.
- Raw installed surface: `agentcli inventory show` then `agentcli inventory item <kind>:<name>`.
- External research: `agentcli research web|github|scout <query>`.
- Deep remediation: `agentcli run <workflow>` plus `.codex-workflows/<workflow>/state.json`.
- Generic long task: `$loopsmith` then `agentcli loop <name>` with a task brief on disk.
- Control-plane upkeep: `$agentcli-maintenance-engineer` or `agentcli maintenance audit`.

## Compatibility

- `agentcli` is the canonical public command.
- `loopsmith` remains a compatibility alias for the current migration release.
- The internal bundle path stays `agentctl/` for this release to avoid a risky filesystem and import break.

## Verified Guarantees

- Shared runner coverage exists for `complete`, `blocked`, and `stalled` terminal states.
- The CLI front door is covered end-to-end with `agentcli run ...` and `agentcli status --json` in temp repos.
- Fresh installs are smoke-tested and allowed to finish `ok` when only degraded-but-documented optional capabilities remain.
- The remaining environment-sensitive piece is the worker runtime itself; unattended runs still require a real callable worker route.

## Key Files

- Internal bundle path: `agentctl/`
- Capabilities snapshot: `agentctl/state/capabilities.json`
- Inventory snapshot: `agentctl/state/inventory.json`
- Guidance snapshot: `agentctl/state/guidance.json`
- Maintenance report: `docs/agent-cli-os/maintenance-report.json`
- Maintenance state: `.codex-workflows/agentcli-maintenance/state.json`

## What Agent CLI OS Does Not Own

- It does not replace the official `skills` CLI or `gh skill`.
- It does not replace vendor CLIs such as `gh`, `vercel`, or `supabase`.
- It does not replace Playwright as the browser runtime.
- It does not replace Codex execution or cloud environments.

## Known Limitations

- `gh skill` is not available locally, so publish/preview wrappers remain disabled.
- `firebase` is detected but intentionally remains detect-only in v1.
- `gcloud` is detected but intentionally remains detect-only in v1.
