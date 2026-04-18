# Unattended Worker Setup

This is the guide that explains how the deep workflow loop really works and what must be configured before you can trust `agentctl run <workflow>` to keep going without repeated chat prompts.

## The Real Loop Contract

The loop is not "keep asking the model again."

The loop is:

1. a checklist file for the human queue
2. a repo-local JSON state file for the machine queue
3. the shared workflow runner for repetition and retry logic
4. a real worker command that performs one pass
5. the workflow guard that blocks false `ready`

If any one of those is missing, the loop is only partially real.

## What Lives Where

For a workflow such as `docs-deep-audit`:

- checklist: `docs/docs-deep-audit-checklist.md`
- state: `.codex-workflows/docs-deep-audit/state.json`
- runner: `workflow-tools/workflow_runner.py`
- guard: `workflow-tools/workflow_guard.py`

The checklist is for people.

The state file is for the runner.

The runner is the outer loop.

The worker command is the thing that actually performs one new batch of work.

## What Counts As A Real Worker

A real worker command is anything that can execute one actual deep-workflow pass in the target repo.

Examples of valid shapes:

- a repo-local script that launches one Codex pass
- a Codex CLI wrapper that runs one deep-skill prompt
- a cloud worker command that performs one pass and exits

What does **not** count:

- re-reading the checklist without changing the repo
- a shell loop with no worker command
- chat memory by itself

## Supported Configuration Paths

`agentctl run <workflow>` supports three ways to get a worker:

- let `agentctl` use the built-in Codex worker wrapper when the Codex runtime is callable
- pass `--worker-command "<real command>"`
- set `CODEX_WORKFLOW_WORKER_COMMAND`
- set `AGENTCTL_CODEX_WORKER_TEMPLATE`

If the machine has a working Codex CLI at a non-default path, point `AGENTCTL_CODEX_PATH` at it so the built-in wrapper can use it.

The first path is the most explicit and easiest to verify.

### Windows note

On Windows, do not rely on the Microsoft Store Codex app's internal `WindowsApps` binaries as the worker runtime. They are packaged app internals and may exist on disk while still failing with `Access is denied` when called from a shell.

Use the standalone Codex CLI instead:

```powershell
npm install -g @openai/codex
setx AGENTCTL_CODEX_PATH "C:\Users\<you>\AppData\Roaming\npm\codex.cmd"
```

After installing, verify:

```powershell
codex --version
codex login status
agentctl.cmd doctor
```

## Recommended Order

### 1. Verify the control plane first

```powershell
agentctl.cmd doctor
agentctl.cmd capabilities
```

If `doctor` says the autonomous deep-run route is degraded, do not assume the loop can keep running unattended yet. Fix the worker route first instead of treating manual chat batches as "still running."

### 2. Choose a workflow

Examples:

- `ui-deep-audit`
- `test-deep-audit`
- `docs-deep-audit`
- `cicd-deep-audit`
- `refactor-deep-audit`

### 3. Provide a real worker command

The safest pattern is explicit:

```powershell
agentctl.cmd run docs-deep-audit --repo C:\path\to\repo --worker-command "<your real worker command>"
```

If you want the repo or machine to keep using the same worker command, set an environment variable instead.

Current-session PowerShell example:

```powershell
$env:CODEX_WORKFLOW_WORKER_COMMAND = "<your real worker command>"
agentctl.cmd run docs-deep-audit --repo C:\path\to\repo
```

Use `AGENTCTL_CODEX_WORKER_TEMPLATE` only when you have a machine-specific Codex runtime shape that is already proven locally.

Use `AGENTCTL_CODEX_PATH` when the default Codex detection is wrong but you do have a callable Codex CLI:

```powershell
$env:AGENTCTL_CODEX_PATH = "C:\path\to\codex.exe"
agentctl.cmd run ui-deep-audit --repo C:\path\to\repo
```

## What The Runner Guarantees

Once a real worker command exists, the runner guarantees:

- it re-reads the checklist and state every iteration
- it repairs stale machine state from the checklist before trusting terminal status
- it scales the iteration budget upward for very large checklists instead of blindly dying at the default cap
- it updates progress after each batch
- it stops as `complete` only when the guard passes
- it stops as `blocked` or `stalled` when progress is no longer real
- it does not trust chat claims of completion

## What The Guard Enforces

The guard checks:

- checklist counts match the state file
- `tasks_open == 0` before `complete`
- blocked or stalled states are surfaced honestly
- `ready_allowed` is only true when the workflow is actually done

You can inspect the guard directly:

```powershell
python .\workflow-tools\workflow_guard.py --state .codex-workflows\docs-deep-audit\state.json --json
```

## How To Observe Progress

Use:

```powershell
agentctl.cmd status --repo C:\path\to\repo --json
```

or open:

- `.codex-workflows/<workflow>/state.json`
- `docs/<workflow>-progress.md`
- `docs/<workflow>-checklist.md`

If those disagree, trust the state and checklist, not prior chat text.

## Typical Failure Modes

### No worker configured

Symptom:

- `agentctl run ...` stops immediately and reports no worker command is configured

Fix:

- supply `--worker-command`
- or set `CODEX_WORKFLOW_WORKER_COMMAND`
- or set `AGENTCTL_CODEX_WORKER_TEMPLATE`

### The loop keeps running but makes no progress

Symptom:

- workflow ends as `stalled`

Meaning:

- the worker ran, but it did not clear or advance meaningful checklist items

Fix:

- inspect the checklist and last batch
- fix the worker prompt or worker command
- rerun with a worker that can actually change the repo and validate the result

### Everything is blocked

Symptom:

- workflow ends as `blocked`

Meaning:

- the remaining unchecked items are all real blockers

Fix:

- resolve the external blocker
- or reduce the checklist to items that are actually actionable now

## Subagents Fit Inside The Worker, Not Outside It

If you use subagents, use them inside the worker pass for independent batches.

Do not replace the outer runner loop with subagents.

The correct shape is:

- `agentctl run` owns repetition
- the worker command owns one pass
- subagents, if used, belong inside that one pass

## Good Final State

You can trust unattended deep loops when all of these are true:

- `agentctl doctor` reports the runtime honestly
- a real worker command is configured
- `agentctl run <workflow>` moves real checklist items without chat help
- `agentctl status` reflects that progress in repo-local state
- `workflow_guard.py` returns exit code `0` only when the checklist is truly done
