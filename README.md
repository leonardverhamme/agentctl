# Agent CLI OS

`Agent CLI OS` is a capability-first Codex control plane for long-running agent work.
`OS` stands for `On Steroids`, not operating system.

It gives agents one stable front door for:

- capability discovery
- deep workflow launch and resume
- research routing
- install health
- upgrade and maintenance

It does not replace the authoritative tools underneath. It routes into them.

## 5-Minute Setup

Install the public wrapper:

```powershell
pipx install agent-cli-os
```

Bootstrap the real bundle into your `CODEX_HOME`:

```powershell
agentcli bootstrap
```

Repair common setup issues and confirm health:

```powershell
agentcli doctor --fix
```

That is the main onboarding path.

`agentcli` is the canonical public command. `loopsmith` still works as a compatibility alias for the current migration release.

## What You Get

- `agentcli` as the public wrapper command
- the internal `agentctl/` bundle under `CODEX_HOME`
- reusable local skills for UI, tests, docs, refactor, CI/CD, research, and maintenance
- a local plugin shell for Codex routing
- deep workflow state under `.codex-workflows/<workflow>/state.json`

## Core Commands

```text
agentcli doctor --fix
agentcli capabilities
agentcli capability <key>
agentcli skill-map
agentcli inventory show
agentcli status --all
agentcli run <workflow>
agentcli loop <name> --task "<brief>"
agentcli research web <query>
agentcli research github <query>
agentcli research scout <query>
agentcli config show
agentcli self-check
agentcli upgrade
agentcli maintenance audit
```

## Examples

Install on the current machine:

```powershell
pipx install agent-cli-os
agentcli bootstrap
agentcli doctor --fix
```

Install on another computer from a local checkout:

```powershell
git clone https://github.com/leonardverhamme/agent-cli-os.git
cd agent-cli-os
python .\scripts\install_bundle.py --codex-home C:\Users\you\.codex
```

Bootstrap from a local checkout during development:

```powershell
agentcli bootstrap --source-root C:\path\to\agent-cli-os
```

Run a deep workflow:

```powershell
agentcli run docs-deep-audit --repo C:\path\to\repo
```

Run a generic long task through the durable loop:

```powershell
agentcli loop repo-cleanup --repo C:\path\to\repo --task "Reduce stale scripts, tighten docs, add missing tests, and keep going until the checklist is empty."
```

Upgrade later:

```powershell
agentcli upgrade
agentcli self-check
```

## Config Layers

`Agent CLI OS` uses a small structured config system with clear precedence:

1. bundled defaults
2. user-global config at `$CODEX_HOME/config.toml`
3. repo-local config at `<repo>/.agent-cli-os/config.toml`

Use:

```powershell
agentcli config show
agentcli config path --scope user
agentcli config set worker.mode auto
agentcli config set browser.preferred_route cli --scope repo --repo C:\path\to\repo
agentcli config unset browser.preferred_route --scope repo --repo C:\path\to\repo
```

Structured config is intentionally small. Use `AGENTS.md` for natural-language guidance.

Default structured keys now cover:

- worker runtime defaults
- browser route preference
- compact menu behavior
- raw inventory refresh behavior
- personal guidance snippet directories and budgets

## Grouped Capability Navigation

The default capability menu is grouped so the top-level surface stays small:

- Core
- Workflows
- Research
- Platforms
- Browser & Design
- Native

Use:

```powershell
agentcli capabilities
agentcli skill-map
agentcli capability platforms
agentcli capability github-advanced-security
agentcli inventory show --kind tools --scope all
```

`agentcli capabilities` is the curated compact front door.

`agentcli skill-map` writes the human-facing menu and skill map to `docs/agent-cli-os/skill-map.md` and the matching one-page PDF to `docs/agent-cli-os/skill-map.pdf`.

`agentcli inventory show` is the raw autodetected surface for debugging and inspection when the curated menu is not enough.

The detailed routing notes live in generated capability pages under `docs/agent-cli-os/capabilities/`.

Default menu budgets:

- max 8 top-level groups
- max 25 items per menu bucket before deterministic splitting
- names-first output by default

## Why This Stays Small

`Agent CLI OS` is intentionally split into three layers:

- raw autodetected inventory
- curated capability menu
- thin visible front-door skills

That separation is the main token-efficiency rule.

It prevents the default route from becoming a giant flat dump of:

- every installed skill
- every plugin-contributed skill
- every MCP server
- every CLI on the machine

The default menu stays compact because:

- newly detected tools are not promoted automatically
- raw inventory lives behind `agentcli inventory show`
- top-level output is names-first instead of paragraph-first
- personal guidance is budgeted instead of appended into skills
- thin skills stay navigation-first and push detail into docs and drill-down pages

## Raw Inventory

`Agent CLI OS` now persists the raw autodetected inventory to:

```text
agentctl/state/inventory.json
```

That snapshot includes:

- machine CLIs
- globally installed skills
- repo-scoped skills when present
- installed/configured plugins
- configured MCP servers

Use:

