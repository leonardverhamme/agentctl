from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_parent(path: str | Path) -> Path:
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def save_json(path: str | Path, payload: dict[str, Any]) -> Path:
    resolved = ensure_parent(path)
    resolved.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return resolved


def load_json(path: str | Path, default: Any = None) -> Any:
    resolved = Path(path).resolve()
    if not resolved.exists():
        return {} if default is None else default
    return json.loads(resolved.read_text(encoding="utf-8"))


def save_text(path: str | Path, content: str) -> Path:
    resolved = ensure_parent(path)
    resolved.write_text(content, encoding="utf-8")
    return resolved


def command_path(name: str) -> str | None:
    return shutil.which(name)


def run_command(args: list[str], *, timeout: int = 30, cwd: str | Path | None = None) -> dict[str, Any]:
    try:
        executable = command_path(args[0]) or args[0]
        suffix = Path(executable).suffix.lower()
        shell = suffix in {".cmd", ".bat", ".ps1"}
        command = subprocess.list2cmdline([executable, *args[1:]]) if shell else [executable, *args[1:]]
        completed = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            shell=shell,
        )
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": (completed.stdout or "").strip(),
            "stderr": (completed.stderr or "").strip(),
        }
    except FileNotFoundError:
        return {"ok": False, "returncode": 127, "stdout": "", "stderr": "command not found"}
    except PermissionError as exc:
        return {"ok": False, "returncode": 126, "stdout": "", "stderr": str(exc)}
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": 124, "stdout": "", "stderr": "command timed out"}


def slugify(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return value or "item"


def short_hash(text: str) -> str:
    import hashlib

    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(value)).strip()


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))
