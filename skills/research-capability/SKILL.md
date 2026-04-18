---
name: research-capability
description: Navigate the research capability in agentctl. Use when deciding between web research, GitHub research, and mixed scouting before implementation.
---

# Research Capability

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself and has confirmed `skill-edit-mode`.

## Overview

Use this as the thin navigation layer for research. The actual work still happens in `$internet-researcher`, `$github-researcher`, or `$web-github-scout`.

## Workflow

1. Run `agentctl capability research`.
2. Read the generated page at `docs/agentctl/capabilities/research.md`.
3. Use `$internet-researcher` for current public-web research.
4. Use `$github-researcher` for repository, issue, release, and code-pattern research.
5. Use `$web-github-scout` when the task needs both tracks and a merged shortlist.

## Do Not Do

- Do not bypass the shared research evidence contract.
- Do not mix web and GitHub evidence blindly before checking which route the task actually needs.
- Do not invent a new research front door when `agentctl research` already covers it.
