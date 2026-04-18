# agentctl-platform

`agentctl-platform` is a public, capability-first Codex bundle for long-running agent workflows.

It packages:

- `agentctl` as a thin control plane
- reusable skills for UI, testing, docs, refactor, CI/CD, research, and maintenance
- the shared deep-workflow runner and guard
- a local Codex plugin shell for routing and maintenance
- zero-touch bootstrap plus explicit unattended-worker health checks

The design goal is simple: give coding agents one stable front door for capability discovery, workflow launch, and state tracking without replacing the authoritative tools underneath.

## What It Is

`agentctl` does four things:

1. discovers what capabilities exist and what is healthy
2. routes research through one interface
3. launches and resumes deep, checklist-driven workflows
4. keeps installs and workflow state machine-readable

It does **not** replace:

- the `skills` CLI or `gh skill`
- vendor CLIs such as `gh`, `vercel`, or `supabase`
- Playwright as the browser authority
- Codex itself as the execution engine

## Repo Layout

This repository is structured as a portable `$CODEX_HOME` bundle:

- `agentctl/`
- `workflow-tools/`
- `skills/`
- `plugins/agentctl-platform/`
- `docs/agentctl/`
- `AGENTS.md`
- `config.toml`

## Quick Start

### Option 1: Run from the clone

If you want to work on the bundle directly, set `CODEX_HOME` to the repository root and run `agentctl` from there.

PowerShell:

```powershell
$env:CODEX_HOME = (Get-Location).Path
python .\agentctl\agentctl.py doctor
```

Bash:

```bash
export CODEX_HOME="$PWD"
python3 ./agentctl/agentctl.py doctor
```

### Option 2: Install into your real `$CODEX_HOME`

Run the installer script:

```powershell
python .\scripts\install_bundle.py
```

This is the zero-touch path. It installs the bundle, enables the plugin, runs post-install health checks, and writes a machine-readable bootstrap report under `agentctl/state/bootstrap-report.json`.

By default it installs into:

- Windows: `%USERPROFILE%\\.codex`
- macOS/Linux: `$HOME/.codex`

You can override the target:

```powershell
python .\scripts\install_bundle.py --codex-home C:\Users\you\.codex
```

After install, you can use the generated wrapper or call the Python entrypoint directly:

```powershell
agentctl.cmd doctor
agentctl.cmd capabilities
```

or

```powershell
python %CODEX_HOME%\agentctl\agentctl.py doctor
```

On macOS or Linux:

```bash
sh ./agentctl.sh doctor
```

## Zero-Touch Agent Setup

If you want to hand this bundle to an agent and let it set itself up, use the installer as the single bootstrap command:

```powershell
python .\scripts\install_bundle.py
```

The installed bundle then discovers the already-present skills, plugins, MCP servers, and CLIs on the machine and exposes them through `agentctl` as capabilities.

See [docs/agentctl/zero-touch-setup.md](docs/agentctl/zero-touch-setup.md) for the full bootstrap and script-placement rules.

## Core Commands

```text
agentctl doctor
agentctl capabilities
agentctl status --all
agentctl run <workflow>
agentctl research web <query>
agentctl research github <query>
agentctl research scout <query>
agentctl skills list
agentctl skills add <source>
agentctl skills check
agentctl skills update
agentctl maintenance audit
```

## Deep Workflows

The bundled deep workflows are:

- `ui-deep-audit`
- `test-deep-audit`
- `docs-deep-audit`
- `cicd-deep-audit`
- `refactor-deep-audit`

Each uses repo-local JSON state at:

```text
.codex-workflows/<workflow>/state.json
```

The runner owns repetition, retries, and stop conditions. The skill remains the judgment-heavy worker.

Unattended execution only counts when a real worker runtime exists. Use `--worker-command`, `CODEX_WORKFLOW_WORKER_COMMAND`, or `AGENTCTL_CODEX_WORKER_TEMPLATE` instead of relying on chat repetition.

## Optional Integrations

This repo is intentionally capability-first. Optional integrations are surfaced as capabilities, but they are not treated as baseline failures when missing.

Examples:

- GitHub
- Vercel
- Supabase
- Stripe
- Sentry
- Figma
- Next.js DevTools
- platform-specific iOS/macOS/Android plugins

## Maintenance

Treat `agentctl` as a maintained product.

Use:

```powershell
python .\agentctl\agentctl.py maintenance audit
```

That refreshes:

- `docs/agentctl/*.md`
- `docs/agentctl/maintenance-report.json`
- `.codex-workflows/agentctl-maintenance/state.json`

## Browser Support

`agentctl` keeps Playwright as the browser authority. For full browser-backed verification, ensure a Chromium-compatible browser route is available.

Typical fix:

```powershell
npx playwright install chromium
```

## CI

This repo ships with a GitHub Actions workflow that runs:

- Python source compilation for `agentctl/`, `workflow-tools/`, and `scripts/`
- `agentctl` unit tests
- `workflow-tools` unit tests
- a maintenance audit smoke test in repo-local mode
- an isolated bundle-install smoke test that runs the installed `agentctl`

The CI workflow is manually runnable with `workflow_dispatch` and uses workflow-level concurrency to cancel stale in-progress runs for the same branch or pull request.

## Releases

This repo also ships a tag-driven release workflow.

- Push a tag such as `v1.0.0`, or
- run the `Release` workflow manually with a version input

The release workflow:

- reruns the core verification gates
- builds a reproducible `agentctl-platform-<version>.zip` bundle
- writes a matching SHA-256 file
- uploads both as workflow artifacts
- publishes them to the matching GitHub release

## License

MIT. See [LICENSE](LICENSE).
