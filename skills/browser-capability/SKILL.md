---
name: browser-capability
description: Navigate the browser automation capability in agentctl. Use when the task needs real-browser automation, screenshots, runtime UI verification, or deciding between Playwright CLI and Playwright MCP.
---

# Browser Capability

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself and has confirmed `skill-edit-mode`.

## Overview

Use this as the thin navigation layer for browser automation. The real browser runtime remains Playwright; this skill only routes into the healthiest browser path.

## Workflow

1. Run `agentctl capability browser-automation`.
2. Read the generated page at `docs/agentctl/capabilities/browser-automation.md`.
3. Prefer `$playwright` and the Playwright CLI when terminal-driven browser work is enough.
4. Use Playwright MCP when the structured MCP interface is the better fit for the task.

## Do Not Do

- Do not create a custom browser runtime here.
- Do not choose between CLI and MCP blindly without checking the capability page first.

