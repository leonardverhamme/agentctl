---
name: skills-management-capability
description: Navigate skill installation and maintenance in agentctl. Use when listing, adding, checking, or updating skills and their provenance.
---

# Skills Management Capability

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself and has confirmed `skill-edit-mode`.

## Overview

Use this as the thin navigation layer for skill installs and provenance. The real install/update work still goes through `agentctl skills` and the official `skills` tooling.

## Workflow

1. Run `agentctl capability skills-management`.
2. Read the generated page at `docs/agentctl/capabilities/skills-management.md`.
3. Use `agentctl skills list`, `agentctl skills add`, `agentctl skills check`, or `agentctl skills update` as needed.
4. Keep installs pinned and let `skills-lock.json` remain the provenance source of truth.

## Do Not Do

- Do not reimplement a custom skill package manager here.
- Do not run broad unsafe updates when a narrower pinned action is enough.
- Do not bypass `agentctl skills` when the task is specifically about managed skill installs.
