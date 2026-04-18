from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


BUNDLE_ITEMS = [
    "agentctl",
    "workflow-tools",
    "skills",
    "plugins",
    "docs/agentctl",
    "README.md",
    "AGENTS.md",
    "agentctl.cmd",
    "agentctl.sh",
]

PLUGIN_SNIPPET = '\n[plugins."agentctl"]\nenabled = true\n'
LEGACY_PLUGIN_KEYS = ('[plugins."agentctl-platform"]', "[plugins.agentctl-platform]")
LEGACY_PLUGIN_DIR = "plugins/agentctl-platform"
DEFAULT_REPO_URL = "https://github.com/leonardverhamme/agentctl"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).resolve()


def copy_item(source_root: Path, target_root: Path, relative: str) -> None:
    source = source_root / relative
    target = target_root / relative
    if source.is_dir():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def ensure_plugin_enabled(config_path: Path) -> None:
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    for legacy_key in LEGACY_PLUGIN_KEYS:
        existing = existing.replace(legacy_key, '[plugins."agentctl"]')
    if '[plugins."agentctl"]' in existing or "[plugins.agentctl]" in existing:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(existing, encoding="utf-8")
        return
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(existing.rstrip() + PLUGIN_SNIPPET, encoding="utf-8")


def cleanup_legacy_plugin(target_root: Path) -> None:
    legacy_path = target_root / LEGACY_PLUGIN_DIR
    if legacy_path.exists():
        shutil.rmtree(legacy_path)


def evaluate_post_check(command_name: str, result: subprocess.CompletedProcess[str]) -> tuple[bool, str | None]:
    if result.returncode == 0:
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return True, None
        return payload.get("status") != "error", payload.get("status")

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False, None

    status = payload.get("status")
    if status in {"ok", "degraded"}:
        return True, status
    if command_name == "maintenance":
        summary = payload.get("summary") or {}
        summary_status = summary.get("status")
        if summary.get("blocked_findings", 0) == 0 and summary_status in {"ok", "degraded"}:
            return True, summary_status
    return False, status


def run_post_install_checks(target_root: Path) -> dict[str, object]:
    agentctl_entry = target_root / "agentctl" / "agentctl.py"
    checks: list[dict[str, object]] = []
    env = os.environ.copy()
    env["CODEX_HOME"] = str(target_root)
    for command_name in ("doctor", "capabilities", "maintenance"):
        command = [sys.executable, str(agentctl_entry), command_name]
        if command_name == "maintenance":
            command.append("audit")
        command.append("--json")
        result = subprocess.run(command, capture_output=True, text=True, check=False, env=env)
        ok, reported_status = evaluate_post_check(command_name, result)
        checks.append(
            {
                "command": " ".join(command[2:-1]),
                "returncode": result.returncode,
                "ok": ok,
                "reported_status": reported_status,
                "stdout_tail": result.stdout[-2000:],
                "stderr_tail": result.stderr[-2000:],
            }
        )

    summary = {
        "status": "ok" if all(check["ok"] for check in checks) else "error",
        "checks": checks,
        "target_codex_home": str(target_root),
    }
    report_path = target_root / "agentctl" / "state" / "bootstrap-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def install_bundle(*, source_root: Path, target_root: Path, skip_post_checks: bool = False) -> dict[str, object]:
    target_root.mkdir(parents=True, exist_ok=True)

    for relative in BUNDLE_ITEMS:
        copy_item(source_root, target_root, relative)

    cleanup_legacy_plugin(target_root)
    ensure_plugin_enabled(target_root / "config.toml")

    summary: dict[str, object] = {
        "status": "ok",
        "target_codex_home": str(target_root),
        "post_checks": None,
    }
    if not skip_post_checks:
        summary["post_checks"] = run_post_install_checks(target_root)
        summary["status"] = str(summary["post_checks"]["status"])
    return summary


def github_archive_url(repo_url: str, *, ref: str, ref_type: str) -> str:
    suffix = "heads" if ref_type == "branch" else "tags"
    return f"{repo_url.rstrip('/')}/archive/refs/{suffix}/{ref}.zip"


def download_archive(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    return destination


def extract_archive(archive_path: Path, destination: Path) -> Path:
    with zipfile.ZipFile(archive_path) as bundle:
        bundle.extractall(destination)
    entries = [path for path in destination.iterdir() if path.is_dir()]
    if len(entries) == 1:
        return entries[0]
    raise RuntimeError(f"Expected one extracted root directory, found {len(entries)}")


def bootstrap_bundle(
    *,
    target_root: Path,
    source_root: Path | None = None,
    repo_url: str = DEFAULT_REPO_URL,
    ref: str = "main",
    ref_type: str = "branch",
    skip_post_checks: bool = False,
) -> dict[str, object]:
    if source_root is not None:
        return install_bundle(source_root=source_root.resolve(), target_root=target_root, skip_post_checks=skip_post_checks)

    with tempfile.TemporaryDirectory(prefix="agentctl-bootstrap-") as temp_dir:
        temp_root = Path(temp_dir)
        archive_path = temp_root / "bundle.zip"
        archive_url = github_archive_url(repo_url, ref=ref, ref_type=ref_type)
        download_archive(archive_url, archive_path)
        extracted_root = extract_archive(archive_path, temp_root / "src")
        return install_bundle(source_root=extracted_root, target_root=target_root, skip_post_checks=skip_post_checks)
