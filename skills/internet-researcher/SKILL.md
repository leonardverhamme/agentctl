---
name: internet-researcher
description: Research current information on the public web and synthesize sourced findings. Use when Codex needs up-to-date documentation, release notes, standards, changelogs, API changes, best-practice comparisons, external examples, bug or regression research, or any answer that should be verified against live online sources. Prefer this skill for read-only research and verification tasks before any code changes.
---

# Internet Researcher

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

Use this skill to run fast, source-first internet research and return a compact, current answer with links. Treat it as a lightweight research wrapper around built-in web access, not as a code-changing workflow.

For deterministic CLI-backed output, prefer:

```text
python C:\Users\leona\.codex\agentctl\agentctl.py research web "<query>"
```

Use `C:\Users\leona\.codex\agentctl\references\research-envelope.md` as the shared output contract when the result needs to feed later work.

## Workflow

1. Restate the research question in one sentence before searching.
2. Search primary sources first: official docs, standards bodies, maintainers, release notes, changelogs, vendor docs, or original announcements.
3. Add secondary sources only when they add comparison value, implementation examples, or user-reported context.
4. Check dates, versions, and ownership. If the topic is time-sensitive, state the exact version or publication date you found.
5. Cross-check claims before repeating them as facts. Call out uncertainty when sources disagree or when you are inferring.
6. Return a concise summary with links, not a long transcript of the search process.
7. If built-in web tools are needed for deeper verification, still normalize the final result into the shared `agentctl` research envelope.

## Priorities

- Prefer official documentation over blog posts.
- Prefer current sources over highly ranked but stale results.
- Prefer direct evidence over commentary.
- Prefer 2 to 5 good sources over a noisy link dump.

## Output

Return findings in this shape when the task is broader than a one-line answer:

1. Direct answer or shortlist.
2. Key supporting points with concrete dates, versions, or constraints.
3. Source links for every material claim.
4. Open questions or uncertainty, if any.

## Boundaries

- Stay read-only unless the user separately asks for implementation.
- Do not pretend older cached knowledge is current when the topic can change.
- Do not overquote sources; summarize and link instead.
- Escalate to a browser-capable tool only if the needed information cannot be reached reliably through normal web retrieval.
