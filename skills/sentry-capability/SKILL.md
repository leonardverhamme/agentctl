---
name: sentry-capability
description: Navigate the Sentry capability in agentctl. Use when the task starts from a production error, event, or issue and you need the Sentry capability front door before taking action.
---

# Sentry Capability

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself and has confirmed `skill-edit-mode`.

## Overview

Use this as the thin navigation layer for Sentry-backed observability work.

## Workflow

1. Run `agentctl capability sentry-observability`.
2. Read the generated page at `docs/agentctl/capabilities/sentry-observability.md`.
3. Use the Sentry capability when the work begins with a production issue or event.

## Do Not Do

- Do not reimplement Sentry API logic in this skill.
- Do not bypass `agentctl` when capability health or auth is unclear.

