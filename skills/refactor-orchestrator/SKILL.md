---
name: refactor-orchestrator
description: Broad refactor and migration orchestration workflow for changes that span multiple modules, packages, or layers. Use when restructuring a subsystem, running a phased migration, decomposing a monolith area, replacing a cross-cutting pattern, or managing a risky multi-step refactor that needs sequencing, tracking, and closeout validation.
---

# Refactor Orchestrator

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

Use this skill for broad refactors that are too wide, risky, or stateful for `$refactor-skill`.

If you cannot load the supporting references for some reason, still follow the defaults in this file.

## What This Skill Covers

- Multi-module refactors
- Phased migrations with compatibility shims
- Large file or subsystem decomposition
- Cross-cutting API or data-flow cleanup
- Deprecation removal after call-site migration
- Checklist-driven structural cleanup with validation waves

## What This Skill Does Not Cover

- Full-repo "make everything cleaner" rewrites without scope
- UI or test deep audits
- Pure documentation maintenance
- Routine local refactors that fit inside one bounded area

Use:

- `$refactor-skill` for local safe cleanup
- `$test-skill` to add or update the needed safety nets as waves land
- `$docs-skill` when architecture docs or ADRs need to change with the new structure

## Bare Invocation Behavior

If the user explicitly invokes `$refactor-orchestrator` with no meaningful extra instruction, do not start rewriting the repo.

Instead:

1. identify the highest-value broad refactor candidates
2. explain the risk, likely waves, and validation path
3. recommend the next scoped orchestrated refactor to run

This default exists to avoid accidental repo churn.

## Execution Modes

### Inspect Mode

Use on bare invocation or when the user is still deciding scope.

Deliver:

- candidate refactor areas
- suggested sequencing
- validation requirements
- likely blockers

### Scoped Execution Mode

Use when the user gives a clear subsystem, migration target, or broad structural goal.

Deliver:

- a phased plan
- the code changes
- validation after each wave
- closeout notes and remaining debt

## Required Workflow

1. Inspect the current structure first:
   - architecture docs, AGENTS, and module boundaries
   - entrypoints, contracts, and dependency direction
   - tests and other quality gates that protect the area
2. State the invariant:
   - what must stay behaviorally true
   - what can change structurally
   - what counts as done
3. Load the references you need from this skill:
   - Always: `references/refactor-phases.md`, `references/risk-review.md`, `references/checklist-format.md`
   - For migrations and deprecations: `references/migration-patterns.md`
   - When comparing against proven systems: `references/premade-systems.md`
   - Short reusable prompts: `references/prompt-template.md`
4. Partition the work into waves.
5. Prefer a repo-native plan or checklist file if the repo already has one.
6. If no durable tracking file exists and the scope is broad, create a small tracked plan such as `docs/refactor-plan.md` or a repo-native equivalent.
7. Execute one wave at a time.
8. Validate after each wave.
9. Update docs or ADRs when boundaries materially change.
10. End with closeout:
   - what shipped
   - what remains
   - what follow-up work should not be bundled into this refactor

## Default Orchestration Posture

- Preserve behavior while changing structure.
- Prefer phased migrations over one-shot rewrites.
- Keep compatibility layers only as long as needed.
- Use the narrowest useful validation after each wave, then run the broader gates before stopping.
- Keep tracking explicit when the refactor spans time or modules.
- Only use subagents when the user explicitly asks for delegation or parallel work.

## Hard Rules

- Do not start a broad rewrite on a bare call.
- Do not refactor without a clear validation path.
- Do not mix unrelated cleanup into an already risky migration.
- Do not remove deprecated paths before callers are migrated and verified.
- Do not leave a half-migrated architecture undocumented when the boundary changed materially.
- Stop if concurrent user edits create direct conflicts in the same write area.

## References

- `references/refactor-phases.md`
- `references/migration-patterns.md`
- `references/checklist-format.md`
- `references/risk-review.md`
- `references/premade-systems.md`
- `references/prompt-template.md`
