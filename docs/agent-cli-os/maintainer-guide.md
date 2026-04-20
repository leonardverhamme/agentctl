# Agent CLI OS Maintainer Guide

Use this when changing the control plane itself.

## Source Of Truth Split

Generated docs:

- `docs/agent-cli-os/overview.md`
- `docs/agent-cli-os/command-map.md`
- `docs/agent-cli-os/inventory.md`
- `docs/agent-cli-os/state-schema.md`
- `docs/agent-cli-os/capability-registry.md`
- `docs/agent-cli-os/cloud-readiness.md`
- `docs/agent-cli-os/maintenance.md`
- `docs/agent-cli-os/maintenance-report.json`

Do not hand-maintain those. Change the code and rerun maintenance.

Hand-maintained docs:

- `README.md`
- `docs/agent-cli-os/zero-touch-setup.md`
- `docs/agent-cli-os/install-on-another-computer.md`
- `docs/agent-cli-os/unattended-worker-setup.md`
- `docs/agent-cli-os/skill-governance.md`
- this file

## Use The Right Runtime

There are two different maintenance targets:

- source repo maintenance
- installed bundle maintenance

Use source repo maintenance when you are changing this repo and want to refresh the checked-in docs:

```powershell
agentcli maintenance audit --json
```

That command now targets the checked-in source tree safely and will not retarget an arbitrary path outside the real Agent CLI OS repo root.

Use installed bundle maintenance when you want to validate a real `CODEX_HOME` install:

```powershell
agentcli maintenance audit
```

Do not confuse those paths. Running the installed bundle audit does not update the docs checked into this repo.

## What To Update

If command surface or routing changes:

- `agentctl/`
- generated docs via `agentcli maintenance audit`
- `README.md`

If install or upgrade logic changes:

- `agentctl/bootstrap.py`
- `agentctl/bundle_install.py`
- `scripts/install_bundle.py`
- `scripts/build_release_bundle.py`
- release workflows
- setup docs

If capability groups or skill front doors change:

- `agentctl/lib/capabilities.py`
- `agentctl/lib/inventory.py`
- generated capability pages
- `AGENTS.md`
- `docs/agent-cli-os/skill-governance.md`
- related tests

If autodetection, menu budgets, or guidance snippets change:

- `agentctl/lib/inventory.py`
- `agentctl/lib/guidance.py`
- `agentctl/lib/self_check.py`
- `agentctl/lib/maintenance.py`
- generated docs via `agentcli maintenance audit`
- related tests

If the generic long-task loop changes:

- `agentctl/agentctl.py`
- `agentctl/lib/workflows.py`
- `workflow-tools/workflow_runner.py`
- `agentctl/codex_worker.py`
- `skills/loopsmith/`
- generated docs via `agentcli maintenance audit`

## Minimum Validation

```powershell
python -m unittest discover -s agentctl/tests -p "test_*.py"
python -m unittest discover -s workflow-tools/tests -p "test_*.py"
agentcli maintenance audit --json
python -m build --sdist --wheel --outdir verify-dist
python scripts/build_release_bundle.py --version v0.0.0-test --output-dir verify-dist
```

For installability:

```powershell
python scripts/install_bundle.py --codex-home <temp dir>
```

## Release Expectations

Tagged releases should:

- build wheel and sdist
- build the `agent-cli-os-bundle-<version>.zip`
- publish GitHub release assets
- publish the Python package to PyPI
- keep bootstrap and upgrade working from released artifacts
- isolate release artifacts in a clean output directory instead of reusing stale `dist/` contents
- fail if legacy-named `loopsmith*` or `agentctl*` release artifacts are about to ship

## Maintainability Contract

- keep the top-level capability menu small
- keep raw inventory separate from the curated menu
- keep personal guidance snippets within budget
- keep thin capability skills short and navigation-first
- put detail in generated pages and docs, not in every `SKILL.md`
- fail maintenance if removed sidecar-app coupling reappears in the product surface

## Less-Is-More Review

Before adding a capability, skill, or menu surface, ask:

- can this stay inside an existing capability group?
- does this need a new visible front door, or only raw inventory coverage?
- will this add routing value, or only more names to the default menu?
- can the detail live in a drill-down page instead of the top-level output?
- should this be user guidance in a snippet directory instead of a longer skill file?

If the answer trends toward "more names, more prose, more default output," do not add it without a stronger justification.

## AGENTS Budget

- keep `AGENTS.md` table-of-contents sized
- use `AGENTS.md` for routing and non-negotiable rules only
- move operational detail into `docs/agent-cli-os/`, generated capability pages, and tests
- if an `AGENTS.md` change mostly adds examples, enumerations, or exceptions, it probably belongs somewhere else

