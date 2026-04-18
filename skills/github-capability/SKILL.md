---
name: github-capability
description: Navigate the GitHub capability surface in agentctl. Use when the task is about repositories, pull requests, issues, releases, GitHub Actions, or deciding whether to use the GitHub plugin skills or `gh`.
---

# GitHub Capability

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself and has confirmed `skill-edit-mode`.

## Overview

Use this as the thin navigation layer for GitHub work. This skill should route into `agentctl`, the GitHub plugin skills, and `gh` rather than reimplementing GitHub logic itself.

## Workflow

1. Run `agentctl capability github-workflows`.
2. Read the generated page at `docs/agentctl/capabilities/github-workflows.md` under the active `CODEX_HOME`.
3. If the task is about GitHub Advanced Security, CodeQL, code scanning, secret scanning, Dependabot alerts, dependency review, or security campaigns, switch to `$github-security-capability`.
4. If the GitHub plugin skills clearly cover the task, use them.
5. Otherwise use `gh` for direct repository, issue, PR, or Actions operations.

## Do Not Do

- Do not duplicate GitHub operational logic in this skill.
- Do not bypass `agentctl` when health, auth, or overlap is unclear.
