from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATE_VERSION = 1
DEFAULT_MAX_ITERATIONS = 30
DEFAULT_MAX_STAGNANT_ITERATIONS = 3
DEFAULT_TARGET_BATCH_SIZE = 4
MAX_AUTO_ITERATIONS = 250
BLOCKER_RE = re.compile(r"\bblocked?\b|\bblocker\b", re.IGNORECASE)
CHECKBOX_RE = re.compile(r"^\s*[-*]\s+\[(?P<mark>[ xX])\]\s+(?P<text>.+?)\s*$")
STATUS_RE = re.compile(r"^\s*[-*]\s*(?P<label>Unchecked|Checked|Blocked|Open|Done)\s*:\s*(?P<count>\d+)\s*$")

REQUIRED_STATE_FIELDS = {
    "schema_version",
    "workflow_name",
    "skill_name",
    "repo_root",
    "checklist_path",
    "progress_path",
    "status",
    "iteration",
    "max_iterations",
    "stagnant_iterations",
    "max_stagnant_iterations",
    "tasks_total",
    "tasks_done",
    "tasks_blocked",
    "tasks_open",
    "last_batch",
    "last_validation",
    "last_error",
    "ready_allowed",
    "remaining_items",
    "blocked_items",
    "evidence",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_path(path: str | Path, base: str | Path | None = None) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        base_path = Path(base) if base is not None else Path.cwd()
        candidate = base_path / candidate
    return candidate.resolve()


def workflow_state_path(repo_root: str | Path, workflow_name: str) -> Path:
    return resolve_path(Path(repo_root) / ".codex-workflows" / workflow_name / "state.json")


def default_checklist_path(repo_root: str | Path, skill_name: str) -> Path:
    return resolve_path(Path(repo_root) / "docs" / f"{skill_name}-checklist.md")


def default_progress_path(repo_root: str | Path, skill_name: str) -> Path:
    return resolve_path(Path(repo_root) / "docs" / f"{skill_name}-progress.md")


def ensure_parent(path: str | Path) -> Path:
    resolved = resolve_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(resolve_path(path).read_text(encoding="utf-8"))


def save_json(path: str | Path, payload: dict[str, Any]) -> Path:
    resolved = ensure_parent(path)
    temp_path = resolved.with_name(f"{resolved.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    last_error: OSError | None = None
    for _ in range(5):
        try:
            os.replace(temp_path, resolved)
            return resolved
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.05)
    if last_error is not None:
        raise last_error
    return resolved


@contextmanager
def exclusive_lock(path: str | Path, *, timeout_seconds: float = 5.0, poll_seconds: float = 0.05):
    resolved = ensure_parent(path)
    deadline = time.monotonic() + timeout_seconds
    fd: int | None = None
    while True:
        try:
            fd = os.open(resolved, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("utf-8"))
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"timed out waiting for lock: {resolved}")
            time.sleep(poll_seconds)
    try:
        yield resolved
    finally:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(resolved)
        except FileNotFoundError:
            pass


