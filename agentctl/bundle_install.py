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
from typing import Any

try:
    from .lib.branding import (
        COMPATIBILITY_COMMAND,
        LEGACY_PLUGIN_NAMES,
        LEGACY_REPO_URL,
        PUBLIC_COMMAND,
        PUBLIC_DOCS_DIRNAME,
        PUBLIC_PLUGIN_NAME,
        PUBLIC_PRODUCT_NAME,
        PUBLIC_REPO_URL,
        RELEASE_BUNDLE_PREFIX,
    )
    from .lib.common import save_json, utc_now
    from .lib.config_layers import CONFIG_SCHEMA_VERSION
except ImportError:
    from lib.branding import (
        COMPATIBILITY_COMMAND,
        LEGACY_PLUGIN_NAMES,
        LEGACY_REPO_URL,
        PUBLIC_COMMAND,
        PUBLIC_DOCS_DIRNAME,
        PUBLIC_PLUGIN_NAME,
        PUBLIC_PRODUCT_NAME,
        PUBLIC_REPO_URL,
        RELEASE_BUNDLE_PREFIX,
    )
    from lib.common import save_json, utc_now
    from lib.config_layers import CONFIG_SCHEMA_VERSION


BUNDLE_ITEMS = [
    "agentctl",
    "workflow-tools",
    "skills",
    "plugins",
    f"docs/{PUBLIC_DOCS_DIRNAME}",
    "README.md",
    "AGENTS.md",
    f"{PUBLIC_COMMAND}.cmd",
    f"{PUBLIC_COMMAND}.sh",
    f"{COMPATIBILITY_COMMAND}.cmd",
    f"{COMPATIBILITY_COMMAND}.sh",
]

PLUGIN_SNIPPET = f'\n[plugins."{PUBLIC_PLUGIN_NAME}"]\nenabled = true\n'
LEGACY_PLUGIN_KEYS = tuple([f'[plugins."{name}"]' for name in LEGACY_PLUGIN_NAMES] + [f"[plugins.{name}]" for name in LEGACY_PLUGIN_NAMES])
LEGACY_PLUGIN_DIRS = tuple(f"plugins/{name}" for name in LEGACY_PLUGIN_NAMES)
DEFAULT_REPO_URL = PUBLIC_REPO_URL
DEFAULT_UPDATE_CHANNEL = "latest"
DEFAULT_UPDATE_SOURCE = "github-release"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).resolve()


def install_metadata_path(target_root: Path) -> Path:
    return target_root / "agentctl" / "state" / "install-metadata.json"


def _latest_release_api(repo_url: str) -> str:
    owner_repo = repo_url.rstrip("/").split("github.com/")[-1]
    return f"https://api.github.com/repos/{owner_repo}/releases/latest"


def _tag_release_api(repo_url: str, version: str) -> str:
    owner_repo = repo_url.rstrip("/").split("github.com/")[-1]
    return f"https://api.github.com/repos/{owner_repo}/releases/tags/{version}"


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": f"{PUBLIC_PRODUCT_NAME}-bootstrap"})
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def _release_metadata(repo_url: str, version: str | None) -> dict[str, Any]:
    payload = _fetch_json(_tag_release_api(repo_url, version) if version else _latest_release_api(repo_url))
    tag = payload.get("tag_name")
    assets = payload.get("assets", [])
    expected_names = [
        f"{RELEASE_BUNDLE_PREFIX}-{tag}.zip",
        f"{PUBLIC_PRODUCT_NAME}-{tag}.zip",
    ]
    asset = next((item for item in assets if item.get("name") in expected_names), None)
    if not asset:
        available = ", ".join(item.get("name", "<unknown>") for item in assets)
        raise RuntimeError(f"Release asset not found for {tag}. Available assets: {available}")
    return {
        "version": tag,
        "asset_name": asset["name"],
        "download_url": asset["browser_download_url"],
        "repo_url": repo_url,
    }


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
        existing = existing.replace(legacy_key, f'[plugins."{PUBLIC_PLUGIN_NAME}"]')
    if f'[plugins."{PUBLIC_PLUGIN_NAME}"]' in existing or f"[plugins.{PUBLIC_PLUGIN_NAME}]" in existing:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(existing, encoding="utf-8")
        return
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(existing.rstrip() + PLUGIN_SNIPPET, encoding="utf-8")


