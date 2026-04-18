---
name: nextjs-runtime-capability
description: Navigate the Next.js runtime capability in agentctl. Use when the task is about a running Next.js dev server, route introspection, or Next.js runtime/build diagnostics.
---

# Next.js Runtime Capability

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself and has confirmed `skill-edit-mode`.

## Overview

Use this as the thin navigation layer for Next.js runtime work. The real runtime surface stays in the Next DevTools MCP path.

## Workflow

1. Run `agentctl capability nextjs-runtime`.
2. Read the generated page at `docs/agentctl/capabilities/nextjs-runtime.md`.
3. Use the Next DevTools MCP route it documents for route, error, and runtime inspection.

## Do Not Do

- Do not replace the Next.js runtime tooling with generic browser guessing when the runtime capability already exists.