def slugify(text: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return normalized or "item"


def default_state(
    *,
    workflow_name: str,
    skill_name: str,
    repo_root: str | Path,
    checklist_path: str | Path,
    progress_path: str | Path,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    max_stagnant_iterations: int = DEFAULT_MAX_STAGNANT_ITERATIONS,
    worker_command: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": STATE_VERSION,
        "state_version": STATE_VERSION,
        "workflow_name": workflow_name,
        "skill_name": skill_name,
        "repo_root": str(resolve_path(repo_root)),
        "checklist_path": str(resolve_path(checklist_path, repo_root)),
        "progress_path": str(resolve_path(progress_path, repo_root)),
        "status": "initializing",
        "iteration": 0,
        "max_iterations": max_iterations,
        "stagnant_iterations": 0,
        "max_stagnant_iterations": max_stagnant_iterations,
        "tasks_total": 0,
        "tasks_done": 0,
        "tasks_blocked": 0,
        "tasks_open": 0,
        "last_batch": [],
        "last_validation": {},
        "last_error": {},
        "ready_allowed": False,
        "remaining_items": [],
        "blocked_items": [],
        "evidence": [],
        "worker_command": worker_command or "",
        "started_at": utc_now(),
        "updated_at": utc_now(),
    }


def validate_state_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_STATE_FIELDS - set(payload))
    if missing:
        errors.append(f"missing required state fields: {', '.join(missing)}")
    for field in ("iteration", "max_iterations", "stagnant_iterations", "max_stagnant_iterations", "tasks_total", "tasks_done", "tasks_blocked", "tasks_open"):
        if field in payload and not isinstance(payload[field], int):
            errors.append(f"{field} must be an integer")
    for field in ("last_batch", "remaining_items", "blocked_items", "evidence"):
        if field in payload and not isinstance(payload[field], list):
            errors.append(f"{field} must be a list")
    for field in ("last_validation", "last_error"):
        if field in payload and not isinstance(payload[field], dict):
            errors.append(f"{field} must be an object")
    if payload.get("status") not in {None, "initializing", "running", "complete", "blocked", "stalled", "error"}:
        errors.append("status must be one of initializing, running, complete, blocked, stalled, error")
    return errors


def normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "title": item["title"],
        "line": item["line"],
        "blocked": item["blocked"],
    }


def parse_checklist(path: str | Path) -> dict[str, Any]:
    resolved = resolve_path(path)
    if not resolved.exists():
        return {
            "exists": False,
            "path": str(resolved),
            "items": [],
            "total": 0,
            "done": 0,
            "open": 0,
            "blocked": 0,
            "remaining_items": [],
            "blocked_items": [],
            "visible_counts": {},
        }

    lines = resolved.read_text(encoding="utf-8").splitlines()
    items: list[dict[str, Any]] = []
    visible_counts: dict[str, int] = {}
    slug_counts: dict[str, int] = {}
    current_item: dict[str, Any] | None = None

    for line_number, line in enumerate(lines, start=1):
        status_match = STATUS_RE.match(line)
        if status_match:
            visible_counts[status_match.group("label").lower()] = int(status_match.group("count"))

        checkbox_match = CHECKBOX_RE.match(line)
        if checkbox_match:
            text = checkbox_match.group("text").strip()
            slug = slugify(text)
            slug_counts[slug] = slug_counts.get(slug, 0) + 1
            item_id = f"{slug}-{slug_counts[slug]}"
            current_item = {
                "id": item_id,
                "title": text,
                "line": line_number,
                "checked": checkbox_match.group("mark").lower() == "x",
                "blocked": bool(BLOCKER_RE.search(text)),
                "notes": [],
            }
            items.append(current_item)
            continue

        if current_item is not None and line.strip():
            current_item["notes"].append(line.strip())
            if BLOCKER_RE.search(line):
                current_item["blocked"] = True

    done_items = [item for item in items if item["checked"]]
    remaining_items = [item for item in items if not item["checked"]]
    blocked_items = [item for item in remaining_items if item["blocked"]]

    return {
        "exists": True,
        "path": str(resolved),
        "items": items,
        "total": len(items),
        "done": len(done_items),
        "open": len(remaining_items),
        "blocked": len(blocked_items),
        "remaining_items": [normalize_item(item) for item in remaining_items],
        "blocked_items": [normalize_item(item) for item in blocked_items],
        "visible_counts": visible_counts,
    }


