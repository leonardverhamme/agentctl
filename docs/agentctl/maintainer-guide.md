# Agentctl Maintainer Guide

Use this guide when you are changing `agentctl` itself rather than just using it.

## Audience

This is for people maintaining:

- `agentctl/`
- `workflow-tools/`
- `skills/`
- `plugins/agentctl/`
- `docs/agentctl/`
- the bundle install and release surface

## The Documentation Split

There are two classes of docs in this repo.

### Generated control-plane docs

These are refreshed by `agentctl maintenance audit`:

- `docs/agentctl/overview.md`
- `docs/agentctl/command-map.md`
- `docs/agentctl/state-schema.md`
- `docs/agentctl/capability-registry.md`
- `docs/agentctl/cloud-readiness.md`
- `docs/agentctl/maintenance.md`
- `docs/agentctl/maintenance-report.json`

Do not hand-maintain those as the primary source of truth. Change the underlying code and rerun maintenance.

### Hand-maintained guides

These should be reviewed directly when behavior changes:

- `README.md`
- `docs/agentctl/zero-touch-setup.md`
- `docs/agentctl/install-on-another-computer.md`
- `docs/agentctl/unattended-worker-setup.md`
- `docs/agentctl/skill-governance.md`
- this file
- `docs/automation-core.md`

## What To Update After Common Changes

### If you change command surface or capability routing

Update:

- `agentctl/`
- generated docs via `agentctl maintenance audit`
- `README.md` if the public entry flow changed
- this guide if the operating model changed

### If you change deep workflow contracts

Update:

- `workflow-tools/`
- `agentctl` runtime code that reads workflow state
- generated docs via `agentctl maintenance audit`
- `docs/agentctl/unattended-worker-setup.md`

### If you change install or bundle layout

Update:

- `scripts/install_bundle.py`
- `scripts/build_release_bundle.py`
- `README.md`
- `docs/agentctl/zero-touch-setup.md`
- `docs/agentctl/install-on-another-computer.md`

### If you change CI or release workflows

Update:

- `.github/workflows/*.yml`
- `README.md`
- rerun `$cicd-deep-audit` or refresh the CI/CD checklist if the workflow surface changed materially

### If you change skills or plugin packaging

Update:

- `skills/` or `plugins/agentctl/`
- `AGENTS.md` if the front-door guidance changed
- `docs/agentctl/skill-governance.md` if the skill-governance rules or capability-wrapper policy changed
- generated docs via `agentctl maintenance audit`

## Minimum Validation Before You Trust A Change

Run these from the repo root:

```powershell
python -m unittest discover -s agentctl/tests -p "test_*.py"
python -m unittest discover -s workflow-tools/tests -p "test_*.py"
python .\agentctl\agentctl.py maintenance audit --json
python .\scripts\install_bundle.py --codex-home <temp dir>
```

If the change touches browser-backed verification, also run:

```powershell
$env:AGENTCTL_RUN_BROWSER_SMOKE="1"
$env:AGENTCTL_BROWSER="msedge"
python -m unittest discover -s agentctl/tests -p "test_browser_smoke.py"
```

If the change touches deep runner behavior, also verify:

- a temp-repo `agentctl run <workflow>` smoke
- `workflow-tools/workflow_guard.py --state ... --json`

## Release Expectations

Before tagging a release:

- the reusable verification workflow should reflect the real repo surface
- the release workflow should depend on that same verification workflow
- `scripts/build_release_bundle.py` should build a zip and checksum cleanly
- `scripts/install_bundle.py` should still produce `Post-install checks: ok`

## Installability Expectations On Another Machine

When you change public setup docs or bundle layout, verify:

- the release bundle still contains the required top-level paths
- the installer still writes `agentctl/state/bootstrap-report.json`
- the new machine can run `doctor`, `capabilities`, and `maintenance audit`
- the docs in `docs/agentctl/` still explain how to get to a working control plane

## Deep Loop Expectations

Do not let docs imply that the checklist alone is the loop.

The docs must keep explaining that:

- the runner owns repetition
- the worker command must be real
- the guard owns closeout truth
- repo-local state is the source of truth for progress

If that explanation drifts, fix [unattended-worker-setup.md](unattended-worker-setup.md).

## When To Run The Deep Doc Audit Again

Use `$docs-deep-audit` again when:

- major repo surfaces are added
- install or release flows change materially
- the public story for setup, maintenance, or unattended loops changes
- new operators could get lost by reading only the existing docs

That keeps the doc system durable instead of chat-dependent.