```powershell
agentcli inventory refresh
agentcli inventory show --kind all --scope all
agentcli inventory item tool:gh
```

This is intentionally separate from the curated capability menu.

## Personal Guidance Snippets

Small personal guidance snippets can now be referenced through structured config instead of bloating skills or prompts.

By default, `Agent CLI OS` validates:

- max guidance files
- max total guidance lines

The compact guidance snapshot is stored at:

```text
agentctl/state/guidance.json
```

This keeps private user preferences out of:

- capability skills
- repo skills
- giant inline config blobs

The goal is better routing with less prompt clutter, not another hidden prompt dump.

## Skill Surface

The important distinction is:

- local front-door skills such as `$ui-skill`, `$ui-deep-audit`, `$context-skill`, `$docs-skill`, and `$test-skill`
- curated plugin skills that also appear in the Codex `$` picker

That is why the `$` picker is much larger than the compact `agentcli capabilities` menu.

When an agent actively routes through one of those local front-door skills, it should mention the literal `$skill-name` once in chat so the human can see the highlighted skill route immediately.

If the desktop app still shows an old `$` list after a bundle sync, open a new thread or restart the app. The active session can keep a stale skill index even when the files on disk are already correct.

Use:

```powershell
agentcli skill-map
agentcli capability ui-workflows
agentcli capability context-workflows
agentcli inventory show --kind skills
```

For intentional skill-system work, use `$editskill`. The older `$skill-edit-mode` name remains as a legacy alias.

## Deep Workflows

Bundled deep workflows:

- `ui-deep-audit`
- `test-deep-audit`
- `docs-deep-audit`
- `cicd-deep-audit`
- `refactor-deep-audit`

Each workflow is disk-backed:

- checklist or progress markdown in the target repo
- machine state in `.codex-workflows/<workflow>/state.json`

For unattended execution, the loop still needs a real worker route. `Agent CLI OS` supports:

- `--worker-command`
- `CODEX_WORKFLOW_WORKER_COMMAND`
- `AGENTCTL_CODEX_WORKER_TEMPLATE`
- a callable standalone Codex CLI when auto-detected

When there is no dedicated deep workflow for the job, use the generic `$loopsmith` skill plus:

```powershell
agentcli loop <name> --repo C:\path\to\repo --task "<brief>"
```

That loop uses the same runner contract, but stores its queue under `docs/<name>-checklist.md`, `docs/<name>-progress.md`, and `.codex-workflows/<name>/state.json`.

## Install and Upgrade Model

The public wrapper is installable as a Python package.

The real bundle is installed into `CODEX_HOME` by `agentcli bootstrap` and upgraded by `agentcli upgrade`.

Install metadata is written to:

```text
agentctl/state/install-metadata.json
```

That metadata lets upgrades use the recorded source and version channel instead of guessing.

## Compatibility

This release intentionally keeps:

- the internal Python package name as `agentctl`
- the internal bundle directory as `agentctl/`
- `agentctl` as a hidden compatibility command alias

That keeps existing installs and repo assumptions stable while the public product name changes to `Agent CLI OS`.

## Documentation Map

- [docs/agent-cli-os/overview.md](docs/agent-cli-os/overview.md)
- [docs/agent-cli-os/zero-touch-setup.md](docs/agent-cli-os/zero-touch-setup.md)
- [docs/agent-cli-os/install-on-another-computer.md](docs/agent-cli-os/install-on-another-computer.md)
- [docs/agent-cli-os/unattended-worker-setup.md](docs/agent-cli-os/unattended-worker-setup.md)
- [docs/agent-cli-os/maintainer-guide.md](docs/agent-cli-os/maintainer-guide.md)
- [docs/agent-cli-os/pypi-publishing.md](docs/agent-cli-os/pypi-publishing.md)
- [docs/agent-cli-os/skill-governance.md](docs/agent-cli-os/skill-governance.md)
- [docs/agent-cli-os/inventory.md](docs/agent-cli-os/inventory.md)
- [docs/agent-cli-os/skill-map.md](docs/agent-cli-os/skill-map.md)

## Release Model

- Python package: `agent-cli-os`
- canonical repo: `https://github.com/leonardverhamme/agent-cli-os`
- GitHub Releases carry the versioned bundle zip used by `bootstrap` and `upgrade`
- tagged releases are configured to build wheel, sdist, bundle zip, checksum, and publish to PyPI
- tagged releases now wait for the package version to appear on live PyPI before calling the publish step complete
- verify live PyPI availability for each release instead of assuming the publish step already succeeded

## Maintenance

Treat the control plane as a maintained product:

```powershell
agentcli maintenance audit
agentcli self-check
```

The maintenance pass refreshes generated docs, checks plugin/config health, enforces grouped-menu budgets, and blocks reintroduced sidecar-app coupling in the product surface.

When changing the source repo itself, run maintenance from the source tree, not through an already installed bundle:

```powershell
agentcli maintenance audit --json
```

That source-tree command now refreshes the checked-in docs directly and refuses to retarget maintenance writes outside the real Agent CLI OS repo root.
