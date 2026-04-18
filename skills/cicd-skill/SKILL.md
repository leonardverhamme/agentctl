---
name: cicd-skill
description: CI/CD and release workflow engineering for repo-native pipelines such as GitHub Actions and platform deployment configs. Use when adding or tightening build, test, lint, typecheck, package, preview, release, or deploy automation; when deduplicating workflows with reusable components; or when improving quality gates, concurrency, caching, and release safety without guessing the stack.
---

# CI/CD Skill

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

Use this skill for day-to-day pipeline and release automation work.

If you cannot load the supporting references for some reason, still follow the defaults in this file.

## What This Skill Covers

- Updating CI workflows and release pipelines
- Adding or tightening lint, typecheck, test, build, and packaging gates
- Designing reusable workflows or composite actions
- Improving matrix usage, concurrency, and caching
- Clarifying environment promotion, manual approvals, and rollback notes
- Keeping CI aligned with the repo's real local commands

## What This Skill Does Not Cover

- Broad release-program orchestration across many services
- Secret provisioning by guesswork
- Platform migrations with unclear ownership
- Full-repo deep audits with remediation queues

Use:

- `$test-skill` when the main work is adding or fixing tests
- `$docs-skill` when CI or release changes need durable runbooks or operational docs
- `$cicd-deep-audit` for full-repo pipeline audits, checklist execution, and older repos with broad automation drift

## Bare Invocation Behavior

If the user explicitly invokes `$cicd-skill` with no meaningful extra instruction, do a lightweight pipeline review and report:

1. the current CI/CD surfaces
2. the biggest safety or duplication gaps
3. the highest-value next improvement

Do not rewrite the whole pipeline in this mode.

## Required Workflow

1. Inspect the current pipeline surface first:
   - `.github/workflows/` or the repo's actual CI system
   - package files, build scripts, test commands, deploy configs, and environment usage
   - existing release docs, rollback notes, and manual approval flow
2. Prefer the repo's existing platform and CLI commands over inventing a parallel pipeline shape.
3. Load the references you need from this skill:
   - Always: `references/github-actions-basics.md`, `references/quality-gates.md`, `references/release-safety.md`
   - For duplication reduction or multi-target workflows: `references/workflow-reuse-and-matrix.md`
   - When comparing against proven systems: `references/premade-systems.md`
   - Short reusable prompts: `references/prompt-template.md`
4. Keep CI steps aligned with the same commands engineers run locally.
5. Separate fast PR feedback from slower release or deploy stages.
6. Reuse workflows or composite actions when duplication is real.
7. Keep permissions, secrets, and environments explicit and minimal.
8. Validate workflow syntax and the underlying commands before stopping.
9. Report what changed, what still requires secrets or platform setup, and what remains intentionally manual.

## Default CI/CD Posture

- Local and CI commands should match.
- Keep pull request feedback fast.
- Use reusable workflows to avoid copy-paste where it helps.
- Use matrix builds only when the variation is real.
- Use concurrency or cancellation to avoid stale duplicate runs.
- Keep deployments gated by explicit environments or approvals when risk is non-trivial.

## Hard Rules

- Do not invent secret names, environment variables, or deploy credentials.
- Do not hide failures behind broad `continue-on-error`.
- Do not make the pipeline slower without a quality reason.
- Do not bundle build, test, and deploy into one opaque job when separation improves safety.
- Do not assume one package manager or runtime if the repo already defines another.
- Do not claim CI is fixed unless the workflow and underlying commands both make sense.

## References

- `references/github-actions-basics.md`
- `references/workflow-reuse-and-matrix.md`
- `references/quality-gates.md`
- `references/release-safety.md`
- `references/premade-systems.md`
- `references/prompt-template.md`
