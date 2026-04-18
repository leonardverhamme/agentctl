---
name: context-skill
description: General repo-context maintenance workflow for coding agents and humans. Use when mapping a codebase, updating AGENTS.md, refreshing architecture or repo-map docs, documenting commands and conventions, reducing onboarding friction, or keeping durable repo context aligned with the current code after restructures, new modules, workflow changes, or repeated confusion about where things live. This is a lightweight maintenance skill, not a deep auditor.
---

# Context Skill

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

Use this skill to keep durable repo context small, accurate, and easy for later sessions to reuse. It should improve the repo's own context artifacts, not replace them with chat memory.

If you cannot load the supporting references for some reason, still follow the defaults in this file.

## What This Skill Covers

- Updating `AGENTS.md` without bloating it
- Creating or refreshing architecture and repo-map docs
- Documenting commands, entrypoints, and verification paths
- Capturing module boundaries, ownership, and file-location guidance
- Making a repo easier to onboard into for later agent or human work

## What This Skill Does Not Cover

- Full-repo deep audits with checklist execution
- Broad code refactors
- Feature documentation or ADR writing as the primary task

Use:

- `$refactor-skill` or `$refactor-orchestrator` for structural code changes
- `$docs-skill` for ADRs, runbooks, and broader durable documentation maintenance

## Bare Invocation Behavior

If the user explicitly invokes `$context-skill` with no meaningful extra instruction, do a lightweight context pass and report:

1. the current durable context artifacts
2. the biggest context gaps or stale areas
3. the next highest-value repo context updates to make

Do not start a deep checklist workflow in this mode.

## Required Workflow

1. Inspect the repo first:
   - root and nested `AGENTS.md`
   - existing architecture, README, onboarding, and runbook docs
   - package files, scripts, CI entrypoints, dev-server commands, and app entrypoints
   - top-level folders, modules, services, UI shells, APIs, and data boundaries
2. Prefer updating existing context artifacts over creating new parallel ones.
3. Load the references you need from this skill:
   - Always: `references/agents-and-context.md`, `references/repo-mapping.md`, `references/context-review.md`
   - When structure changed materially: `references/context-refresh.md`
   - When comparing against proven systems: `references/premade-systems.md`
   - Short reusable prompts: `references/prompt-template.md`
4. Keep AGENTS small and durable.
5. Put larger navigational material into repo docs, not into AGENTS.
6. Record commands, boundaries, and file-finding guidance concretely.
7. Report what was updated and what still remains stale or implicit.

## Default Context Posture

- Keep `AGENTS.md` concise and enforceable.
- Put volatile details into normal docs, not AGENTS.
- Prefer navigational docs over giant manifestos.
- Prefer explicit commands and paths over vague prose.
- Update the source of truth instead of duplicating context in multiple files.

## Hard Rules

- Do not turn `AGENTS.md` into a giant essay.
- Do not duplicate the same context across `AGENTS.md`, README, architecture docs, and feature docs.
- Do not leave key repo commands only in chat when they belong in the repo.
- Do not invent new doc files when an existing durable home already exists.
- Do not document guesses as facts.

## References

- `references/agents-and-context.md`
- `references/repo-mapping.md`
- `references/context-refresh.md`
- `references/context-review.md`
- `references/premade-systems.md`
- `references/prompt-template.md`
