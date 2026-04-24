# Install Agent CLI OS On Another Computer

Use this when you want a second machine to end up with a working install, not just a copied folder.

## Recommended Path

```powershell
pipx install git+https://github.com/leonardverhamme/agent-cli-os.git
agentcli bootstrap
agentcli doctor --fix
```

## From A Local Checkout

```powershell
git clone https://github.com/leonardverhamme/agent-cli-os.git
cd agent-cli-os
python .\scripts\install_bundle.py --codex-home C:\Users\you\.codex
```

When that target is the machine's default `CODEX_HOME`, the installer also publishes PATH launcher shims for `agentcli`, `loopsmith`, and `agentctl`.
Use `--publish-shims` if you need the same launcher publishing behavior for a custom `CODEX_HOME`.

Or:

```powershell
agentcli bootstrap --source-root C:\path\to\agent-cli-os
```

## Required Surface

The machine should have:

- Python 3.12+
- Node.js and `npx`

Recommended:

- a Chromium-capable browser route for Playwright-backed work
- optional vendor CLIs such as `gh`, `vercel`, and `supabase`
- optional `graphify` for repo-intel flows
- optional Obsidian for repo-intel vault exports

`Agent CLI OS` will report missing optional tools honestly rather than pretending they are healthy.

## What To Verify

Run:

```powershell
agentcli doctor --fix
agentcli capabilities
agentcli self-check
agentcli maintenance audit
```

Good state:

- install metadata exists at `agentctl/state/install-metadata.json`
- `agentcli` resolves from PATH in a fresh shell
- `maintenance audit` returns `ok`
- generated docs exist under `docs/agent-cli-os/`
- the plugin is enabled
- the grouped capability menu renders cleanly

## Deep Loops

If the second machine must run unattended deep workflows, also configure a real worker route.

See [unattended-worker-setup.md](unattended-worker-setup.md).

## Repo Intel On A New Machine

Repo-intel is not part of the base install contract, but the new machine can enable it after bootstrap:

```powershell
agentcli repo-intel status --repo C:\path\to\repo
agentcli repo-intel ensure --repo C:\path\to\repo
```

Use `agentcli repo-intel audit --all-trusted` after you have marked the machine’s trusted repos in `$CODEX_HOME/config.toml`.


