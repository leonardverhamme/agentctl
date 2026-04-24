# Agent CLI OS Zero-Touch Setup

Use this when you want an agent or operator to get to a working install with the fewest possible steps.

## Fast Path

```powershell
pipx install git+https://github.com/leonardverhamme/agent-cli-os.git
agentcli bootstrap
agentcli doctor --fix
```

That is the canonical public setup path.

When the PyPI project is live, this becomes the public one-liner:

```powershell
pipx install agent-cli-os
```

The one-time maintainer setup for that path is tracked in [pypi-publishing.md](pypi-publishing.md).

## What Bootstrap Does

- installs the bundle into `CODEX_HOME`
- keeps the internal bundle under `agentctl/`
- enables the `agent-cli-os` plugin in `config.toml`
- publishes PATH launcher shims for `agentcli`, `loopsmith`, and `agentctl` when targeting the default `CODEX_HOME`
- writes install metadata to `agentctl/state/install-metadata.json`
- runs post-install checks against the exact target `CODEX_HOME`

On Windows, launcher publishing prefers an existing user-writable PATH directory such as `%APPDATA%\Python\Scripts`, then falls back to other common user launcher locations.

Post-install checks include:

- `agentcli doctor --json`
- `agentcli capabilities --json`
- `agentcli maintenance audit --json`
- `agentcli self-check --json`

## Local Development Bootstrap

If you are working from a local checkout:

```powershell
agentcli bootstrap --source-root C:\path\to\agent-cli-os
```

Use `--source-root` only for local development. Public installs should prefer release artifacts.

## After Bootstrap

Run:

```powershell
agentcli doctor --fix
agentcli capabilities
agentcli self-check
```

The install is in good shape when:

- `doctor` reports `ok` or only documented optional degradation
- `capabilities` shows the grouped top-level menu
- `self-check` reports matching wrapper, bundle, and config health
- `docs/agent-cli-os/maintenance-report.json` exists in `CODEX_HOME`

## Config Layers

`Agent CLI OS` uses:

1. bundled defaults
2. `$CODEX_HOME/config.toml`
3. `<repo>/.agent-cli-os/config.toml`

Use `agentcli config show` to inspect the merged result.

## Worker Runtime

Deep workflows only count as unattended when a real worker route exists.

Use one of:

- the auto-detected Codex CLI
- `--worker-command`
- `CODEX_WORKFLOW_WORKER_COMMAND`
- `AGENTCTL_CODEX_WORKER_TEMPLATE`

Read [unattended-worker-setup.md](unattended-worker-setup.md) before treating deep loops as fully autonomous.

## Script Placement Rule

Task-specific helper scripts belong in the target repo being worked on.

They do not belong in:

- `CODEX_HOME`
- the `Agent CLI OS` bundle repo unless it is the active target repo
- `skills/`
- `plugins/*/skills/`

## Optional Repo Intel Runtime

Base bootstrap does not require Graphify or Obsidian.

If you want repo-intel after bootstrap:

```powershell
agentcli repo-intel status --repo C:\path\to\repo
agentcli repo-intel ensure --repo C:\path\to\repo
agentcli repo-intel audit --all-trusted
```

That keeps the contract clean:

- Graphify is optional and detected as an external runtime
- Agent CLI OS owns the repo-intel manifest and workspace registry
- Obsidian export is optional and does not block the base install


