<!-- agentctl:auto-generated -->
# Agentctl Maintenance

## Last Run

- Generated: `2026-04-18T12:47:01.623783+00:00`
- Status: `ok`
- Checks passed: 19 / 19
- Open findings: 0
- Blocked findings: 0

## When to Run Maintenance

- After changing `agentctl` commands, adapters, or state contracts.
- After changing plugin metadata, plugin skills, or packaging layout.
- After adding or removing supported CLIs or browser routes.
- Before trusting cloud-readiness assumptions for a new workflow.

## Operator Runbook

1. Run `agentctl maintenance check` for a quick signal.
2. If command surface, docs, or packaging changed, run `agentctl maintenance audit`.
3. Read `maintenance.md`, `maintenance-report.json`, and `.codex-workflows/agentctl-maintenance/state.json` together.
4. If findings are doc-only, prefer `agentctl maintenance fix-docs` over hand edits.
5. Re-run the relevant tests and smoke checks before trusting a green maintenance state.

## What Must Be Updated After Changes

- Refresh `docs/agentctl/*.md` from machine state.
- Keep `state-schema.md`, `capability-registry.md`, and `maintenance-contract.md` aligned with code.
- Re-run tests for `agentctl` and the shared workflow tools.
- Keep `AGENTS.md` aligned with the intended front door.

## Clean State Expectations

- `maintenance-report.json` has `status: ok`.
- `.codex-workflows/agentctl-maintenance/state.json` has `status: complete` and `ready_allowed: true`.
- `agentctl doctor` stays compact and health-focused.
- `agentctl capabilities` stays capability-first.
- `agentctl status --all` surfaces durable active workflows and hides stale temp history by default.

## Maintenance Checklist

- [x] No open maintenance findings remain.

## Known Limitations

- `gh skill` is not available locally, so publish/preview wrappers remain disabled.
- `firebase` is detected but intentionally remains detect-only in v1.
- `gcloud` is detected but intentionally remains detect-only in v1.
