# agentctl

`agentctl` is a public, capability-first Codex bundle for long-running agent workflows.

It packages:

- `agentctl` as a thin control plane
- reusable skills for UI, testing, docs, refactor, CI/CD, research, and maintenance
- the shared deep-workflow runner and guard
- a local Codex plugin shell for routing and maintenance
- `automation-core`, a local Gmail + Calendar + Notion bridge for CRM-style inbox automation
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
- `plugins/agentctl/`
- `docs/agentctl/`
- `automation-core/`
- `AGENTS.md`
- `config.toml`

Operational docs for the automation bridge live in:

- [automation-core/README.md](automation-core/README.md)
- [docs/automation-core.md](docs/automation-core.md)

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

## automation-core

This repo now also contains a workstation-local automation stack for Gmail, Google Calendar, and Notion:

- local approval UI for pending inbox and meeting decisions
- incremental Gmail and Calendar polling
- Notion technical tables plus business-record updates
- Codex automation entrypoints for hourly sync, briefs, reviews, and hygiene sweeps

Typical operator sequence:

```powershell
cd automation-core
copy .env.example .env
npm install
npm run cli -- schema-bootstrap
npm run dev
```

Then connect Google once:

```text
http://localhost:3010/auth/google/start
```

And run a first manual sync:

```powershell
npm run cli -- job gmail-sync
npm run cli -- job calendar-sync
npm run cli -- job reconcile
```

See [docs/automation-core.md](docs/automation-core.md) for the operator contract and [automation-core/README.md](automation-core/README.md) for the project-local command surface.

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

## Verified Loop Behavior

The deep-workflow loop is verified in the repo, not just described:

- the shared runner reaches `complete` with `ready_allowed=true` when the checklist is fully cleared
- repeated no-progress runs end as `stalled`
- all-blocked checklists end as `blocked`
- `agentctl run ...` is covered end-to-end against the fake worker in a temp repo
- shared registry updates are covered for concurrent deep runs so parallel workflows do not lose entries

The remaining environment-dependent part is a real unattended Codex worker route on the local machine. The deterministic loop is covered; the worker runtime still depends on the machine or cloud environment.

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

It now also verifies the `automation-core` subproject by running:

- `npm --prefix automation-core ci`
- `npm --prefix automation-core run typecheck`
- `npm --prefix automation-core run build`
- `npm --prefix automation-core test`

## Releases

This repo also ships a tag-driven release workflow.

- Push a tag such as `v1.0.0`, or
- run the `Release` workflow manually with a version input

The release workflow:

- reruns the core verification gates
- builds a reproducible `agentctl-<version>.zip` bundle
- writes a matching SHA-256 file
- uploads both as workflow artifacts
- publishes them to the matching GitHub release

## License

MIT. See [LICENSE](LICENSE).
