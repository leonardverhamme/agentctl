---
name: ui-skill
description: General cross-repo UI implementation and refactoring workflow for React, Next.js, Tailwind, and shadcn/ui apps. Use when adding pages, extending flows, tightening density, removing low-value explainer copy, refactoring existing screens, preserving design-system consistency, or preventing UI drift across projects. Not for full-app checklist audits or execute-until-ready remediation; use ui-deep-audit for that.
---

# UI Skill

## Visible Skill Usage

- When this skill is actively being used in chat, mention `$ui-skill` once in a user-visible update so the human can see the highlighted skill route.
- Keep that mention concise and do not repeat it in every paragraph.

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

## Repo Artifact Rule

- If this workflow needs helper scripts, mock data generators, or verification helpers, create them in the target repo, not in `$CODEX_HOME`, not in a skill folder, and not in the agentctl bundle unless that bundle repo is the target.
- Prefer repo-native locations such as `scripts/`, `tools/`, `app/testing/`, `src/testing/`, or `.github/scripts/`.

Use this skill for normal UI work across repos when you want dense, calm, production-grade product UI instead of generic AI-generated dashboard layouts. This skill is repo-aware first and opinionated about density, hierarchy, and product surfaces second.

If you cannot load the supporting references for some reason, still follow the defaults in this file.

## What This Skill Covers

- Adding a new page, module, settings screen, or workflow step
- Extending existing UI without design drift
- Refactoring bloated or inconsistent screens
- Internal tools, CRUD, admin, ops, and settings screens
- Dense shadcn or Tailwind product UI
- Overview and analytics surfaces with justified charts
- Product-embedded AI conversation UI
- Browser-verified closeout for changed runnable UI surfaces
- Final per-task UI review before stopping

## Anti-Explainer Copy Rule

- Default to zero intro paragraphs on internal tools, operator consoles, approval queues, CRUD pages, dashboards, and settings screens.
- Assume the UI should orient the user through layout, section labels, table headers, badges, tabs, counters, and state chips before it uses prose.
- Treat generic orientation copy such as "this page helps you...", "use this section to...", or "X feeds Y while Z remains authoritative..." as a likely defect unless the user explicitly asked for editorial guidance copy.
- If explanatory copy is truly required, compress it to the smallest possible inline note, usually one short sentence, and only where the action would otherwise be ambiguous.
- Prefer dense labels, empty states, inline helper text, or disclosure patterns over standalone explanatory paragraphs.

## Use the Companion Audit Skill When Needed

If the request is any of the following, use `$ui-deep-audit` instead:

- Full-app UI audit
- Page-by-page UX, design, or readability review
- Writing or refreshing a checkbox audit file
- Working a checklist until every item is complete
- Replying only `ready` when the whole audit backlog is finished

## Required Workflow

1. Inspect the repo first:
   - `package.json`, `components.json`, global styles, tokens, layouts, shell components, and representative screens
   - existing verification commands
2. If shadcn/ui is present or the task is shadcn-oriented, use the official shadcn skill or equivalent project-aware shadcn context first.
3. Load the references you need from this skill package:
   - Always: `references/design-tokens.md`, `references/component-rules.md`, `references/a11y-gates.md`, `references/ui-checklist.md`
   - Dense CRUD or internal-tool UI: `references/dense-product-ui.md`
   - Analytics or overview screens: `references/dashboard-charts.md`
   - AI chat or assistant surfaces: `references/ai-conversation-ui.md`
   - Final review: `references/ui-review.md`
   - Pattern lookup only: `references/ui-examples.md`, `references/ui-anti-patterns.md`
   - Next.js App Router only: `references/nextjs-guardrails.md`
4. Critique the requested UI before generating:
   - density
   - copy volume
   - whether the screen needs any intro copy at all
   - radius
   - hierarchy
   - whether the surface should really be a table, form, chart, chat, or simple detail page
5. Implement with repo primitives:
   - reuse the existing primitive layer
   - preserve existing server or client boundaries
   - keep route files thin
   - extend variants before creating wrappers
6. Run real-browser verification with Playwright whenever the affected UI can run locally:
   - use `$browser-capability` and `$playwright` for the changed or directly affected flows
   - verify the real rendered surface, not just code structure or static screenshots
   - if the Playwright MCP path is locked, stale, or attached to another session, do not stop there
   - fall back to the Playwright CLI wrapper and start a fresh browser session instead
   - if the current app port is busy, unstable, or already occupied, restart the app on another free port and continue the visual pass there
   - use practical repo-native artifacts when helpful, such as screenshots, snapshots, or console output under a repo-local artifact path
7. Review before stopping:
   - run the dense UI checklist
   - run the review reference
   - verify loading, empty, success, error, disabled, desktop, and narrow viewport states
   - remove or compress low-signal explainer copy that the structure already makes obvious
   - report which browser route you used, what you verified, and any remaining unverifiable blockers

## Default Product Posture

- Prefer dense, calm, table-first product UI.
- For module or entity pages, default to a full-width table-first layout.
- Keep one primary action per area.
- Prefer one main task per screen.
- Use compact spacing and compact controls.
- Use restrained titles, short labels, and almost no explanatory copy.
- Default internal and operator surfaces to structure-first communication, not paragraph-first communication.
- Keep charts secondary to the data model.
- Keep AI conversation surfaces compact and product-like, not demo-like.

## Default Density

- Gaps usually `gap-1`, `gap-2`, `gap-3`
- Padding usually `p-2`, `p-3`
- Standard row or control height usually `h-8`
- Icon buttons usually `h-7 w-7` or `h-8 w-8`
- Most text should be `text-sm`
- Metadata can drop to `text-xs`
- Small and medium radius should dominate

## Hard Rules

- Do not force a single visual language across unrelated repos, but do force density and clarity when the task is internal product UI.
- Do not duplicate shadcn guidance locally when project-aware shadcn context already exists.
- Do not add giant hero sections to internal product pages.
- Do not wrap tables and forms in unnecessary cards.
- Do not add long explanatory copy above CRUD tables.
- Do not place generic explainer paragraphs under page titles on operator, dashboard, queue, CRUD, or settings screens.
- Do not add lane descriptions or section blurbs that simply restate the label the user already sees.
- Do not use friendly onboarding copy, "how this works" prose, or policy narration as a substitute for clear structure and status design.
- Do not add charts without analytical reason.
- Do not ship AI chat that feels larger or louder than the rest of the app.
- Do not default to oversized radii, pill buttons, gradient-heavy AI styling, or wrapper piles.
- Do not call runnable UI work done without a real browser pass on the affected surface.
- Do not accept "Playwright was busy" or "the browser MCP was locked" as a stopping point; use the CLI wrapper, a fresh browser session, or another free app port and finish the verification.
- Do not rely on MCP-only browser access when Playwright CLI can complete the same visual pass more reliably.
- Do not stop before checking core states and responsive behavior.

## Preserve and Improve

- Preserve coherent existing patterns.
- Tighten readability, accessibility, and engineering quality.
- If the repo has no coherent system, introduce a restrained one rather than a flashy one.

## References

- `references/design-tokens.md`
- `references/component-rules.md`
- `references/nextjs-guardrails.md` when the repo is Next.js App Router
- `references/a11y-gates.md`
- `references/dense-product-ui.md`
- `references/dashboard-charts.md`
- `references/ai-conversation-ui.md`
- `references/ui-review.md`
- `references/ui-examples.md`
- `references/ui-anti-patterns.md`
- `references/ui-checklist.md`
- `references/prompt-template.md` when the user wants a reusable session prompt

