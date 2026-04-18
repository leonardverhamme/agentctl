from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .common import load_json
from .codex_runtime import resolve_codex_worker_command
from .paths import WORKFLOW_REGISTRY_PATH, WORKFLOW_TOOLS_DIR

sys.path.insert(0, str(WORKFLOW_TOOLS_DIR))

from workflow_common import validate_state_payload  # type: ignore  # noqa: E402


WORKFLOW_RUNNER = WORKFLOW_TOOLS_DIR / "workflow_runner.py"


def _repo_root(repo: str | None) -> Path:
    return Path(repo).resolve() if repo else Path.cwd().resolve()


def _read_state(path: Path) -> dict[str, Any]:
    payload = load_json(path, default={})
    if "schema_version" not in payload and "state_version" in payload:
        payload["schema_version"] = payload["state_version"]
    return payload


def _state_path_for_entry(entry: dict[str, Any]) -> Path:
    repo_root = entry.get("repo_root")
    workflow_name = entry.get("workflow_name")
    if not repo_root or not workflow_name:
        return Path()
    return Path(repo_root).resolve() / ".codex-workflows" / workflow_name / "state.json"


def _is_ephemeral_repo(repo_root: str | None) -> bool:
    if not repo_root:
        return True
    lowered = str(Path(repo_root)).lower()
    temp_root = str(Path(tempfile.gettempdir()).resolve()).lower()
    return lowered.startswith(temp_root) or "\\appdata\\local\\temp\\" in lowered or "/tmp/" in lowered


def _workflow_record_from_state(state_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    errors = validate_state_payload(payload)
    if payload.get("status") == "complete" and not payload.get("ready_allowed"):
        errors.append("complete workflow must have ready_allowed=true")
    return {
        "workflow_name": payload.get("workflow_name", state_path.parent.name),
        "skill_name": payload.get("skill_name"),
        "repo_root": payload.get("repo_root", str(state_path.parents[2])),
        "status": payload.get("status", "unknown"),
        "tasks_total": payload.get("tasks_total", 0),
        "tasks_done": payload.get("tasks_done", 0),
        "tasks_open": payload.get("tasks_open", 0),
        "tasks_blocked": payload.get("tasks_blocked", 0),
        "iteration": payload.get("iteration", 0),
        "schema_version": payload.get("schema_version"),
        "state_path": str(state_path),
        "checklist_path": payload.get("checklist_path"),
        "ready_allowed": payload.get("ready_allowed"),
        "updated_at": payload.get("updated_at"),
        "errors": errors,
    }


def _registry_record(entry_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    state_path = _state_path_for_entry(payload)
    if state_path.exists():
        record = _workflow_record_from_state(state_path, _read_state(state_path))
    else:
        record = {
            "workflow_name": payload.get("workflow_name", entry_id),
            "skill_name": payload.get("skill_name"),
            "repo_root": payload.get("repo_root"),
            "status": payload.get("status", "unknown"),
            "tasks_total": payload.get("tasks_total", 0),
            "tasks_done": payload.get("tasks_done", 0),
            "tasks_open": payload.get("tasks_open", 0),
            "tasks_blocked": payload.get("tasks_blocked", 0),
            "iteration": payload.get("iteration", 0),
            "schema_version": payload.get("schema_version"),
            "state_path": str(state_path) if state_path else None,
            "checklist_path": payload.get("checklist_path"),
            "ready_allowed": payload.get("ready_allowed"),
            "updated_at": payload.get("updated_at"),
            "errors": [],
        }
    record["id"] = entry_id
    record["ephemeral"] = _is_ephemeral_repo(record.get("repo_root"))
    return record


def workflow_status(*, repo: str | None, use_registry: bool) -> dict[str, Any]:
    workflows: list[dict[str, Any]] = []
    historical_workflows: list[dict[str, Any]] = []
    if use_registry:
        registry = load_json(WORKFLOW_REGISTRY_PATH, default={})
        for key, value in registry.items():
            record = _registry_record(key, value)
            if record["ephemeral"]:
                historical_workflows.append(record)
            else:
                workflows.append(record)
    else:
        repo_root = _repo_root(repo)
        workflow_dir = repo_root / ".codex-workflows"
        if workflow_dir.exists():
            for state_path in workflow_dir.glob("*/state.json"):
                workflows.append(_workflow_record_from_state(state_path, _read_state(state_path)))

    status = "error" if any(entry.get("errors") for entry in workflows) else "ok"
    return {
        "summary": {
            "status": status,
            "count": len(workflows),
            "historical_count": len(historical_workflows),
        },
        "workflows": sorted(workflows, key=lambda item: (item["status"] != "running", item["workflow_name"], item.get("repo_root", ""))),
        "historical_workflows": sorted(historical_workflows, key=lambda item: (item["workflow_name"], item.get("updated_at", ""))),
    }


def run_workflow(
    *,
    workflow: str,
    repo: str | None,
    checklist: str | None,
    progress: str | None,
    worker_command: str | None,
    worker_mode: str,
    max_iterations: int,
    max_stagnant: int,
) -> int:
    repo_root = _repo_root(repo)
    resolved_worker_command = worker_command
    if not resolved_worker_command and worker_mode in {"auto", "codex"}:
        resolved_worker_command = resolve_codex_worker_command()
    command = [
        sys.executable,
        str(WORKFLOW_RUNNER),
        "--skill",
        workflow,
        "--repo",
        str(repo_root),
        "--max-iterations",
        str(max_iterations),
        "--max-stagnant",
        str(max_stagnant),
    ]
    if checklist:
        command.extend(["--checklist", checklist])
    if progress:
        command.extend(["--progress", progress])
    if resolved_worker_command:
        command.extend(["--worker-command", resolved_worker_command])
    command.extend(["--worker-mode", worker_mode])
    result = subprocess.run(command, cwd=str(repo_root), check=False)
    return result.returncode
