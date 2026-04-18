---
name: test-deep-audit
description: "Full-repo test audit and checklist-driven remediation workflow for backend and frontend codebases. Use when auditing the entire repository's test health, mapping current coverage and missing layers, writing or refreshing a markdown checklist such as docs/test-deep-audit-checklist.md with `- [ ]` items, executing that checklist until all items are implemented and validated, and only replying `ready` when zero unchecked items remain. Also use when the user asks for deep test criticism, repo-wide test gap analysis, full automation quality review, or a queue-like workflow for test remediation. If explicitly invoked with no further instructions, run the default full workflow automatically using docs/test-deep-audit-checklist.md: audit the repo, refresh the checklist, execute the checklist, keep iterating until complete or blocked, and then run closeout."
---

# Test Deep Audit

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

## Repo Artifact Rule

- If this workflow needs helper scripts, fixtures, generated test helpers, or audit artifacts, create them in the target repo, not in `$CODEX_HOME`, not in a skill folder, and not in the agentctl bundle unless that bundle repo is the target.
- Prefer repo-native locations such as `scripts/`, `tools/`, `tests/helpers/`, `test/helpers/`, `docs/`, or `.codex-workflows/`.

Use this skill for the heavy workflow that the normal testing skill should not absorb: full-repo test audit, canonical checklist creation, checklist execution, and final closeout.

For implementation decisions while working the checklist, load `$test-skill` and use it as the base testing skill.

## Required Entry Point

- If `agentctl` is available, start or resume this workflow through `agentctl run test-deep-audit`, not by relying on chat memory alone.
- Treat `docs/test-deep-audit-checklist.md` as the human queue and `.codex-workflows/test-deep-audit/state.json` as the machine queue.
- If unattended execution is expected, the outer loop must use a real worker command such as an explicit worker command or a configured Codex worker template. A checklist file by itself is not a worker.

## Core Modes

- Audit mode: inspect the full repo and write or refresh the checklist file.
- Execution mode: read the checklist file as the source of truth and work through unchecked items.
- Closeout mode: verify that no invalid completions remain and only then reply `ready`.

## Bare Invocation Behavior

If the user explicitly invokes `$test-deep-audit` with no meaningful extra instruction, run the default workflow automatically:

1. Use `docs/test-deep-audit-checklist.md` as the checklist path.
2. Run a fresh audit pass of the repo and create or refresh the checklist file.
3. Immediately start executing the checklist in the same run.
4. Keep iterating until the checklist is complete or a real blocker remains.
5. Run closeout validation.
6. Only reply `ready` when the closeout rules pass.

## Default File Contract

- Default checklist path: `docs/test-deep-audit-checklist.md`
- Default state path: `.codex-workflows/test-deep-audit/state.json`
- If the user gives a specific path, use that instead.
- Treat the checklist file as the queue and source of truth.
- Re-read the checklist file before each new batch of work instead of trusting chat memory.
- Re-open the state file at the start of every turn. If checklist and state disagree, repair the state from the checklist before continuing.

## Shared Runtime Contract

- When `.codex-workflows/test-deep-audit/state.json` exists or should be created, load or initialize it and keep it in sync with the checklist.
- Use the bundle-local `workflow-tools/workflow_schema.md` as the shared runtime schema.
- Update the checklist and the workflow state after each meaningful batch.
- Never self-certify `ready`; only do so when the bundle-local `workflow-tools/workflow_guard.py --state <state.json>` check would pass.

## Required Workflow

1. Inspect the repo first:
   - test scripts, CI workflows, coverage tools, fixtures, seeds, mocks, factories, test directories, and reporters
   - runtime stacks for backend and frontend
   - browser automation setup, Playwright usage, accessibility setup, contract testing, property-based testing, mutation testing, and flake handling
2. Load the references you need from this skill:
   - Always: `references/audit-scope.md`, `references/checklist-format.md`, `references/execution-loop.md`, `references/closeout.md`
   - Short reusable prompts: `references/prompt-shortcuts.md`
3. Load `$test-skill` before implementing checklist items so fixes stay aligned with the repo's actual testing strategy.
4. Create or refresh the checklist file from a fresh audit pass unless the user explicitly asked for execution-only behavior.
5. Group findings by area, then by page, feature, package, or subsystem as needed.
6. Use markdown checkboxes:
   - `- [ ]` unresolved or blocked
   - `- [x]` implemented and validated
7. Keep findings concrete, fixable, and implementation-ready.
8. Start executing the checklist in the same run after the audit refresh.
9. Before marking anything done, implement it, validate it, and update the checklist file.
10. Continue until zero unchecked items remain or a real blocker remains.
11. Only reply `ready` when the closeout rules pass.

## Automatic Mode Selection

- Bare invocation: full-cycle mode
- Explicit audit-only request: audit mode
- Explicit execution-only request: execution mode
- Explicit closeout-only request: closeout mode

## Parallel And Agent Rules

- Do not simulate coverage by repeating the same prompt.
- Use the checklist file as the stateful queue.
- If the user explicitly asks for subagents, delegation, parallel work, or deeper coverage, partition the repo and use subagents by audit zone or subsystem.
- Good audit zones are:
  - test scripts, package manager commands, and CI entrypoints
  - unit and integration coverage
  - backend services, APIs, and data boundaries
  - frontend components, forms, and app flows
  - browser smoke, e2e, and Playwright coverage
  - accessibility and visual regression
  - contracts, schemas, and consumer-provider drift
  - edge cases, property-based coverage, mutation gaps, flake and speed problems

## Audit Output Rules

- Cover the full repo, not only the obvious test folder.
- Include backend and frontend test health.
- Include unit, integration, e2e, regression, accessibility, contract, visual, edge-case, mutation, flake, CI, and speed concerns where relevant.
- Prefer actionable defects and concrete missing coverage over abstract testing commentary.
- Deduplicate overlapping findings so the checklist stays workable.

## Execution Rules

- Work from the checklist file, not from memory.
- Work from the state file and checklist together, not from prior chat claims.
- Pick a coherent batch of unchecked items.
- Prefer small coherent batches, usually 2 to 6 related items.
- Implement the fixes or missing tests.
- Run the smallest correct validation.
- Mark items `- [x]` only after implementation and validation.
- If a correct test reveals broken product code, fix the code instead of weakening the test.
- If an item cannot be completed yet, leave it unchecked and append a short blocker note instead of pretending it is done.
- Keep going until no unchecked items remain.

## Early-Stop Rules

- Do not stop immediately after refreshing the checklist unless the user explicitly asked for audit-only behavior.
- Do not treat vague requests like "deep check" or "use this skill" as audit-only.
- Do not stop because the checklist is large; continue in coherent validated batches.
- If a real blocker prevents further progress, say exactly what is blocked and what remains unchecked.

## Closeout Rules

- Do not say `ready` if any `- [ ]` items remain.
- Do not say `ready` if items were marked complete without evidence of implementation and validation.
- Do not say `ready` if the suite is still broken, flaky, or clearly unbalanced in a way the checklist claimed to fix.
- If blocked items remain, say what is blocked and why.

## References

- `references/audit-scope.md`
- `references/checklist-format.md`
- `references/execution-loop.md`
- `references/closeout.md`
- `references/prompt-shortcuts.md`
