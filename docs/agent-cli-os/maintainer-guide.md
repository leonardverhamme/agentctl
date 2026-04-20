# Agent CLI OS Maintainer Guide

Use this when changing the control plane itself.

## Source Of Truth Split

Generated docs:

- `docs/agent-cli-os/overview.md`
- `docs/agent-cli-os/command-map.md`
- `docs/agent-cli-os/inventory.md`
- `docs/agent-cli-os/skill-map.md`
- `docs/agent-cli-os/skill-map.pdf`
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
- `docs/agent-cli-os/pypi-publishing.md`
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
- `scripts/check_pypi_release.py`
- setup docs

If capability groups or skill front doors change:

- `agentctl/lib/capabilities.py`
- `agentctl/lib/inventory.py`
- `agentctl/lib/skill_map.py`
- generated capability pages
- generated skill map
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

If skill files stop appearing in the official skills list:

- check `SKILL.md` starts with `---` at byte zero
- remove any UTF-8 BOM before frontmatter
- verify with `npx skills ls -g --json`, not only Agent CLI OS inventory
- remember maintenance now performs a safe mirrored `npx skills ls -g --json` check automatically for the current local skill tree

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

For a real tagged release, also verify the live PyPI version once upload succeeds:

```powershell
python scripts/check_pypi_release.py --package agent-cli-os --version <released-version>
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
- support trusted publishing or a `PYPI_API_TOKEN` fallback when trusted publishing is temporarily unavailable
- keep bootstrap and upgrade working from released artifacts
- isolate release artifacts in a clean output directory instead of reusing stale `dist/` contents
- fail if legacy-named `loopsmith*` or `agentctl*` release artifacts are about to ship
- verify that the released package version becomes visible on live PyPI before the publish phase is treated as complete

## Maintainability Contract

- keep the top-level capability menu small
- keep raw inventory separate from the curated menu
- keep personal guidance snippets within budget
- keep thin capability skills short and navigation-first
- when a front-door skill is actually used, make the assistant mention the literal `$skill-name` once in chat so the human can see the highlighted route
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

