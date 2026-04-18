from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from workflow_common import (
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_MAX_STAGNANT_ITERATIONS,
    append_evidence,
    default_checklist_path,
    default_progress_path,
    derive_last_batch,
    ensure_parent,
    load_or_initialize_state,
    meaningful_progress,
    parse_checklist,
    render_progress_markdown,
    save_json,
    sync_state_from_checklist,
    update_registry,
    utc_now,
    validate_state_payload,
    workflow_state_path,
)
from workflow_guard import evaluate_guard


GLOBAL_REGISTRY = Path(r"../workflow-state/registry.json")


def build_retry_hint(state: dict, checklist: dict, *, worker_rc: int | None = None, guard_message: str | None = None) -> str:
    remaining_titles = [item["title"] for item in checklist["remaining_items"][:10]]
    blocked_titles = [item["title"] for item in checklist["blocked_items"][:10]]
    hint_lines = [
        f"Workflow: {state['workflow_name']}",
        f"Iteration: {state['iteration']}",
        f"Remaining unchecked items: {checklist['open']}",
        f"Blocked items: {checklist['blocked']}",
    ]
    if remaining_titles:
        hint_lines.append("Top remaining items:")
        hint_lines.extend(f"- {title}" for title in remaining_titles)
    if blocked_titles:
        hint_lines.append("Currently blocked items:")
        hint_lines.extend(f"- {title}" for title in blocked_titles)
    if state.get("last_batch"):
        hint_lines.append("Last batch:")
        hint_lines.extend(f"- {entry}" for entry in state["last_batch"])
    if worker_rc not in (None, 0):
        hint_lines.append(f"Last worker exit code: {worker_rc}")
    if guard_message:
        hint_lines.append(f"Last guard result: {guard_message}")
    hint_lines.append("Try another way. Do not repeat the same failed approach. Update checklist and workflow state after the next batch.")
    return "\n".join(hint_lines)


def persist_state(state_path: Path, state: dict, registry_path: Path, render: bool = True) -> None:
    save_json(state_path, state)
    update_registry(registry_path, state)
    if render:
        checklist = parse_checklist(state["checklist_path"])
        progress = render_progress_markdown(state, checklist)
        ensure_parent(state["progress_path"]).write_text(progress, encoding="utf-8")


def determine_worker_command(cli_value: str | None) -> str | None:
    return cli_value or os.environ.get("CODEX_WORKFLOW_WORKER_COMMAND")


