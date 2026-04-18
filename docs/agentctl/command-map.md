<!-- agentctl:auto-generated -->
# Agentctl Command Map

This is the frozen v1 command surface that maintenance checks expect.

## Quick Routing Rules

- `doctor` is the shortest health-oriented entrypoint.
- `capabilities` is the full menu for capability discovery.
- `capability <key>` is the drill-down page for a single capability and should be preferred before choosing lower-level vendor tools.
- `status` is for workflow progress, not general health.
- `run` is only for deep workflows that use the shared runner/state contract.
- `run` should prefer a real worker runtime such as Codex CLI or an explicit worker command, not chat-only repetition.
- `research` is for evidence creation, not implementation.
- `skills` wraps official install/update tooling and provenance checks.
- `maintenance` is only for the control plane itself.

## Verification Notes

- `run` is tested at two levels: the shared workflow runner directly and the public `agentctl run` CLI path.
- Shared state transitions are expected to end as `complete`, `blocked`, or `stalled`; `ready_allowed` must gate any `complete` state.
- Shared-registry updates are expected to tolerate concurrent deep workflows without losing entries.

## Core

- `agentctl doctor [--json]`
  - Check installed tools, wrappers, auth health, and browser readiness.
- `agentctl capabilities [--json]`
  - Emit the machine-readable capability inventory and preferred interfaces.
- `agentctl capability <key> [--json]`
  - Show the drill-down page for a single capability.
- `agentctl status [--repo <path>] [--all] [--json]`
  - Inspect repo-local or registry-backed deep workflow state.
- `agentctl run <workflow> [--repo <path>] [--worker-command <cmd>]`
  - Launch or resume a deep workflow through the shared runner.

Typical sequence:

- `agentctl doctor`
- `agentctl capabilities` if you need the full menu
- `agentctl status --all` if you need workflow progress
- `agentctl run <workflow>` only when a deep workflow is the right shape
- If no worker runtime is healthy, configure `--worker-command` or `AGENTCTL_CODEX_WORKER_TEMPLATE` before treating the run as unattended

## Research

- `agentctl research web <query> [--limit N]`
  - Research current public web sources through the shared evidence contract.
- `agentctl research github <query> [--limit N]`
  - Research GitHub repositories, code, issues, and releases through gh-first routing.
- `agentctl research scout <query> [--limit N]`
  - Run web and GitHub research together and merge them into one evidence envelope.

Typical sequence:

- `agentctl research web <query>` for current official docs or standards
- `agentctl research github <query>` for field practice and repository evidence
- `agentctl research scout <query>` when both are needed before implementation

## Skills

- `agentctl skills list [--project] [--json]`
  - List installed skills through the official skills CLI.
- `agentctl skills add <source> [--skill <name>] [--ref <ref>] [--project]`
  - Install skills with provenance recording and optional pinning.
- `agentctl skills check [--project] [--json]`
  - Compare installed skills with the local provenance lock file.
- `agentctl skills update [--project] [--json]`
  - Refresh tracked skills from the lock file without broad unsafe updates.

Typical sequence:

- `agentctl skills list` to inspect current installs
- `agentctl skills check` to inspect provenance and local-vs-external management
- `agentctl skills add ...` only when you are intentionally extending the skill surface

## Maintenance

- `agentctl maintenance check [--json]`
  - Check command/docs/plugin drift and write a machine-readable maintenance report.
- `agentctl maintenance audit [--json]`
  - Run the full maintenance pass, refresh docs, and update maintenance state.
- `agentctl maintenance fix-docs [--json]`
  - Regenerate the human-facing agentctl docs from current machine state.
- `agentctl maintenance render-report [--json]`
  - Render the maintenance Markdown page and JSON report without regenerating every doc.

Typical sequence:

- `agentctl maintenance check` for a quick control-plane inspection
- `agentctl maintenance audit` after code or contract changes
- `agentctl maintenance fix-docs` only when the docs need regeneration without broader change
