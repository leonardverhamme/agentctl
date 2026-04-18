---
name: autonomous-deep-runs-capability
description: Navigate unattended deep workflow execution in agentctl. Use when launching, resuming, or diagnosing deep audits and their worker-command setup.
---

# Autonomous Deep Runs Capability

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself and has confirmed `skill-edit-mode`.

## Overview

Use this as the thin navigation layer for unattended deep workflows. The loop logic stays in `agentctl` and `workflow-tools`; this skill only routes into the right runner path.

## Workflow

1. Run `agentctl capability autonomous-deep-runs`.
2. Read the generated page at `docs/agentctl/capabilities/autonomous-deep-runs.md`.
3. Launch or resume the workflow with `agentctl run <workflow>`.
4. If unattended execution is needed, provide `--worker-command` or make sure `AGENTCTL_CODEX_WORKER_TEMPLATE` is configured.
5. Treat the checklist plus `.codex-workflows/<workflow>/state.json` as the durable source of truth, not prior chat claims.

## Do Not Do

- Do not fake an execute-until-done loop with chat memory alone.
- Do not bypass the guard, checklist, or state contract.
- Do not claim unattended deep runs are healthy if there is no real worker route.
