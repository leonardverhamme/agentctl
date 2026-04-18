---
name: vercel-capability
description: Navigate the Vercel platform capability in agentctl. Use when the task is about deployments, linking, logs, env vars, domains, Vercel platform operations, or deciding between Vercel plugin skills and the Vercel CLI.
---

# Vercel Capability

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself and has confirmed `skill-edit-mode`.

## Overview

Use this as the thin navigation layer for Vercel work. The real logic stays in the Vercel plugin skills, Vercel CLI, and configured platform interfaces.

## Workflow

1. Run `agentctl capability vercel-platform`.
2. Read the generated page at `docs/agentctl/capabilities/vercel-platform.md`.
3. Prefer the Vercel plugin skills when they already model the task well.
4. Use `vercel` for direct CLI operations such as linking, deployments, logs, or env work.

## Do Not Do

- Do not duplicate Vercel deployment logic in this skill.
- Do not bypass `agentctl` when deciding whether plugin, CLI, or MCP-backed Vercel tooling is the right route.

