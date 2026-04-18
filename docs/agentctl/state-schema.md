<!-- agentctl:auto-generated -->
# Agentctl State Schema

## Deep Workflow State

The shared deep-workflow schema lives at `agentctl/references/state-schema.md` and is the canonical contract for repo-local workflow state.

## Maintenance Report Schema

The maintenance report is stored at `docs/agentctl/maintenance-report.json` and is mirrored into `.codex-workflows/agentctl-maintenance/state.json`.

Top-level report fields:

- `schema_version`
- `generated_at`
- `root`
- `summary`
- `command_surface`
- `artifacts`
- `docs`
- `references`
- `skills`
- `plugin`
- `tests`
- `cloud_readiness`
- `capabilities_snapshot`
- `known_limitations`
- `findings`

## Lifecycle Semantics

- Repo-local workflow state is canonical; the global registry is only a convenience mirror.
- `ready_allowed` is the completion gate. A workflow must not claim `complete` unless this is `true`.
- `remaining_items` and `blocked_items` should always be derivable from the current checklist, not chat memory.
- `last_validation` should capture the smallest real validation that supports the last completed batch.
- Shared-registry writes must remain concurrency-safe because multiple deep workflows may update the registry at the same time.

## Status Meanings

- `initializing`: state exists but the first meaningful batch has not completed yet.
- `running`: the workflow is active and more work remains.
- `complete`: all tracked work is done and the ready gate passes.
- `blocked`: remaining work exists but a real blocker currently prevents completion.
- `stalled`: repeated attempts failed to make meaningful progress.
- `error`: the state itself is malformed or execution failed before a valid workflow step completed.

## Current Shared Workflow Fields

`agentctl` relies on the shared deep-workflow schema already defined in:

- `../../workflow-tools/workflow_schema.md`

Canonical repo-local state:

- `.codex-workflows/<workflow>/state.json`

Required top-level fields:

- `schema_version`
- `workflow_name`
- `skill_name`
- `repo_root`
- `checklist_path`
- `progress_path`
- `status`
- `iteration`
- `max_iterations`
- `stagnant_iterations`
- `max_stagnant_iterations`
- `tasks_total`
- `tasks_done`
- `tasks_open`
- `tasks_blocked`
- `last_batch`
- `last_validation`
- `last_error`
- `ready_allowed`
- `remaining_items`
- `blocked_items`
- `evidence`

`agentctl status` reads only this shared schema. If it sees an older `state_version` field without `schema_version`, it backfills compatibility in memory but treats `schema_version` as the canonical contract.

## Current Maintenance Summary

```json
{
  "blocked_findings": 0,
  "open_findings": 0,
  "passed_checks": 51,
  "status": "ok",
  "total_checks": 51
}
```
