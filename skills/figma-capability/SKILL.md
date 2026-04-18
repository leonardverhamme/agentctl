---
name: figma-capability
description: Navigate the Figma capability in agentctl. Use when the task is about Figma design context, code-connect, design-system search, or direct Figma MCP operations.
---

# Figma Capability

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself and has confirmed `skill-edit-mode`.

## Overview

Use this as the thin navigation layer for Figma work. Figma is MCP-backed in this setup.

## Workflow

1. Run `agentctl capability figma-design`.
2. Read the generated page at `docs/agentctl/capabilities/figma-design.md`.
3. Use the Figma MCP route described there for design context, code-connect, and direct design operations.

## Do Not Do

- Do not invent a separate Figma routing layer in this skill.
- Do not assume local success implies cloud readiness without checking the page.