def sync_state_from_checklist(
    payload: dict[str, Any],
    checklist: dict[str, Any],
    *,
    status: str | None = None,
    last_batch: list[str] | None = None,
    last_validation: dict[str, Any] | None = None,
    last_error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    updated = deepcopy(payload)
    updated["tasks_total"] = checklist["total"]
    updated["tasks_done"] = checklist["done"]
    updated["tasks_blocked"] = checklist["blocked"]
    updated["tasks_open"] = checklist["open"]
    updated["remaining_items"] = checklist["remaining_items"]
    updated["blocked_items"] = checklist["blocked_items"]
    updated["ready_allowed"] = checklist["open"] == 0 and checklist["blocked"] == 0
    if status is not None:
        updated["status"] = status
    if last_batch is not None:
        updated["last_batch"] = last_batch
    if last_validation is not None:
        updated["last_validation"] = last_validation
    if last_error is not None:
        updated["last_error"] = last_error
    updated["updated_at"] = utc_now()
    return updated


def meaningful_progress(before: dict[str, Any], after: dict[str, Any]) -> bool:
    return any(
        [
            before["done"] != after["done"],
            before["open"] != after["open"],
            before["blocked"] != after["blocked"],
            before["remaining_items"] != after["remaining_items"],
            before["blocked_items"] != after["blocked_items"],
        ]
    )


def suggested_max_iterations(open_items: int, configured_max: int, *, target_batch_size: int = DEFAULT_TARGET_BATCH_SIZE, hard_cap: int = MAX_AUTO_ITERATIONS) -> int:
    normalized_open = max(open_items, 0)
    if normalized_open == 0:
        return max(configured_max, DEFAULT_MAX_ITERATIONS)
    required_batches = (normalized_open + max(target_batch_size, 1) - 1) // max(target_batch_size, 1)
    recommended = max(DEFAULT_MAX_ITERATIONS, required_batches + 8)
    return min(max(configured_max, recommended), hard_cap)


def derive_last_batch(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    before_open = {item["id"]: item for item in before["remaining_items"]}
    after_open = {item["id"]: item for item in after["remaining_items"]}
    before_done_ids = {item["id"] for item in before.get("items", []) if item["checked"]}
    after_done_ids = {item["id"] for item in after.get("items", []) if item["checked"]}

    newly_done = [item["title"] for item in before.get("items", []) if item["id"] in (after_done_ids - before_done_ids)]
    if newly_done:
        return newly_done

    changed_open = []
    for item_id, after_item in after_open.items():
        before_item = before_open.get(item_id)
        if before_item is None:
            changed_open.append(after_item["title"])
        elif before_item.get("blocked") != after_item.get("blocked"):
            changed_open.append(after_item["title"])
    return changed_open[:10]


def append_evidence(payload: dict[str, Any], entry: dict[str, Any], *, keep_last: int = 20) -> dict[str, Any]:
    updated = deepcopy(payload)
    evidence = list(updated.get("evidence", []))
    evidence.append(entry)
    updated["evidence"] = evidence[-keep_last:]
    updated["updated_at"] = utc_now()
    return updated


def render_progress_markdown(payload: dict[str, Any], checklist: dict[str, Any]) -> str:
    lines = [
        f"# {payload['workflow_name']} Progress",
        "",
        "## Summary",
        "",
        f"- Status: `{payload['status']}`",
        f"- Iteration: {payload['iteration']} / {payload['max_iterations']}",
        f"- Stagnant iterations: {payload['stagnant_iterations']} / {payload['max_stagnant_iterations']}",
        f"- Total tasks: {payload['tasks_total']}",
        f"- Done: {payload['tasks_done']}",
        f"- Open: {payload['tasks_open']}",
        f"- Blocked: {payload['tasks_blocked']}",
        f"- Ready allowed: `{str(payload['ready_allowed']).lower()}`",
        "",
        "## Paths",
        "",
        f"- Checklist: `{payload['checklist_path']}`",
        f"- State: `{workflow_state_path(payload['repo_root'], payload['workflow_name'])}`",
        "",
    ]

    if payload.get("last_batch"):
        lines.extend(["## Last Batch", ""])
        for entry in payload["last_batch"]:
            lines.append(f"- {entry}")
        lines.append("")

    if payload.get("last_validation"):
        lines.extend(["## Last Validation", "", "```json", json.dumps(payload["last_validation"], indent=2, sort_keys=True), "```", ""])

    if payload.get("last_error"):
        lines.extend(["## Last Error", "", "```json", json.dumps(payload["last_error"], indent=2, sort_keys=True), "```", ""])

    if checklist["remaining_items"]:
        lines.extend(["## Remaining Items", ""])
        for item in checklist["remaining_items"][:50]:
            suffix = " (blocked)" if item["blocked"] else ""
            lines.append(f"- [ ] {item['title']}{suffix}")
        lines.append("")

    if checklist["blocked_items"]:
        lines.extend(["## Blocked Items", ""])
        for item in checklist["blocked_items"][:50]:
            lines.append(f"- [ ] {item['title']}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def load_or_initialize_state(
    *,
    state_path: str | Path,
    workflow_name: str,
    skill_name: str,
    repo_root: str | Path,
    checklist_path: str | Path,
    progress_path: str | Path,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    max_stagnant_iterations: int = DEFAULT_MAX_STAGNANT_ITERATIONS,
    worker_command: str | None = None,
) -> dict[str, Any]:
    resolved_state_path = resolve_path(state_path)
    if resolved_state_path.exists():
        payload = load_json(resolved_state_path)
        payload.setdefault("schema_version", payload.get("state_version", STATE_VERSION))
        payload["state_version"] = payload["schema_version"]
        if worker_command:
            payload["worker_command"] = worker_command
        else:
            payload.setdefault("worker_command", "")
        existing_max_iterations = payload.get("max_iterations", max_iterations)
        if not isinstance(existing_max_iterations, int):
            existing_max_iterations = max_iterations
        payload["max_iterations"] = max(existing_max_iterations, max_iterations)
        existing_max_stagnant = payload.get("max_stagnant_iterations", max_stagnant_iterations)
        if not isinstance(existing_max_stagnant, int):
            existing_max_stagnant = max_stagnant_iterations
        payload["max_stagnant_iterations"] = max(existing_max_stagnant, max_stagnant_iterations)
        payload["checklist_path"] = str(resolve_path(checklist_path, repo_root))
        payload["progress_path"] = str(resolve_path(progress_path, repo_root))
        payload["repo_root"] = str(resolve_path(repo_root))
        payload["workflow_name"] = workflow_name
        payload["skill_name"] = skill_name
        payload["updated_at"] = utc_now()
        return payload

    return default_state(
        workflow_name=workflow_name,
        skill_name=skill_name,
        repo_root=repo_root,
        checklist_path=checklist_path,
        progress_path=progress_path,
        max_iterations=max_iterations,
        max_stagnant_iterations=max_stagnant_iterations,
        worker_command=worker_command,
    )


def update_registry(registry_path: str | Path, payload: dict[str, Any]) -> None:
    resolved = ensure_parent(registry_path)
    lock_path = resolved.with_name(f"{resolved.name}.lock")
    with exclusive_lock(lock_path):
        if resolved.exists():
            registry = load_json(resolved)
        else:
            registry = {}
        registry_key = f"{payload['repo_root']}::{payload['workflow_name']}"
        registry[registry_key] = {
            "schema_version": payload.get("schema_version", STATE_VERSION),
            "workflow_name": payload["workflow_name"],
            "skill_name": payload["skill_name"],
            "repo_root": payload["repo_root"],
            "checklist_path": payload["checklist_path"],
            "progress_path": payload["progress_path"],
            "status": payload["status"],
            "iteration": payload["iteration"],
            "tasks_total": payload["tasks_total"],
            "tasks_done": payload["tasks_done"],
            "tasks_open": payload["tasks_open"],
            "tasks_blocked": payload["tasks_blocked"],
            "ready_allowed": payload.get("ready_allowed", False),
            "updated_at": payload["updated_at"],
        }
        save_json(resolved, registry)
