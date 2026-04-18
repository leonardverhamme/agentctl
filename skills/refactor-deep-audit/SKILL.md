---
name: refactor-deep-audit
description: "Broad refactor audit and checklist-driven remediation workflow for older repos and multi-module cleanup campaigns. Use when auditing a repo for structural debt, long files, tangled boundaries, outdated patterns, duplicated logic, migration candidates, and decomposition opportunities; when writing or refreshing a markdown checklist such as docs/refactor-deep-audit-checklist.md with `- [ ]` items; when executing that checklist in tracked waves; and when only replying `ready` once zero unchecked items remain. If explicitly invoked with no further instructions, run the default full-cycle workflow automatically using docs/refactor-deep-audit-checklist.md: audit or refresh, execute, keep iterating, and close out."
---

# Refactor Deep Audit

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

## Repo Artifact Rule

- If this workflow needs helper scripts, codemods, or generated migration helpers, create them in the target repo, not in `$CODEX_HOME`, not in a skill folder, and not in the agentctl bundle unless that bundle repo is the target.
- Prefer repo-native locations such as `scripts/`, `tools/`, `codemods/`, `bin/`, or `.codex-workflows/`.

Use this skill for the heavy refactor workflow that `$refactor-skill` should not absorb: broad structural audit, canonical checklist creation, tracked execution, and final closeout.

For implementation decisions while working the checklist, load `$refactor-skill` and use it as the base refactor skill. If you need additional migration and phasing guidance, also load `$refactor-orchestrator`.

## Required Entry Point

- If `agentctl` is available, start or resume this workflow through `agentctl run refactor-deep-audit`, not by relying on chat memory alone.
- Treat `docs/refactor-deep-audit-checklist.md` as the human queue and `.codex-workflows/refactor-deep-audit/state.json` as the machine queue.
- If unattended execution is expected, the outer loop must use a real worker command such as an explicit worker command, the built-in Codex worker wrapper when the Codex runtime is callable, or a configured Codex worker template. A checklist file by itself is not a worker.
- If `agentctl doctor` reports the autonomous deep-run route as degraded, do not quietly treat manual chat batches as an unattended loop. Fix the worker route first with `--worker-command`, `AGENTCTL_CODEX_WORKER_TEMPLATE`, or `AGENTCTL_CODEX_PATH`.
- A partial batch executed directly in chat is manual progress, not a running unattended deep audit.

## Core Modes

- Full-cycle mode: audit or refresh, then execute the checklist in the same run, then close out.
- Audit-only mode: inspect the repo structure and write or refresh the checklist without implementing fixes.
- Execution-only mode: read the checklist file as the source of truth and work through unchecked items.
- Closeout-only mode: verify that no invalid completions remain and only then reply `ready`.

Full-cycle mode is the default. Audit-only is never the default.

## Bare Invocation Behavior

If the user explicitly invokes `$refactor-deep-audit` with no meaningful extra instruction, run the default full-cycle workflow automatically:

1. Use `docs/refactor-deep-audit-checklist.md` as the checklist path.
2. Run a fresh structural audit pass or refresh the existing checklist unless the user explicitly asked for execution-only behavior.
3. Immediately start executing the checklist in the same run.
4. Keep iterating until the checklist is complete or a real blocker remains.
5. Run closeout validation.
6. Only reply `ready` when the closeout rules pass.

## Default File Contract

- Default checklist path: `docs/refactor-deep-audit-checklist.md`
- Default state path: `.codex-workflows/refactor-deep-audit/state.json`
- If the user gives a specific path, use that instead.
- Treat the checklist file as the queue and source of truth.
- Re-read the checklist file before each new batch of work instead of trusting chat memory.
- Re-open the state file at the start of every turn. If checklist and state disagree, repair the state from the checklist before continuing.

## Shared Runtime Contract

- When `.codex-workflows/refactor-deep-audit/state.json` exists or should be created, load or initialize it and keep it in sync with the checklist.
- Use the bundle-local `workflow-tools/workflow_schema.md` as the shared runtime schema.
- Update the checklist and the workflow state after each meaningful batch.
- Never self-certify `ready`; only do so when the bundle-local `workflow-tools/workflow_guard.py --state <state.json>` check would pass.

## Required Workflow

1. Inspect the repo first:
   - module boundaries, directory structure, entrypoints, service and UI seams, data flow, dependency direction, long files, duplication, and outdated patterns
   - tests and quality gates that can protect structural changes
   - architecture docs and ownership notes that may need updates
2. Load the references you need from this skill:
   - Always: `references/audit-scope.md`, `references/checklist-format.md`, `references/execution-loop.md`, `references/closeout.md`
   - Short reusable prompts: `references/prompt-shortcuts.md`
3. Load `$refactor-skill` before implementing checklist items so fixes stay behavior-preserving and scoped.
4. Create or refresh the checklist file from a fresh audit pass unless the user explicitly asked for audit-only behavior.
5. Group findings by subsystem, then by structural issue or migration wave.
6. Use markdown checkboxes:
   - `- [ ]` unresolved or blocked
   - `- [x]` implemented and validated
7. Keep findings concrete, fixable, and implementation-ready.
8. Start execution in the same run after the audit refresh unless the user explicitly asked for audit-only behavior.
9. Before marking anything done, implement it, validate behavior and structure, and update the checklist file.
10. Continue until zero unchecked items remain or a real blocker remains.
11. Only reply `ready` when the closeout rules pass.

## Automatic Mode Selection

When the user does not clearly choose a mode:

- Bare invocation or vague requests like "deep refactor audit", "clean this old repo", or "use this skill": full-cycle mode
- Explicit "audit only", "review only", or "do not refactor yet": audit-only mode
- Explicit "execute the checklist", "finish this file", or "continue refactoring": execution-only mode
- Explicit "close out" or "verify ready": closeout-only mode

## Audit Output Rules

- Cover the structural debt surface, not just one long file.
- Include long files, duplicate logic, tangled responsibilities, unstable boundaries, dependency cycles, awkward seams, migration candidates, and outdated compatibility paths where relevant.
- Prefer actionable structural work over abstract architecture commentary.
- Deduplicate overlapping findings so the checklist stays workable.

## Execution Rules

- Work from the checklist file, not from memory.
- Work from the state file and checklist together, not from prior chat claims.
- Pick a coherent batch of unchecked items.
- Prefer small coherent batches, usually 2 to 6 related items.
- Implement the refactor wave.
- Run the smallest correct validation for that batch.
- Mark items `- [x]` only after implementation and validation.
- If a correct test or validation reveals broken product behavior, fix the product code or setup rather than weakening the safety net.
- If an item cannot be completed yet, leave it unchecked and add a short blocker note.
- Keep going until no unchecked items remain.

## Early-Stop Rules

- Do not stop immediately after creating or refreshing the checklist unless the user explicitly asked for audit-only behavior.
- Do not treat "deep refactor audit" as audit-only.
- Do not stop because the checklist is large; continue in coherent validated waves.
- If a real blocker prevents further progress, say exactly what is blocked and what remains unchecked.

## Closeout Rules

- Do not say `ready` if any `- [ ]` items remain.
- Do not say `ready` if items were marked complete without evidence of code changes and validation.
- Do not say `ready` if the repo still has major structural debt in the areas the checklist claimed to fix.
- If blocked items remain, say what is blocked and why.

## References

- `references/audit-scope.md`
- `references/checklist-format.md`
- `references/execution-loop.md`
- `references/closeout.md`
- `references/prompt-shortcuts.md`
