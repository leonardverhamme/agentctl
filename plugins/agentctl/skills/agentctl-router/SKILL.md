---
name: agentctl-router
description: Route Codex work through agentctl when the task is about capability discovery, research routing, maintenance, or deep workflow launch. Use when the user needs to know what tools exist, which interface is healthy, how to start or resume a deep workflow, or which research route should be used before implementation.
---

# Agentctl Router

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

## Overview

Use `agentctl` as the first door for control-plane questions and long-running workflow launch. Keep the source of truth in the underlying skills, vendor CLIs, Playwright, and Codex runtime.

## Routing Rules

- Use `agentctl doctor` or `agentctl capabilities` to inspect what is installed and healthy.
- Use `agentctl capability <key>` when the agent needs the drill-down page for one capability or vendor surface.
- Prefer the thin capability skills such as `$github-capability`, `$vercel-capability`, `$supabase-capability`, `$browser-capability`, `$stripe-capability`, `$sentry-capability`, `$figma-capability`, and `$nextjs-runtime-capability` when the task clearly belongs to one of those surfaces and visible skill usage is helpful.
- Use `agentctl research web|github|scout` for evidence-driven research before implementation.
- Use `agentctl run <workflow>` for deep workflows such as `ui-deep-audit` or `test-deep-audit`.
- Use `agentctl maintenance ...` when the control plane itself may have drifted.

## Do Not Do

- Do not force the agent to think in terms of CLI vs MCP vs plugin first; route by capability, then pick the healthiest authoritative interface.
- Do not reinvent vendor CLI logic inside the skill.
- Do not bypass the shared workflow state contract for deep workflows.
- Do not assume cloud support from local success. Use the explicit cloud-readiness docs.
