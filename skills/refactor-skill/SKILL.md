---
name: refactor-skill
description: Focused code refactor workflow for one feature area, module, or bounded set of files. Use when modernizing code, splitting long files, extracting helpers or components, renaming APIs, tightening boundaries, removing duplication, or improving structure without changing intended behavior. This is the everyday refactor skill, not the broad migration or multi-module orchestration workflow.
---

# Refactor Skill

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

Use this skill for small to medium refactors that should stay behavior-preserving, test-backed, and tightly scoped.

If you cannot load the supporting references for some reason, still follow the defaults in this file.

## What This Skill Covers

- Extracting helpers, services, hooks, utilities, or subcomponents
- Breaking up long files or functions into smaller units
- Renaming symbols or APIs inside a bounded area
- Replacing deprecated patterns with modern equivalents
- Reducing duplication and clarifying module responsibilities
- Improving readability, dependency direction, and local structure

## What This Skill Does Not Cover

- Wide-scope migrations across many modules or subsystems
- Full-repo mechanical rewrites
- Deep audit or checklist-driven refactor campaigns
- Feature redesign disguised as refactoring

Use:

- `$refactor-deep-audit` for full structural audits, checklist execution, and broad cleanup campaigns on older repos
- `$refactor-orchestrator` for manually scoped broad refactors, migrations, and phased multi-module changes
- `$test-skill` when safety nets need to be added or expanded during the refactor
- `$docs-skill` when architecture docs or ADRs need to be updated after structural change

## Bare Invocation Behavior

If the user explicitly invokes `$refactor-skill` with no meaningful extra instruction, do a lightweight refactor review and report:

1. the most obvious safe refactor targets in the current area
2. the behavior constraints and validation path
3. the smallest high-value refactor to do next

Do not start a broad rewrite in this mode.

## Required Workflow

1. Inspect the target code first:
   - current responsibilities, boundaries, call sites, and data flow
   - existing tests, fixtures, and validation commands
   - AGENTS and repo docs that constrain the area
2. Define the behavior boundary before editing.
3. Load the references you need from this skill:
   - Always: `references/behavior-preserving.md`, `references/safety-net.md`, `references/scope-control.md`
   - Common refactor moves: `references/refactor-patterns.md`
   - When comparing against proven systems: `references/premade-systems.md`
   - Short reusable prompts: `references/prompt-template.md`
4. If coverage is weak, add or update the smallest useful characterization tests before risky edits.
5. Refactor in small verified steps.
6. Run the relevant checks after each meaningful step or batch.
7. Keep the diff narrow and structural.
8. Report what improved, what remains awkward, and what should wait for a broader pass.

## Default Refactor Posture

- Preserve behavior first.
- Prefer small steps over one-shot rewrites.
- Backfill safety nets before risky changes.
- Reuse existing repo abstractions before inventing new ones.
- Favor extraction, renaming, and simplification over architectural churn.
- Use repo-native CLIs first for validation.

## Hard Rules

- Do not silently mix feature changes into a refactor.
- Do not weaken correct tests just to get green.
- Do not do a repo-wide sweep without explicit scope.
- Do not leave the code in a partially broken state between steps when smaller steps are possible.
- If a correct test exposes a real defect, fix the product code or setup, not the test.
- Stop and ask only when ongoing user changes create a direct conflict.

## References

- `references/behavior-preserving.md`
- `references/refactor-patterns.md`
- `references/safety-net.md`
- `references/scope-control.md`
- `references/premade-systems.md`
- `references/prompt-template.md`
