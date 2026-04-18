---
name: web-github-scout
description: Combine internet research with GitHub research to scout the best external references, examples, and tradeoffs for a technical topic. Use when Codex needs to compare docs plus real-world code, build a shortlist of strong sources, study how teams solve a problem in practice, or produce a compact research brief before implementation.
---

# Web GitHub Scout

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

Use this skill when the task is broader than a single search and needs both official web sources and real-world GitHub evidence. Keep it read-only and synthesis-focused.

For deterministic CLI-backed output, prefer:

```text
python C:\Users\leona\.codex\agentctl\agentctl.py research scout "<query>"
```

Use `C:\Users\leona\.codex\agentctl\references\research-envelope.md` as the shared output contract.

## Workflow

1. Split the topic into two tracks:
   - Web track for official docs, standards, vendor guidance, and current announcements.
   - GitHub track for production-facing examples, issue history, pull requests, and library adoption patterns.
2. Search each track separately before mixing conclusions.
3. Promote only the strongest results into the final shortlist: current, relevant, and directly evidenced.
4. Compare patterns across sources. Distinguish documented best practice from field practice when they differ.
5. Produce a compact brief that helps the next implementation step, but do not implement yet unless the user asks.
6. Keep the web track and GitHub track distinct until the final synthesis, then persist the merged result through the shared `agentctl` research envelope.

## Good Fits

- "Find the best current approaches to solve X in React."
- "Compare official guidance with how open-source projects actually implement this."
- "Find strong repos, docs, and issue threads for this library decision."
- "Scout examples, tradeoffs, and migration notes before we change code."

## Output

Return a brief with:

1. Top sources from the web.
2. Top sources from GitHub.
3. Repeated patterns or disagreements across them.
4. A final shortlist of the best references to use next.

## Boundaries

- Do not dump raw search results.
- Do not collapse official guidance and community practice into one unsupported conclusion.
- Escalate to a browser-capable tool only when a source requires real interaction to inspect.
