---
name: ui-deep-audit
description: Full-app UI audit and checklist-driven remediation workflow for React, Next.js, Tailwind, and shadcn/ui apps. Use when auditing an entire app page by page, mapping routes and UI zones, writing or refreshing a markdown checklist file such as docs/ui-deep-audit-checklist.md with `- [ ]` items, executing that checklist until all items are implemented and validated, and only replying `ready` when zero unchecked items remain. Also use when the user asks for deep design or UX criticism, queue-like completion tracking, or subagent-based parallel UI audits. If explicitly invoked with no further instructions, run the default full workflow automatically using docs/ui-deep-audit-checklist.md.
---

# UI Deep Audit

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

## Overview

Use this skill for the heavy workflow that your normal UI skill should not absorb: deep full-app audit, canonical markdown checklist creation, checklist execution, and final closeout.

For UI implementation decisions while working the checklist, load `C:\Users\leona\.codex\skills\ui-skill\SKILL.md` and use it as the base implementation skill.

## Core Modes

- Audit mode: inspect the full app, map pages and UI zones, and write or refresh the checklist file.
- Execution mode: read the checklist file as the source of truth and work through unchecked items.
- Closeout mode: verify that no invalid completions remain and only then reply `ready`.

## Bare Invocation Behavior

If the user explicitly invokes `$ui-deep-audit` with no meaningful extra instruction, run the default workflow automatically:

1. Use `docs/ui-deep-audit-checklist.md` as the checklist path.
2. If the file does not exist, run a full audit and create it.
3. If the file exists and contains unchecked items, continue executing the checklist until it is complete or blocked.
4. If the file exists and every item is checked, run closeout validation.
5. Only reply `ready` when the closeout rules pass.

## Default File Contract

- Default checklist path: `docs/ui-deep-audit-checklist.md`
- If the user gives a specific path, use that instead.
- Treat the checklist file as the queue and source of truth.
- Re-read the checklist file before each new batch of work instead of trusting chat memory.

## Required Workflow

1. Inspect the app first:
   - routes, pages, layouts, shell components, navigation, feature modules
   - global styles, tokens, palette, spacing, radius, typography, charts, tables, forms, AI surfaces
   - lint, typecheck, test, and browser verification commands
2. Load the references you need from this skill:
   - Always: `references/audit-scope.md`, `references/checklist-format.md`, `references/execution-loop.md`, `references/closeout.md`
   - Short reusable prompts: `references/prompt-shortcuts.md`
3. Load `C:\Users\leona\.codex\skills\ui-skill\SKILL.md` before implementing checklist items so UI fixes stay consistent and dense instead of drifting.
4. If the checklist file does not exist, or the user asked for a fresh audit, create or refresh it.
5. Group findings by page, then by section or component.
6. Use markdown checkboxes:
   - `- [ ]` unresolved or blocked
   - `- [x]` implemented and validated
7. Keep findings concrete, fixable, and implementation-ready.
8. Before marking anything done, implement it, validate it, and update the checklist file.
9. Continue until zero unchecked items remain.
10. Only reply `ready` when the closeout rules pass.

## Automatic Mode Selection

When the user does not clearly choose a mode, infer it from the checklist file state:

- No checklist file: audit mode
- Checklist exists with `- [ ]` items: execution mode
- Checklist exists with zero `- [ ]` items: closeout mode

## Parallel and Agent Rules

- Do not simulate coverage by repeating the same prompt.
- Use the checklist file as the stateful queue.
- If the user explicitly asks for subagents, delegation, parallel work, or deeper coverage, partition the app and use subagents by audit zone or page group.
- Good audit zones are:
  - navigation and information architecture
  - overview and dashboard pages
  - CRUD and module pages
  - forms and validation UX
  - tables, density, and scanability
  - color, contrast, spacing, radius, and tokens
  - AI chat and assistant surfaces
  - responsiveness and mobile behavior
  - accessibility, focus, and keyboard behavior
  - consistency and design-system drift

## Audit Output Rules

- Cover the whole app, not just obvious pages.
- Go page by page, then section by section when needed.
- Include navigation, IA, overview, user friendliness, readability, scanability, color palette, contrast, corners, radius, spacing, typography, tables, forms, charts, AI surfaces, empty states, responsiveness, accessibility, and consistency.
- Prefer actionable defects over abstract design commentary.
- Deduplicate overlapping findings so the checklist stays workable.

## Execution Rules

- Work from the checklist file, not from memory.
- Pick a coherent batch of unchecked items.
- Implement the fixes.
- Run the smallest correct validation.
- Mark items `- [x]` only after implementation and validation.
- If an item cannot be completed yet, leave it unchecked and append a short blocker note instead of pretending it is done.
- Keep going until no unchecked items remain.

## Closeout Rules

- Do not say `ready` if any `- [ ]` items remain.
- Do not say `ready` if items were marked complete without evidence of implementation and validation.
- Do not say `ready` if the UI is visually inconsistent after the fixes.
- If blocked items remain, say what is blocked and why.

## References

- `references/audit-scope.md`
- `references/checklist-format.md`
- `references/execution-loop.md`
- `references/closeout.md`
- `references/prompt-shortcuts.md`