def main() -> int:
    parser = argparse.ArgumentParser(description="Shared runner for deep-skill workflows.")
    parser.add_argument("--skill", required=True, help="Deep skill name, e.g. ui-deep-audit")
    parser.add_argument("--repo", required=True, help="Repository root")
    parser.add_argument("--checklist", help="Optional checklist path")
    parser.add_argument("--progress", help="Optional progress markdown path")
    parser.add_argument("--max-iterations", type=int, default=DEFAULT_MAX_ITERATIONS)
    parser.add_argument("--max-stagnant", type=int, default=DEFAULT_MAX_STAGNANT_ITERATIONS)
    parser.add_argument("--worker-command", help="Shell command used to run one deep-skill pass")
    parser.add_argument("--worker-mode", choices=("auto", "explicit", "codex"), default="auto", help="How the caller resolved the worker command")
    parser.add_argument("--registry", help="Optional override for the global registry path")
    parser.add_argument("--state", help="Optional override for the repo-local workflow state path")
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    workflow_name = args.skill
    checklist_path = Path(args.checklist).resolve() if args.checklist else default_checklist_path(repo_root, args.skill)
    progress_path = Path(args.progress).resolve() if args.progress else default_progress_path(repo_root, args.skill)
    state_path = Path(args.state).resolve() if args.state else workflow_state_path(repo_root, workflow_name)
    registry_path = Path(args.registry).resolve() if args.registry else GLOBAL_REGISTRY
    worker_command = determine_worker_command(args.worker_command)

    state = load_or_initialize_state(
        state_path=state_path,
        workflow_name=workflow_name,
        skill_name=args.skill,
        repo_root=repo_root,
        checklist_path=checklist_path,
        progress_path=progress_path,
        max_iterations=args.max_iterations,
        max_stagnant_iterations=args.max_stagnant,
        worker_command=worker_command,
    )
    validation_errors = validate_state_payload(state)
    if validation_errors:
        state["status"] = "error"
        state["last_error"] = {"timestamp": utc_now(), "message": "; ".join(validation_errors)}
        persist_state(state_path, state, registry_path)
        print(state["last_error"]["message"])
        return 3

    if not worker_command:
        state["status"] = "blocked"
        state["last_error"] = {
            "timestamp": utc_now(),
            "message": (
                "no worker command configured; pass --worker-command, set CODEX_WORKFLOW_WORKER_COMMAND, "
                "or configure AGENTCTL_CODEX_WORKER_TEMPLATE for codex-backed deep runs"
            ),
        }
        state["worker_mode"] = args.worker_mode
        persist_state(state_path, state, registry_path)
        print(state["last_error"]["message"])
        return 2

    state["worker_command"] = worker_command
    state["worker_mode"] = args.worker_mode
    persist_state(state_path, state, registry_path)

    while True:
        state = load_or_initialize_state(
            state_path=state_path,
            workflow_name=workflow_name,
            skill_name=args.skill,
            repo_root=repo_root,
            checklist_path=checklist_path,
            progress_path=progress_path,
            max_iterations=args.max_iterations,
            max_stagnant_iterations=args.max_stagnant,
            worker_command=worker_command,
        )

        before = parse_checklist(state["checklist_path"])
        if state["iteration"] >= state["max_iterations"]:
            state["status"] = "stalled"
            state["last_error"] = {
                "timestamp": utc_now(),
                "message": f"maximum iterations reached ({state['max_iterations']})",
            }
            persist_state(state_path, state, registry_path)
            print(state["last_error"]["message"])
            return 2

        state["iteration"] += 1
        state["status"] = "running"
        retry_hint = build_retry_hint(state, before)
        env = os.environ.copy()
        env.update(
            {
                "CODEX_WORKFLOW_STATE": str(state_path),
                "CODEX_WORKFLOW_CHECKLIST": str(checklist_path),
                "CODEX_WORKFLOW_PROGRESS": str(progress_path),
                "CODEX_WORKFLOW_SKILL": args.skill,
                "CODEX_WORKFLOW_REPO": str(repo_root),
                "CODEX_WORKFLOW_ITERATION": str(state["iteration"]),
                "CODEX_WORKFLOW_RETRY_HINT": retry_hint,
            }
        )
        persist_state(state_path, state, registry_path)

        result = subprocess.run(
            worker_command,
            cwd=str(repo_root),
            env=env,
            shell=True,
            capture_output=True,
            text=True,
        )

        state = load_or_initialize_state(
            state_path=state_path,
            workflow_name=workflow_name,
            skill_name=args.skill,
            repo_root=repo_root,
            checklist_path=checklist_path,
            progress_path=progress_path,
            max_iterations=args.max_iterations,
            max_stagnant_iterations=args.max_stagnant,
            worker_command=worker_command,
        )
        after = parse_checklist(state["checklist_path"])
        progress_made = meaningful_progress(before, after)
        state["stagnant_iterations"] = 0 if progress_made else state.get("stagnant_iterations", 0) + 1
        state = sync_state_from_checklist(
            state,
            after,
            status="running",
            last_batch=derive_last_batch(before, after),
            last_validation={
                "timestamp": utc_now(),
                "worker_exit_code": result.returncode,
                "worker_stdout_tail": result.stdout[-1000:],
                "worker_stderr_tail": result.stderr[-1000:],
            },
            last_error=(
                {}
                if result.returncode == 0
                else {
                    "timestamp": utc_now(),
                    "message": f"worker command exited with {result.returncode}",
                    "stderr_tail": result.stderr[-1000:],
                }
            ),
        )
        state = append_evidence(
            state,
            {
                "timestamp": utc_now(),
                "iteration": state["iteration"],
                "worker_exit_code": result.returncode,
                "progress_made": progress_made,
                "tasks_done": state["tasks_done"],
                "tasks_open": state["tasks_open"],
                "tasks_blocked": state["tasks_blocked"],
            },
        )

        persist_state(state_path, state, registry_path)
        guard_code, guard_message, _ = evaluate_guard(state_path)
        state["last_guard"] = {"timestamp": utc_now(), "code": guard_code, "message": guard_message}

        if guard_code == 0:
            state["status"] = "complete"
            state["ready_allowed"] = True
            persist_state(state_path, state, registry_path)
            print(guard_message)
            return 0

        if guard_code == 3:
            state["status"] = "error"
            state["ready_allowed"] = False
            state["last_error"] = {"timestamp": utc_now(), "message": guard_message}
            persist_state(state_path, state, registry_path)
            print(guard_message)
            return 3

        if state["stagnant_iterations"] >= state["max_stagnant_iterations"]:
            state["status"] = "blocked" if after["blocked"] and after["blocked"] == after["open"] else "stalled"
            state["ready_allowed"] = False
            state["last_error"] = {"timestamp": utc_now(), "message": guard_message}
            persist_state(state_path, state, registry_path)
            print(guard_message)
            return 2

        if guard_code == 2:
            state["last_error"] = {"timestamp": utc_now(), "message": guard_message}
            persist_state(state_path, state, registry_path)
            continue

        persist_state(state_path, state, registry_path)


if __name__ == "__main__":
    sys.exit(main())
