---
name: github-security-capability
description: Navigate the GitHub Advanced Security capability surface in agentctl. Use when the task is about GHAS rollout, CodeQL, code scanning, secret scanning, Dependabot alerts, dependency review, or deciding between `gh`, `gh codeql`, `ghas-cli`, and GitHub security APIs.
---

# GitHub Security Capability

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself and has confirmed `skill-edit-mode`.

## Overview

Use this as the thin navigation layer for GitHub Advanced Security work. The authoritative routes are `gh api` for security endpoints, `gh codeql` for local CodeQL tooling, and `ghas-cli` for rollout-at-scale work when that CLI is healthy.

## Workflow

1. Run `agentctl capability github-advanced-security`.
2. Read the generated page at `docs/agentctl/capabilities/github-advanced-security.md` under the active `CODEX_HOME`.
3. Prefer `ghas-cli` for GHAS enablement and rollout across many repositories when it is healthy.
4. Prefer `gh codeql` for local CodeQL CLI management, version pinning, and query workflows.
5. Prefer `gh api` for code scanning, secret scanning, Dependabot, and dependency review alert inspection or targeted automation.
6. If the task turns out to be generic GitHub repo/PR/issue work rather than GHAS, switch to `$github-capability`.

## Rules

- Do not assume the generic GitHub plugin skills cover GHAS-specific work; they currently do not provide first-class GHAS workflow coverage.
- Treat `ghas-cli` as optional enhancement, not the only path. If it is degraded, use `gh api` and `gh codeql`.
- Keep security work capability-first: choose the GitHub security route before thinking about CLI, plugin, or API transport details.

## Do Not Do

- Do not duplicate GHAS operational logic in this skill.
- Do not silently trust `ghas-cli` if `agentctl` reports it as degraded.
- Do not bypass `agentctl` when health, auth, or overlap is unclear.
