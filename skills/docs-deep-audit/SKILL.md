---
name: docs-deep-audit
description: "Full-repo documentation audit and checklist-driven remediation workflow for durable engineering docs, ADRs, architecture overviews, runbooks, README files, and developer guides. Use when auditing an older repo's documentation surface, writing or refreshing a markdown checklist such as docs/docs-deep-audit-checklist.md with `- [ ]` items, executing that checklist until the durable docs are aligned with the code, and only replying `ready` when zero unchecked items remain. If explicitly invoked with no further instructions, run the default full-cycle workflow automatically using docs/docs-deep-audit-checklist.md: audit or refresh, execute, keep iterating, and close out."
---

# Docs Deep Audit

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

## Repo Artifact Rule

- If this workflow needs helper scripts or generated documentation helpers, create them in the target repo, not in `$CODEX_HOME`, not in a skill folder, and not in the agentctl bundle unless that bundle repo is the target.
- Prefer repo-native locations such as `scripts/`, `tools/`, `docs/`, or `.codex-workflows/`.

Use this skill for the heavy documentation workflow that `$docs-skill` should not absorb: full-repo docs audit, canonical checklist creation, checklist execution, and final closeout.

For documentation decisions while working the checklist, load `$docs-skill` and use it as the base documentation skill.

## Required Entry Point

- If `agentctl` is available, start or resume this workflow through `agentctl run docs-deep-audit`, not by relying on chat memory alone.
- Treat `docs/docs-deep-audit-checklist.md` as the human queue and `.codex-workflows/docs-deep-audit/state.json` as the machine queue.
- If unattended execution is expected, the outer loop must use a real worker command such as an explicit worker command or a configured Codex worker template. A checklist file by itself is not a worker.

## Core Modes

- Full-cycle mode: audit or refresh, then execute the checklist in the same run, then close out.
- Audit-only mode: inspect the repo docs surface and write or refresh the checklist without implementing fixes.
- Execution-only mode: read the checklist file as the source of truth and work through unchecked items.
- Closeout-only mode: verify that no invalid completions remain and only then reply `ready`.

Full-cycle mode is the default. Audit-only is never the default.

## Bare Invocation Behavior

If the user explicitly invokes `$docs-deep-audit` with no meaningful extra instruction, run the default full-cycle workflow automatically:

1. Use `docs/docs-deep-audit-checklist.md` as the checklist path.
2. Run a fresh audit pass or refresh the existing checklist unless the user explicitly asked for execution-only behavior.
3. Immediately start executing the checklist in the same run.
4. Keep iterating until the checklist is complete or a real blocker remains.
5. Run closeout validation.
6. Only reply `ready` when the closeout rules pass.

## Default File Contract

- Default checklist path: `docs/docs-deep-audit-checklist.md`
- Default state path: `.codex-workflows/docs-deep-audit/state.json`
- If the user gives a specific path, use that instead.
- Treat the checklist file as the queue and source of truth.
- Re-read the checklist file before each new batch of work instead of trusting chat memory.
- Re-open the state file at the start of every turn. If checklist and state disagree, repair the state from the checklist before continuing.

## Shared Runtime Contract

- When `.codex-workflows/docs-deep-audit/state.json` exists or should be created, load or initialize it and keep it in sync with the checklist.
- Use the bundle-local `workflow-tools/workflow_schema.md` as the shared runtime schema.
- Update the checklist and the workflow state after each meaningful batch.
- Never self-certify `ready`; only do so when the bundle-local `workflow-tools/workflow_guard.py --state <state.json>` check would pass.

## Required Workflow

1. Inspect the repo first:
   - README files, onboarding docs, architecture docs, ADR folders, runbooks, command docs, feature docs, and AGENTS files
   - package files, scripts, CI entrypoints, environments, and code boundaries the docs should reflect
   - where commands, flows, and ownership have drifted
2. Load the references you need from this skill:
   - Always: `references/audit-scope.md`, `references/checklist-format.md`, `references/execution-loop.md`, `references/closeout.md`
   - Short reusable prompts: `references/prompt-shortcuts.md`
3. Load `$docs-skill` before implementing checklist items so fixes stay aligned with the repo's durable documentation model.
4. Create or refresh the checklist file from a fresh audit pass unless the user explicitly asked for audit-only behavior.
5. Group findings by doc surface, then by file or subsystem.
6. Use markdown checkboxes:
   - `- [ ]` unresolved or blocked
   - `- [x]` implemented and validated
7. Keep findings concrete, fixable, and implementation-ready.
8. Start execution in the same run after the audit refresh unless the user explicitly asked for audit-only behavior.
9. Before marking anything done, implement it, verify the commands, paths, and code alignment, and update the checklist file.
10. Continue until zero unchecked items remain or a real blocker remains.
11. Only reply `ready` when the closeout rules pass.

## Automatic Mode Selection

When the user does not clearly choose a mode:

- Bare invocation or vague requests like "deep docs audit", "audit the docs", or "use this skill": full-cycle mode
- Explicit "audit only", "review only", or "do not update docs yet": audit-only mode
- Explicit "execute the checklist", "finish this file", or "continue fixing docs": execution-only mode
- Explicit "close out" or "verify ready": closeout-only mode

## Audit Output Rules

- Cover the whole durable documentation surface, not only the root README.
- Include README, onboarding, architecture overviews, ADRs, runbooks, command docs, feature docs, and repo context docs where present.
- Flag stale commands, wrong paths, missing ownership or boundary docs, duplicated information, missing ADRs, and missing operational guidance where it matters.
- Prefer actionable doc defects over vague commentary.
- Deduplicate overlapping findings so the checklist stays workable.

## Execution Rules

- Work from the checklist file, not from memory.
- Work from the state file and checklist together, not from prior chat claims.
- Pick a coherent batch of unchecked items.
- Prefer small coherent batches, usually 2 to 6 related items.
- Implement the documentation fixes.
- Run the smallest correct verification for that batch.
- Mark items `- [x]` only after implementation and validation.
- If a command or path cannot be verified yet, leave the item unchecked and add a short blocker note.
- Keep going until no unchecked items remain.

## Early-Stop Rules

- Do not stop immediately after creating or refreshing the checklist unless the user explicitly asked for audit-only behavior.
- Do not treat "deep docs audit" as audit-only.
- Do not stop because the checklist is large; continue in coherent validated batches.
- If a real blocker prevents further progress, say exactly what is blocked and what remains unchecked.

## Closeout Rules

- Do not say `ready` if any `- [ ]` items remain.
- Do not say `ready` if items were marked complete without evidence of updated docs and verification.
- Do not say `ready` if key docs still drift from the code or commands.
- If blocked items remain, say what is blocked and why.

## References

- `references/audit-scope.md`
- `references/checklist-format.md`
- `references/execution-loop.md`
- `references/closeout.md`
- `references/prompt-shortcuts.md`