def cleanup_legacy_plugin(target_root: Path) -> list[str]:
    removed: list[str] = []
    for relative in LEGACY_PLUGIN_DIRS:
        legacy_path = target_root / relative
        if legacy_path.exists():
            shutil.rmtree(legacy_path)
            removed.append(str(legacy_path))
    return removed


def evaluate_post_check(command_name: str, result: subprocess.CompletedProcess[str]) -> tuple[bool, str | None]:
    if result.returncode == 0:
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return True, None
        if command_name == "doctor":
            summary = payload.get("summary", {})
            return summary.get("status", "ok") != "error", summary.get("status")
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


def write_install_metadata(
    target_root: Path,
    *,
    source_kind: str,
    repo_url: str,
    version: str,
    channel: str = DEFAULT_UPDATE_CHANNEL,
    update_source: str = DEFAULT_UPDATE_SOURCE,
    source_ref: str | None = None,
) -> Path:
    payload = {
        "schema_version": 1,
        "product_name": PUBLIC_PRODUCT_NAME,
        "public_command": PUBLIC_COMMAND,
        "compatibility_command": COMPATIBILITY_COMMAND,
        "bundle_dir": "agentctl",
        "installed_at": utc_now(),
        "repo_url": repo_url,
        "version": version,
        "channel": channel,
        "update_source": update_source,
        "source_kind": source_kind,
        "source_ref": source_ref,
        "config_schema_version": CONFIG_SCHEMA_VERSION,
    }
    return save_json(install_metadata_path(target_root), payload)


def read_install_metadata(target_root: Path | None = None) -> dict[str, Any]:
    root = target_root or default_codex_home()
    path = install_metadata_path(root)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def repair_install(target_root: Path, *, reason: str = "doctor-fix") -> dict[str, Any]:
    target_root.mkdir(parents=True, exist_ok=True)
    removed = cleanup_legacy_plugin(target_root)
    ensure_plugin_enabled(target_root / "config.toml")
    metadata = read_install_metadata(target_root)
    changed = bool(removed)
    if not metadata:
        write_install_metadata(
            target_root,
            source_kind="repaired-local",
            repo_url=PUBLIC_REPO_URL,
            version="unknown",
            source_ref=reason,
        )
        changed = True
    return {
        "status": "ok",
        "changed": changed,
        "removed_legacy_plugins": removed,
        "config_path": str(target_root / "config.toml"),
        "install_metadata_path": str(install_metadata_path(target_root)),
    }


