---
name: agentctl-maintenance-engineer
description: Maintain the agentctl control plane itself. Use when checking or refreshing agentctl docs, command-to-doc drift, capability-registry health, maintenance state, plugin packaging, config enablement, cloud-readiness docs, or the machine-readable maintenance report. Trigger after changing agentctl commands, adapters, plugin metadata, maintenance docs, or platform contracts.
---

# Agentctl Maintenance Engineer

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

## Overview

Treat `agentctl` as a maintained product. Use the maintenance commands to verify the control plane, refresh its docs, and keep its packaging and state explicit.

## Workflow

1. Run `agentctl maintenance check` first to inspect current health.
2. If docs or packaging drift exists, run `agentctl maintenance audit`.
3. Read the generated outputs before making follow-up changes:
   - `C:\Users\leona\.codex\docs\agentctl\maintenance.md`
   - `C:\Users\leona\.codex\docs\agentctl\maintenance-report.json`
   - `C:\Users\leona\.codex\.codex-workflows\agentctl-maintenance\state.json`
4. If the issue is documentation-only, use `agentctl maintenance fix-docs`.
5. If only the report page needs a refresh, use `agentctl maintenance render-report`.

## Operating Rules

- Keep `agentctl` as the control plane, not as a replacement for vendor CLIs, Playwright, or Codex execution.
- Keep the command surface frozen unless you also update the generated docs and tests.
- Keep cloud-readiness explicit. Local success is not proof of cloud support.
- Do not hand-edit generated maintenance docs unless you are changing the generator itself.

## References

- Read [workflow.md](C:/Users/leona/.codex/skills/agentctl-maintenance-engineer/references/workflow.md) when you need the exact maintenance commands and artifact paths.
- Read [maintenance-contract.md](C:/Users/leona/.codex/agentctl/references/maintenance-contract.md) when you are changing the maintenance subsystem itself.
- Read [cloud-readiness.md](C:/Users/leona/.codex/agentctl/references/cloud-readiness.md) when changes affect cloud assumptions.
