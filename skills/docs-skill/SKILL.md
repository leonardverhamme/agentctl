---
name: docs-skill
description: Durable repo documentation workflow for README updates, architecture notes, ADRs, runbooks, onboarding docs, developer guides, and command references that must stay aligned with the code. Use when code changes create doc drift, when a decision needs an ADR, or when repo-native documentation should become clearer and more navigable.
---

# Docs Skill

## Visible Skill Usage

- When this skill is actively being used in chat, mention `$docs-skill` once in a user-visible update so the human can see the highlighted skill route.
- Keep that mention concise and do not repeat it in every paragraph.

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

Use this skill to keep durable engineering docs accurate, navigable, and close to the real code and commands.

If you cannot load the supporting references for some reason, still follow the defaults in this file.

## What This Skill Covers

- Updating durable README and onboarding docs
- Creating or refreshing `docs/Architecture.md` or repo-native architecture maps
- Writing or updating ADRs
- Updating runbooks, command references, and operational notes
- Keeping developer docs aligned after structural or workflow changes

## What This Skill Does Not Cover

- Full-repo deep doc audits with checklist execution
- Marketing copy, sales copy, or content writing as the main task
- Broad code refactors
- UI or test deep audits

Use:

- `$context-skill` for repo maps and durable context maintenance
- `$refactor-skill` or `$refactor-orchestrator` for structural code work
- `$docs-deep-audit` for full-repo docs audits, checklist execution, and older repos with broad documentation drift

## Bare Invocation Behavior

If the user explicitly invokes `$docs-skill` with no meaningful extra instruction, do a lightweight docs review and report:

1. the main durable docs that already exist
2. the biggest stale or missing docs
3. the highest-value next documentation update

Do not start a broad docs rewrite in this mode.

## Required Workflow

1. Inspect the real sources of truth first:
   - AGENTS, README, architecture docs, ADRs, runbooks, and feature docs
   - package files, scripts, commands, CI entrypoints, and code ownership boundaries
   - the exact code or configuration that changed
2. Prefer updating existing docs over creating parallel ones.
3. Load the references you need from this skill:
   - Always: `references/durable-docs.md`, `references/architecture-overview.md`, `references/runbooks-and-commands.md`
   - For decision records: `references/adr-patterns.md`
   - When comparing against proven systems: `references/premade-systems.md`
   - Short reusable prompts: `references/prompt-template.md`
4. Put information in the narrowest durable home:
   - README for repo entry and basic run/start
   - architecture doc for system map and boundaries
   - ADR for a single durable technical decision
   - runbook for operational procedures
5. Keep docs navigational and concrete.
6. Verify commands, file paths, and ownership statements against the code.
7. Report what was updated and what still deserves documentation later.

## Default Documentation Posture

- Docs are context infrastructure, not ceremony.
- Prefer one clear home per topic.
- Keep architecture docs navigational.
- Keep ADRs short, decision-focused, and durable.
- Record commands exactly as they run in the repo.
- Add diagrams only when they materially improve understanding.

## Hard Rules

- Do not duplicate the same information across README, AGENTS, architecture docs, and ADRs.
- Do not document guessed commands or paths.
- Do not write giant aspirational docs detached from the codebase.
- Do not open a new doc file when an existing durable home fits.
- Do not repeat obvious code line-by-line when a higher-level explanation is enough.

## References

- `references/durable-docs.md`
- `references/adr-patterns.md`
- `references/architecture-overview.md`
- `references/runbooks-and-commands.md`
- `references/premade-systems.md`
- `references/prompt-template.md`

