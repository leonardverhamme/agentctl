---
name: cicd-deep-audit
description: "Full-repo CI/CD audit and checklist-driven remediation workflow for pipelines, release automation, workflow reuse, quality gates, environments, and deployment safety. Use when auditing an older repo's automation surface, writing or refreshing a markdown checklist such as docs/cicd-deep-audit-checklist.md with `- [ ]` items, executing that checklist until the automation posture is materially better, and only replying `ready` when zero unchecked items remain. If explicitly invoked with no further instructions, run the default full-cycle workflow automatically using docs/cicd-deep-audit-checklist.md: audit or refresh, execute, keep iterating, and close out."
---

# CI/CD Deep Audit

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

## Repo Artifact Rule

- If this workflow needs helper scripts, workflow helpers, or generated reports, create them in the target repo, not in `$CODEX_HOME`, not in a skill folder, and not in the agentctl bundle unless that bundle repo is the target.
- Prefer repo-native locations such as `scripts/`, `tools/`, `bin/`, `.github/scripts/`, `docs/`, or `.codex-workflows/`.

Use this skill for the heavy CI/CD workflow that `$cicd-skill` should not absorb: full automation audit, canonical checklist creation, checklist execution, and final closeout.

For implementation decisions while working the checklist, load `$cicd-skill` and use it as the base CI/CD skill.

## Required Entry Point

- If `agentctl` is available, start or resume this workflow through `agentctl run cicd-deep-audit`, not by relying on chat memory alone.
- Treat `docs/cicd-deep-audit-checklist.md` as the human queue and `.codex-workflows/cicd-deep-audit/state.json` as the machine queue.
- If unattended execution is expected, the outer loop must use a real worker command such as an explicit worker command or a configured Codex worker template. A checklist file by itself is not a worker.

## Core Modes

- Full-cycle mode: audit or refresh, then execute the checklist in the same run, then close out.
- Audit-only mode: inspect the pipeline surface and write or refresh the checklist without implementing fixes.
- Execution-only mode: read the checklist file as the source of truth and work through unchecked items.
- Closeout-only mode: verify that no invalid completions remain and only then reply `ready`.

Full-cycle mode is the default. Audit-only is never the default.

## Bare Invocation Behavior

If the user explicitly invokes `$cicd-deep-audit` with no meaningful extra instruction, run the default full-cycle workflow automatically:

1. Use `docs/cicd-deep-audit-checklist.md` as the checklist path.
2. Run a fresh audit pass or refresh the existing checklist unless the user explicitly asked for execution-only behavior.
3. Immediately start executing the checklist in the same run.
4. Keep iterating until the checklist is complete or a real blocker remains.
5. Run closeout validation.
6. Only reply `ready` when the closeout rules pass.

## Default File Contract

- Default checklist path: `docs/cicd-deep-audit-checklist.md`
- Default state path: `.codex-workflows/cicd-deep-audit/state.json`
- If the user gives a specific path, use that instead.
- Treat the checklist file as the queue and source of truth.
- Re-read the checklist file before each new batch of work instead of trusting chat memory.
- Re-open the state file at the start of every turn. If checklist and state disagree, repair the state from the checklist before continuing.

## Shared Runtime Contract

- When `.codex-workflows/cicd-deep-audit/state.json` exists or should be created, load or initialize it and keep it in sync with the checklist.
- Use the bundle-local `workflow-tools/workflow_schema.md` as the shared runtime schema.
- Update the checklist and the workflow state after each meaningful batch.
- Never self-certify `ready`; only do so when the bundle-local `workflow-tools/workflow_guard.py --state <state.json>` check would pass.

## Required Workflow

1. Inspect the repo first:
   - CI workflow files, release automation, deploy configs, package scripts, build commands, test commands, typecheck and lint commands
   - workflow duplication, matrix usage, concurrency, caches, environments, permissions, secrets references, artifact flow, preview and production deployment logic
   - release docs and rollback notes
2. Load the references you need from this skill:
   - Always: `references/audit-scope.md`, `references/checklist-format.md`, `references/execution-loop.md`, `references/closeout.md`
   - Short reusable prompts: `references/prompt-shortcuts.md`
3. Load `$cicd-skill` before implementing checklist items so fixes stay aligned with the repo's actual automation model.
4. Create or refresh the checklist file from a fresh audit pass unless the user explicitly asked for audit-only behavior.
5. Group findings by automation surface, then by workflow, environment, or subsystem.
6. Use markdown checkboxes:
   - `- [ ]` unresolved or blocked
   - `- [x]` implemented and validated
7. Keep findings concrete, fixable, and implementation-ready.
8. Start execution in the same run after the audit refresh unless the user explicitly asked for audit-only behavior.
9. Before marking anything done, implement it, validate the workflow logic and underlying commands, and update the checklist file.
10. Continue until zero unchecked items remain or a real blocker remains.
11. Only reply `ready` when the closeout rules pass.

## Automatic Mode Selection

When the user does not clearly choose a mode:

- Bare invocation or vague requests like "deep CI audit", "audit the pipelines", or "use this skill": full-cycle mode
- Explicit "audit only", "review only", or "do not change workflows yet": audit-only mode
- Explicit "execute the checklist", "finish this file", or "continue fixing CI": execution-only mode
- Explicit "close out" or "verify ready": closeout-only mode

## Audit Output Rules

- Cover the full automation surface, not only one workflow file.
- Include PR checks, release workflows, deploy flows, matrices, caches, concurrency, permissions, environments, secrets references, artifact paths, and rollback gaps where relevant.
- Prefer actionable defects and missing protections over vague pipeline commentary.
- Deduplicate overlapping findings so the checklist stays workable.

## Execution Rules

- Work from the checklist file, not from memory.
- Work from the state file and checklist together, not from prior chat claims.
- Pick a coherent batch of unchecked items.
- Prefer small coherent batches, usually 2 to 6 related items.
- Implement the workflow or release fixes.
- Run the smallest correct validation for that batch.
- Mark items `- [x]` only after implementation and validation.
- If a workflow depends on missing secrets or platform state, leave the item unchecked and add a short blocker note.
- Keep going until no unchecked items remain.

## Early-Stop Rules

- Do not stop immediately after creating or refreshing the checklist unless the user explicitly asked for audit-only behavior.
- Do not treat "deep CI audit" as audit-only.
- Do not stop because the checklist is large; continue in coherent validated batches.
- If a real blocker prevents further progress, say exactly what is blocked and what remains unchecked.

## Closeout Rules

- Do not say `ready` if any `- [ ]` items remain.
- Do not say `ready` if items were marked complete without evidence of workflow changes and validation.
- Do not say `ready` if key quality gates, release safety, or pipeline correctness still drift from the checklist claims.
- If blocked items remain, say what is blocked and why.

## References

- `references/audit-scope.md`
- `references/checklist-format.md`
- `references/execution-loop.md`
- `references/closeout.md`
- `references/prompt-shortcuts.md`
