# Unattended Worker Setup

This guide explains when a deep workflow or generic long-task loop is actually autonomous.

## Real Loop Contract

An unattended deep run requires all of these:

1. a checklist or progress surface in the target repo
2. `.codex-workflows/<workflow>/state.json`
3. the shared runner
4. a real worker command that performs one pass
5. the workflow guard

Without the worker command, the loop is only partially real.

## Supported Worker Paths

`agentcli run <workflow>` and `agentcli loop <name>` can use:

- the auto-detected standalone Codex CLI
- `--worker-command`
- `CODEX_WORKFLOW_WORKER_COMMAND`
- `AGENTCTL_CODEX_WORKER_TEMPLATE`

If the default Codex CLI path is wrong, set:

```powershell
$env:AGENTCTL_CODEX_PATH = "C:\path\to\codex.cmd"
```

## Windows Note

Do not rely on the Windows Store app internals under `WindowsApps` as the worker runtime.

Use the standalone CLI:

```powershell
npm install -g @openai/codex
codex login status
```

Then verify:

```powershell
agentcli doctor
```

If `agentcli` or `loopsmith` is not available on PATH, do not replace the requested run with hand-written progress docs. Run the bundle-local control plane and repair the public launcher first:

```powershell
python "$env:CODEX_HOME\agentctl\agentctl.py" doctor --fix
```

If `CODEX_HOME` is not set, use the default bundle path:

```powershell
python "$HOME\.codex\agentctl\agentctl.py" doctor --fix
```

## Safe First Run

```powershell
agentcli run docs-deep-audit --repo C:\path\to\repo --worker-command "<real worker command>"
agentcli loop repo-cleanup --repo C:\path\to\repo --task "Finish the cleanup in validated batches until the checklist is empty." --worker-command "<real worker command>"
agentcli status --repo C:\path\to\repo --json
```

The run is trustworthy when:

- checklist progress changes
- state.json changes
- the guard can pass only when `ready_allowed` is true
- the workflow ends as `complete`, `blocked`, or `stalled` honestly

## What The Runner Guarantees

- re-reads checklist and state every iteration
- repairs stale machine state from the checklist before trusting terminal status
- scales iteration budget for large checklists
- refuses false `complete`

## What It Does Not Guarantee

- that the worker itself is good
- that chat memory alone can substitute for a worker
- that a packaged app binary is a usable CLI

Subagents belong inside the worker pass, not outside it.

