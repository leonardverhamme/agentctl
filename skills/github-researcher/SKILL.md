---
name: github-researcher
description: Research GitHub repositories, code, issues, pull requests, discussions, and release history. Use when Codex needs external implementation patterns, library usage examples, maintainer guidance, regression history, popular repositories for a topic, or evidence from open-source projects before recommending or writing code.
---

# GitHub Researcher

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

Use this skill to search GitHub deliberately and summarize the strongest external implementation evidence. Prefer the GitHub connector when available, then `gh` CLI if authenticated, then GitHub web search as a fallback.

For deterministic CLI-backed output, prefer:

```text
python C:\Users\leona\.codex\agentctl\agentctl.py research github "<query>"
```

Use `C:\Users\leona\.codex\agentctl\references\research-envelope.md` as the shared output contract when you need a machine-readable artifact plus a short brief.

## Workflow

1. Define the search target precisely: repositories, code patterns, issues, pull requests, discussions, or releases.
2. Use GitHub-native filters whenever possible: `repo:`, `org:`, `language:`, `path:`, `is:issue`, `is:pr`, or exact-string queries.
3. Prefer upstream repositories, maintained libraries, and primary issue or PR threads over reposted examples.
4. Open the most relevant files, issues, or PRs and capture the exact path, thread, or release link behind each claim.
5. Compare at least a few candidates when the task is evaluative, not just factual.
6. Return a compact shortlist with direct links and why each result matters.
7. When the result should feed later implementation work, persist the final evidence through the shared `agentctl` research envelope instead of returning only free-form notes.

## What To Look For

- Active maintenance: recent commits, releases, or maintainer responses.
- Real adoption: repeated patterns across multiple repositories, not one novelty example.
- Correct scope: examples that match the framework, language, and architectural style the user actually needs.
- Change context: open issues, merged fixes, or release notes that explain why a pattern exists.

## Output

Return findings in this shape when the task is broader than a single link:

1. Best repositories, files, issues, or PRs.
2. The pattern or decision each result demonstrates.
3. Maintenance signals or caveats.
4. Direct GitHub links for every cited result.

## Boundaries

- Stay read-only unless the user asks to clone, patch, or port code.
- Do not confuse stars with quality; inspect actual code and issue history.
- Do not paste long code blocks from third-party repositories when a link and short summary will do.