def run_post_install_checks(target_root: Path) -> dict[str, object]:
    agentctl_entry = target_root / "agentctl" / "agentctl.py"
    checks: list[dict[str, object]] = []
    env = os.environ.copy()
    env["CODEX_HOME"] = str(target_root)
    for command_name, args in (
        ("doctor", [PUBLIC_COMMAND, "doctor", "--json"]),
        ("capabilities", [PUBLIC_COMMAND, "capabilities", "--json"]),
        ("maintenance", [PUBLIC_COMMAND, "maintenance", "audit", "--json"]),
        ("self-check", [PUBLIC_COMMAND, "self-check", "--json"]),
    ):
        command = [sys.executable, str(agentctl_entry), *args[1:]]
        result = subprocess.run(command, capture_output=True, text=True, check=False, env=env)
        ok, reported_status = evaluate_post_check(command_name, result)
        checks.append(
            {
                "command": " ".join(args),
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


def install_bundle(
    *,
    source_root: Path,
    target_root: Path,
    skip_post_checks: bool = False,
    source_kind: str = "local-source",
    repo_url: str = PUBLIC_REPO_URL,
    version: str = "dev",
    channel: str = DEFAULT_UPDATE_CHANNEL,
    update_source: str = DEFAULT_UPDATE_SOURCE,
    source_ref: str | None = None,
) -> dict[str, object]:
    target_root.mkdir(parents=True, exist_ok=True)

    for relative in BUNDLE_ITEMS:
        copy_item(source_root, target_root, relative)

    removed = cleanup_legacy_plugin(target_root)
    ensure_plugin_enabled(target_root / "config.toml")
    metadata_path = write_install_metadata(
        target_root,
        source_kind=source_kind,
        repo_url=repo_url,
        version=version,
        channel=channel,
        update_source=update_source,
        source_ref=source_ref,
    )

    summary: dict[str, object] = {
        "status": "ok",
        "target_codex_home": str(target_root),
        "post_checks": None,
        "removed_legacy_plugins": removed,
        "install_metadata_path": str(metadata_path),
    }
    if not skip_post_checks:
        summary["post_checks"] = run_post_install_checks(target_root)
        summary["status"] = str(summary["post_checks"]["status"])
    return summary


def download_archive(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": f"{PUBLIC_PRODUCT_NAME}-bootstrap"})
    with urllib.request.urlopen(request) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    return destination


def extract_archive(archive_path: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as bundle:
        bundle.extractall(destination)
    entries = list(destination.iterdir())
    directory_entries = [path for path in entries if path.is_dir()]
    if len(directory_entries) == 1 and len(directory_entries) == len(entries):
        return directory_entries[0]

    top_level_names = {path.name for path in entries}
    expected_bundle_entries = {Path(relative).parts[0] for relative in BUNDLE_ITEMS}
    if expected_bundle_entries.issubset(top_level_names):
        return destination

    raise RuntimeError(f"Expected one extracted root directory or a flat release bundle, found entries: {sorted(top_level_names)}")


def github_archive_url(repo_url: str, *, ref: str, ref_type: str) -> str:
    suffix = "heads" if ref_type == "branch" else "tags"
    return f"{repo_url.rstrip('/')}/archive/refs/{suffix}/{ref}.zip"


def bootstrap_bundle(
    *,
    target_root: Path,
    source_root: Path | None = None,
    repo_url: str = DEFAULT_REPO_URL,
    version: str | None = None,
    ref: str = "main",
    ref_type: str = "branch",
    skip_post_checks: bool = False,
) -> dict[str, object]:
    if source_root is not None:
        return install_bundle(
            source_root=source_root.resolve(),
            target_root=target_root,
            skip_post_checks=skip_post_checks,
            source_kind="local-source",
            repo_url=repo_url,
            version=version or "dev",
            source_ref=str(source_root.resolve()),
        )

    with tempfile.TemporaryDirectory(prefix=f"{PUBLIC_PRODUCT_NAME}-bootstrap-") as temp_dir:
        temp_root = Path(temp_dir)
        archive_path = temp_root / "bundle.zip"
        try:
            release = _release_metadata(repo_url, version)
            download_archive(release["download_url"], archive_path)
            extracted_root = extract_archive(archive_path, temp_root / "src")
            return install_bundle(
                source_root=extracted_root,
                target_root=target_root,
                skip_post_checks=skip_post_checks,
                source_kind="github-release",
                repo_url=repo_url,
                version=release["version"],
                channel=DEFAULT_UPDATE_CHANNEL,
                update_source=DEFAULT_UPDATE_SOURCE,
                source_ref=release["asset_name"],
            )
        except Exception:
            fallback_url = github_archive_url(repo_url or LEGACY_REPO_URL, ref=ref, ref_type=ref_type)
            download_archive(fallback_url, archive_path)
            extracted_root = extract_archive(archive_path, temp_root / "src")
            return install_bundle(
                source_root=extracted_root,
                target_root=target_root,
                skip_post_checks=skip_post_checks,
                source_kind="github-archive-fallback",
                repo_url=repo_url or LEGACY_REPO_URL,
                version=version or ref,
                source_ref=fallback_url,
            )


def upgrade_bundle(
    *,
    target_root: Path,
    skip_post_checks: bool = False,
    version: str | None = None,
) -> dict[str, object]:
    metadata = read_install_metadata(target_root)
    repo_url = metadata.get("repo_url") or PUBLIC_REPO_URL
    channel = metadata.get("channel") or DEFAULT_UPDATE_CHANNEL
    update_source = metadata.get("update_source") or DEFAULT_UPDATE_SOURCE
    summary = bootstrap_bundle(
        target_root=target_root,
        repo_url=repo_url,
        version=version,
        skip_post_checks=skip_post_checks,
    )
    summary["channel"] = channel
    summary["update_source"] = update_source
    return summary
