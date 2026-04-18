---
name: "playwright"
description: "Use when the task requires automating a real browser from the terminal (navigation, form filling, snapshots, screenshots, data extraction, UI-flow debugging) via `playwright-cli` or the bundled wrapper script."
---


# Playwright CLI Skill

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill's files during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself.
- Even then, do not edit immediately. First ask for explicit confirmation to open `skill-edit-mode` for the named skill or skills.
- If that confirmation is absent, refuse the skill-file edit and continue with non-skill work.

## Repo Artifact Rule

- If browser automation needs helper scripts, snapshots, or saved artifacts, put them in the target repo, not in `$CODEX_HOME`, not in a skill folder, and not in the agentctl bundle unless that bundle repo is the target.
- Prefer repo-native locations such as `output/playwright/`, `artifacts/browser/`, `tmp/browser/`, or `scripts/`.

Drive a real browser from the terminal using `playwright-cli`. Prefer the `playwright.cmd` wrapper when it is on `PATH`; if the current repo bundles agentctl, use the bundle-local `agentctl/playwright.cmd`.
Treat this skill as CLI-first automation. Do not pivot to `@playwright/test` unless the user explicitly asks for test files.

## Prerequisite check (required)

Before proposing commands, check whether `npx` is available (the wrapper depends on it):

```bash
command -v npx >/dev/null 2>&1
```

If it is not available, pause and ask the user to install Node.js/npm (which provides `npx`). Provide these steps verbatim:

```bash
# Verify Node/npm are installed
node --version
npm --version

# If missing, install Node.js/npm, then:
npm install -g @playwright/cli@latest
playwright-cli --help
```

Once `npx` is present, proceed with the wrapper script. A global install of `playwright-cli` is optional.

## Skill path (set once)

PowerShell / Windows:

```powershell
$env:PWCLI = if (Get-Command playwright.cmd -ErrorAction SilentlyContinue) {
  "playwright.cmd"
} elseif (Test-Path ".\\agentctl\\playwright.cmd") {
  (Resolve-Path ".\\agentctl\\playwright.cmd").Path
} elseif ($env:CODEX_HOME -and (Test-Path (Join-Path $env:CODEX_HOME "agentctl\\playwright.cmd"))) {
  (Join-Path $env:CODEX_HOME "agentctl\\playwright.cmd")
} else {
  throw "No playwright wrapper found on PATH, in ./agentctl, or in `$CODEX_HOME\\agentctl."
}
```

Fallback Bash path:

```bash
if command -v playwright.cmd >/dev/null 2>&1; then
  export PWCLI="playwright.cmd"
elif [ -x "./skills/playwright/scripts/playwright_cli.sh" ]; then
  export PWCLI="./skills/playwright/scripts/playwright_cli.sh"
else
  export PWCLI="./agentctl/playwright.cmd"
fi
```

## Quick start

Use the preferred wrapper:

```bash
"$PWCLI" open https://playwright.dev --headed
"$PWCLI" snapshot
"$PWCLI" click e15
"$PWCLI" type "Playwright"
"$PWCLI" press Enter
"$PWCLI" screenshot
```

If the user prefers a global install, this is also valid:

```bash
npm install -g @playwright/cli@latest
playwright-cli --help
```

## Core workflow

1. Open the page.
2. Snapshot to get stable element refs.
3. Interact using refs from the latest snapshot.
4. Re-snapshot after navigation or significant DOM changes.
5. Capture artifacts (screenshot, pdf, traces) when useful.
6. If the browser route is locked, stale, or attached to another session, start a fresh CLI session instead of stopping.
7. If the current app port is unavailable or already occupied, rerun the app on another free port and continue the browser pass there.

Minimal loop:

```bash
"$PWCLI" open https://example.com
"$PWCLI" snapshot
"$PWCLI" click e3
"$PWCLI" snapshot
```

## When to snapshot again

Snapshot again after:

- navigation
- clicking elements that change the UI substantially
- opening/closing modals or menus
- tab switches

Refs can go stale. When a command fails due to a missing ref, snapshot again.

## Recommended patterns

### Form fill and submit

```bash
"$PWCLI" open https://example.com/form
"$PWCLI" snapshot
"$PWCLI" fill e1 "user@example.com"
"$PWCLI" fill e2 "password123"
"$PWCLI" click e3
"$PWCLI" snapshot
```

### Debug a UI flow with traces

```bash
"$PWCLI" open https://example.com --headed
"$PWCLI" tracing-start
# ...interactions...
"$PWCLI" tracing-stop
```

### Multi-tab work

```bash
"$PWCLI" tab-new https://example.com
"$PWCLI" tab-list
"$PWCLI" tab-select 0
"$PWCLI" snapshot
```

## Wrapper script

The preferred global wrapper uses `npx --package @playwright/cli playwright-cli` through:

```text
playwright.cmd
```

If the repo bundles agentctl, the equivalent bundle-local path is `agentctl/playwright.cmd`. The legacy Bash skill wrapper still exists for shells that prefer it.

```bash
"$PWCLI" --help
```

Prefer the wrapper unless the repository already standardizes on a global install.

## References

Open only what you need:

- CLI command reference: `references/cli.md`
- Practical workflows and troubleshooting: `references/workflows.md`

## Guardrails

- Always snapshot before referencing element ids like `e12`.
- Re-snapshot when refs seem stale.
- Prefer explicit commands over `eval` and `run-code` unless needed.
- When you do not have a fresh snapshot, use placeholder refs like `eX` and say why; do not bypass refs with `run-code`.
- Use `--headed` when a visual check will help.
- When capturing artifacts in this repo, use `output/playwright/` and avoid introducing new top-level artifact folders.
- Default to CLI commands and workflows, not Playwright test specs.
- Do not stop because another Playwright session has the MCP/browser route locked; open a fresh CLI-driven browser session and continue.
- Do not treat the first chosen localhost port as fixed; if the app is runnable and the port is blocked, switch to another free port and finish the verification.
