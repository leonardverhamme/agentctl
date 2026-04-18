from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .common import command_path, run_command


CODEX_ENV_TEMPLATE = "AGENTCTL_CODEX_WORKER_TEMPLATE"
DEFAULT_CANDIDATES = [
    "codex",
    r"C:\Program Files\WindowsApps\OpenAI.Codex_26.409.7971.0_x64__2p2nqsd0c76g0\app\resources\codex.exe",
]


def _candidate_paths() -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for candidate in DEFAULT_CANDIDATES:
        resolved = command_path(candidate) if Path(candidate).name == candidate else candidate
        if not resolved:
            continue
        normalized = str(Path(resolved))
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
        "worker_runtime_ready": bool(template) or callable_runtime,
    }


def resolve_codex_worker_command() -> str | None:
    template = os.environ.get(CODEX_ENV_TEMPLATE, "").strip()
    return template or None
