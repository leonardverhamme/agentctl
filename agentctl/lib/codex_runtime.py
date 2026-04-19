from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .common import command_path, run_command


CODEX_ENV_TEMPLATE = "AGENTCTL_CODEX_WORKER_TEMPLATE"
CODEX_PATH_ENV = "AGENTCTL_CODEX_PATH"
DEFAULT_CANDIDATES = [
    "codex.cmd",
    "codex",
    r"C:\Program Files\WindowsApps\OpenAI.Codex_26.409.7971.0_x64__2p2nqsd0c76g0\app\resources\codex.exe",
]


def _windows_global_cli_candidates() -> list[str]:
    if os.name != "nt":
        return []
    appdata = os.environ.get("APPDATA", "").strip()
    if not appdata:
        return []
    npm_dir = Path(appdata) / "npm"
    candidates = [
        npm_dir / "codex.cmd",
        npm_dir / "codex.ps1",
        npm_dir / "codex",
    ]
    return [str(path) for path in candidates if path.exists()]


def _is_explicit_path(candidate: str) -> bool:
    return (
        "/" in candidate
        or "\\" in candidate
        or candidate.startswith(".")
        or candidate.startswith("~")
        or (len(candidate) >= 2 and candidate[1] == ":")
    )


def _candidate_paths() -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    env_candidate = os.environ.get(CODEX_PATH_ENV, "").strip()
    candidates = [env_candidate] if env_candidate else []
    candidates.extend(_windows_global_cli_candidates())
    candidates.extend(DEFAULT_CANDIDATES)
    for candidate in candidates:
        resolved = candidate if _is_explicit_path(candidate) else command_path(candidate)
        if not resolved:
            continue
        normalized = resolved
        if normalized not in seen:
            seen.add(normalized)
            values.append(normalized)
    return values


def detect_codex_runtime() -> dict[str, Any]:
    candidates = _candidate_paths()
    template = os.environ.get(CODEX_ENV_TEMPLATE, "").strip()

    if not candidates:
        return {
            "name": "codex",
            "installed": False,
            "status": "missing",
            "callable": False,
            "template_configured": bool(template),
            "worker_runtime_ready": False,
            "candidates": [],
            "path_env": CODEX_PATH_ENV,
        }

    path = candidates[0]
    probe = run_command([path, "--help"], timeout=20)
    detail = probe["stderr"] or probe["stdout"]
    callable_runtime = probe["ok"]
    status = "ok" if callable_runtime else "degraded"
    if not callable_runtime and "access is denied" in detail.lower():
        status = "degraded"

    return {
        "name": "codex",
        "installed": True,
        "status": status,
        "path": path,
        "candidates": candidates,
        "callable": callable_runtime,
        "call_detail": detail,
        "template_configured": bool(template),
        "template_env": CODEX_ENV_TEMPLATE,
        "path_env": CODEX_PATH_ENV,
        "builtin_worker_wrapper": str(Path(__file__).resolve().parents[1] / "codex_worker.py"),
        "worker_runtime_ready": bool(template) or callable_runtime,
    }


def _quoted(value: str | Path) -> str:
    return subprocess.list2cmdline([str(value)])


def builtin_codex_worker_command() -> str:
    worker_path = Path(__file__).resolve().parents[1] / "codex_worker.py"
    return subprocess.list2cmdline([sys.executable, str(worker_path)])


def render_worker_command_template(template: str, *, workflow: str, repo_root: str | Path, checklist_path: str | Path, progress_path: str | Path, state_path: str | Path) -> str:
    runtime = detect_codex_runtime()
    codex_path = runtime.get("path") or ""
    worker_path = Path(__file__).resolve().parents[1] / "codex_worker.py"
    context = {
        "workflow": workflow,
        "workflow_name": workflow,
        "skill_name": workflow,
        "repo_root": str(Path(repo_root)),
        "checklist_path": str(Path(checklist_path)),
        "progress_path": str(Path(progress_path)),
        "state_path": str(Path(state_path)),
        "python": sys.executable,
        "python_q": _quoted(sys.executable),
        "codex_path": codex_path,
        "codex_path_q": _quoted(codex_path) if codex_path else "",
        "codex_worker": str(worker_path),
        "codex_worker_q": _quoted(worker_path),
    }
    return template.format_map(context)


def resolve_codex_worker_command(*, workflow: str, repo_root: str | Path, checklist_path: str | Path, progress_path: str | Path, state_path: str | Path) -> str | None:
    template = os.environ.get(CODEX_ENV_TEMPLATE, "").strip()
    if template:
        return render_worker_command_template(
            template,
            workflow=workflow,
            repo_root=repo_root,
            checklist_path=checklist_path,
            progress_path=progress_path,
            state_path=state_path,
        )

    runtime = detect_codex_runtime()
    if runtime.get("callable"):
        return builtin_codex_worker_command()
    return None
