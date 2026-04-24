from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .branding import PUBLIC_COMMAND, PUBLIC_DOCS_DIRNAME
from .common import command_path, load_json, print_json, run_command, save_json, utc_now
from .config_layers import _load_toml, effective_config
from .paths import CODEX_HOME, COMPUTER_GRAPH_PATH, CONFIG_PATH, STATE_DIR


SCHEMA_VERSION = 1
WORKSPACE_SCHEMA_VERSION = 1
MANIFEST_DIRNAME = ".agentcli"
MANIFEST_FILENAME = "repo-intel.json"
WORKSPACE_REGISTRY_PATH = STATE_DIR / "workspace-graph.json"
DEFAULT_GRAPH_DIRNAME = "graphify-out"
DEFAULT_OBSIDIAN_ROOT = str(CODEX_HOME / "docs" / "repo-intel-obsidian")
AGENTS_START = "<!-- agentcli:repo-intel:start -->"
AGENTS_END = "<!-- agentcli:repo-intel:end -->"
GITIGNORE_START = "# agentcli:repo-hygiene:start"
GITIGNORE_END = "# agentcli:repo-hygiene:end"
GRAPHIFYIGNORE_TEMPLATE = "\n".join(
    [
        "# Agent CLI OS repo-intel defaults",
        ".git/",
        ".agentcli/",
        f".{PUBLIC_DOCS_DIRNAME}/",
        "graphify-out/",
        "node_modules/",
        "dist/",
        "build/",
        "coverage/",
        ".next/",
        ".venv/",
        "__pycache__/",
        "*.pyc",
        "",
    ]
)
GITIGNORE_TEMPLATE = "\n".join(
    [
        GITIGNORE_START,
        "# Agent CLI OS repo hygiene defaults",
        ".agentcli/",
        ".codex-workflows/",
        "graphify-out/",
        ".playwright-cli/",
        "playwright-report/",
        "test-results/",
        "coverage/",
        ".pytest_cache/",
        ".mypy_cache/",
        ".ruff_cache/",
        ".tmp/",
        ".tmp-plugin-eval/",
        "output/playwright/",
        "*.log",
        "logs/",
        "tmp/",
        "temp/",
        GITIGNORE_END,
        "",
    ]
)
DEFAULT_SKIP_DIRS = {
    ".git",
    ".codex-workflows",
    ".agentcli",
    f".{PUBLIC_DOCS_DIRNAME}",
    ".playwright-cli",
    ".tmp-plugin-eval",
    ".tmp",
    ".pytest_cache",
    ".mypy_cache",
    "graphify-out",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    ".venv",
    "venv",
    "__pycache__",
}
DEFAULT_SKIP_FILENAMES = {
    "AGENTS.md",
}
CODE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".rb",
    ".cs",
    ".kt",
    ".kts",
    ".scala",
    ".php",
    ".swift",
    ".lua",
    ".zig",
    ".ps1",
    ".ex",
    ".exs",
    ".m",
    ".mm",
    ".jl",
    ".vue",
    ".svelte",
    ".dart",
    ".sh",
    ".bash",
    ".zsh",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".jsonc",
    ".ini",
    ".cfg",
    ".lock",
}
SEMANTIC_EXTENSIONS = {
    ".md",
    ".mdx",
    ".txt",
    ".rst",
    ".html",
    ".pdf",
    ".docx",
    ".xlsx",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".svg",
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".avi",
    ".m4v",
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
}
OK_STATES = {"fresh", "disabled"}


def _path_candidate(repo: str | Path | None = None) -> Path:
    path = Path(repo).resolve() if repo else Path.cwd().resolve()
    return path if path.is_dir() else path.parent


def detect_repo_root(repo: str | Path | None = None) -> Path | None:
    candidate = _path_candidate(repo)
    if candidate.exists():
        result = run_command(["git", "rev-parse", "--show-toplevel"], cwd=candidate, timeout=20)
        if result["ok"]:
            raw = (result["stdout"] or "").strip()
            if raw:
                resolved = Path(raw).resolve()
                if resolved.exists():
                    return resolved
    for current in (candidate, *candidate.parents):
        if not current.exists():
            continue
        if (current / ".git").exists():
            return current
    return None


def _repo_root(repo: str | Path | None = None) -> Path:
    return detect_repo_root(repo) or _path_candidate(repo)


def _repo_intel_config(repo_root: Path) -> dict[str, Any]:
    effective = effective_config(repo_root)
    defaults = {
        "enabled": True,
        "graph_engine": "graphify",
        "graph_dir": DEFAULT_GRAPH_DIRNAME,
        "manifest_dir": MANIFEST_DIRNAME,
        "write_agents_hint": True,
        "obsidian_export": False,
        "obsidian_vault_root": DEFAULT_OBSIDIAN_ROOT,
        "update_policy": "ensure",
        "hooks_default": "off",
    }
    payload = defaults.copy()
    payload.update(effective.get("repo_intel", {}))
    return payload


def repo_intel_manifest_path(repo: str | Path | None = None) -> Path:
    repo_root = _repo_root(repo)
    config = _repo_intel_config(repo_root)
    return repo_root / str(config.get("manifest_dir") or MANIFEST_DIRNAME) / MANIFEST_FILENAME


def _graph_dir(repo_root: Path, config: dict[str, Any]) -> Path:
    return repo_root / str(config.get("graph_dir") or DEFAULT_GRAPH_DIRNAME)


def repo_intel_graph_paths(repo: str | Path | None = None) -> dict[str, str]:
    repo_root = _repo_root(repo)
    config = _repo_intel_config(repo_root)
    graph_dir = _graph_dir(repo_root, config)
    return {
        "graph_dir": str(graph_dir),
        "graph_json": str(graph_dir / "graph.json"),
        "graph_report": str(graph_dir / "GRAPH_REPORT.md"),
        "graph_html": str(graph_dir / "graph.html"),
    }


def _obsidian_export_path(repo_root: Path, config: dict[str, Any]) -> str | None:
    if not config.get("obsidian_export"):
        return None
    root = str(config.get("obsidian_vault_root") or "").strip()
    if not root:
        return None
    return str(Path(root).expanduser().resolve() / repo_root.name)


def detect_graphify_runtime() -> dict[str, Any]:
    path = command_path("graphify")
    record: dict[str, Any] = {
        "name": "graphify",
        "command": "graphify",
        "path": path,
        "installed": bool(path),
        "status": "missing",
        "version": None,
    }
    if not path:
        return record
    help_result = run_command(["graphify", "--help"], timeout=20)
    if help_result["ok"]:
        first_line = (help_result["stdout"] or help_result["stderr"] or "").splitlines()
        record["status"] = "ok"
        record["version"] = first_line[0] if first_line else "graphify installed"
    else:
        record["status"] = "degraded"
        record["runtime_error"] = help_result["stderr"] or help_result["stdout"] or "failed to execute graphify --help"
    return record


def detect_obsidian_runtime() -> dict[str, Any]:
    candidates = []
    direct = command_path("obsidian")
    if direct:
        candidates.append(Path(direct))
    local = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    candidates.extend(
        [
            local / "Programs" / "Obsidian" / "Obsidian.exe",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Obsidian" / "Obsidian.exe",
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Obsidian" / "Obsidian.exe",
        ]
    )
    found = next((candidate for candidate in candidates if candidate.exists()), None)
    return {
        "name": "obsidian",
        "command": "obsidian",
        "path": str(found) if found else None,
        "installed": bool(found),
        "status": "ok" if found else "missing",
    }


def trusted_repo_paths() -> list[Path]:
    payload = _load_toml(CONFIG_PATH)
    projects = payload.get("projects", {})
    results: list[Path] = []
    for raw_path, meta in projects.items():
        if not isinstance(meta, dict) or meta.get("trust_level") != "trusted":
            continue
        candidate = Path(raw_path).expanduser().resolve()
        if candidate.exists() and (candidate / ".git").exists():
            results.append(candidate)
    unique = {str(path): path for path in results}
    return [unique[key] for key in sorted(unique)]


def _trusted_repo_root_strings() -> set[str]:
    return {str(path) for path in trusted_repo_paths()}


def discovered_repo_paths() -> list[Path]:
    payload = load_json(COMPUTER_GRAPH_PATH, default={})
    repos: list[Path] = []
    for record in payload.get("repos", []):
        if not isinstance(record, dict):
            continue
        if not record.get("audit_candidate", True):
            continue
        raw_path = record.get("path")
        if not isinstance(raw_path, str):
            continue
        path = Path(raw_path).expanduser().resolve()
        if path.exists():
            repos.append(path)
    unique = {str(path): path for path in repos}
    return [unique[key] for key in sorted(unique)]


def _load_ignore_patterns(repo_root: Path) -> list[str]:
    ignore_path = repo_root / ".graphifyignore"
    if not ignore_path.exists():
        return []
    patterns: list[str] = []
    for raw_line in ignore_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line.replace("\\", "/"))
    return patterns


def _matches_ignore(rel_path: str, patterns: list[str]) -> bool:
    rel_value = rel_path.replace("\\", "/")
    rel_parts = rel_value.split("/")
    basename = rel_parts[-1]
    for pattern in patterns:
        if pattern.endswith("/"):
            prefix = pattern[:-1].strip("/")
            if prefix and (rel_value == prefix or rel_value.startswith(prefix + "/")):
                return True
            continue
        if "/" not in pattern and fnmatch.fnmatch(basename, pattern):
            return True
        if fnmatch.fnmatch(rel_value, pattern) or fnmatch.fnmatch(rel_value, f"**/{pattern}"):
            return True
    return False


def _classify_path(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in CODE_EXTENSIONS:
        return "code"
    if suffix in SEMANTIC_EXTENSIONS:
        return "semantic"
    return None


def _iter_repo_files(repo_root: Path) -> tuple[list[Path], list[Path]]:
    patterns = _load_ignore_patterns(repo_root)
    code_files: list[Path] = []
    semantic_files: list[Path] = []
    for current_root, dirs, files in os.walk(repo_root):
        current = Path(current_root)
        rel_dir = "." if current == repo_root else current.relative_to(repo_root).as_posix()
        filtered_dirs: list[str] = []
        for dirname in list(dirs):
            if dirname in DEFAULT_SKIP_DIRS:
                continue
            rel = dirname if rel_dir == "." else f"{rel_dir}/{dirname}"
            if _matches_ignore(rel, patterns):
                continue
            filtered_dirs.append(dirname)
        dirs[:] = filtered_dirs
        for filename in files:
            if filename in DEFAULT_SKIP_FILENAMES:
                continue
            rel = filename if rel_dir == "." else f"{rel_dir}/{filename}"
            if _matches_ignore(rel, patterns):
                continue
            path = current / filename
            category = _classify_path(path)
            if category == "code":
                code_files.append(path)
            elif category == "semantic":
                semantic_files.append(path)
    return code_files, semantic_files


def _fingerprint(files: list[Path], repo_root: Path) -> dict[str, Any]:
    digest = hashlib.sha1()
    samples: list[str] = []
    for path in sorted(files):
        try:
            stat = path.stat()
        except OSError:
            continue
        rel = path.relative_to(repo_root).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
        if len(samples) < 5:
            samples.append(rel)
    return {"sha1": digest.hexdigest(), "count": len(files), "samples": samples}


def _hash_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def _config_hash(config: dict[str, Any]) -> str:
    graph_shaping = {
        "enabled": bool(config.get("enabled", True)),
        "graph_engine": str(config.get("graph_engine") or "graphify"),
        "graph_dir": str(config.get("graph_dir") or DEFAULT_GRAPH_DIRNAME),
        "manifest_dir": str(config.get("manifest_dir") or MANIFEST_DIRNAME),
        "obsidian_export": bool(config.get("obsidian_export", False)),
        "obsidian_vault_root": str(config.get("obsidian_vault_root") or ""),
    }
    stable = json.dumps(graph_shaping, sort_keys=True, separators=(",", ":"))
    return _hash_text(stable)


def _ignore_hash(repo_root: Path) -> str:
    ignore_path = repo_root / ".graphifyignore"
    if not ignore_path.exists():
        return _hash_text("")
    return _hash_text(ignore_path.read_text(encoding="utf-8"))


def _git_value(repo_root: Path, *args: str) -> str | None:
    result = run_command(["git", *args], cwd=repo_root, timeout=20)
    if not result["ok"]:
        return None
    value = (result["stdout"] or "").strip()
    return value or None


def _artifact_readability(graph_json: Path, graph_report: Path) -> tuple[bool, str | None]:
    if not graph_json.exists() or not graph_report.exists():
        return False, "required graph artifacts are missing"
    try:
        json.loads(graph_json.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"graph.json is unreadable: {exc}"
    try:
        report_text = graph_report.read_text(encoding="utf-8").strip()
    except Exception as exc:
        return False, f"GRAPH_REPORT.md is unreadable: {exc}"
    if not report_text:
        return False, "GRAPH_REPORT.md is empty"
    return True, None


def _recommended_action(status: str) -> str:
    mapping = {
        "missing": f"{PUBLIC_COMMAND} repo-intel ensure",
        "stale_code": f"{PUBLIC_COMMAND} repo-intel update --code-only",
        "stale_semantic": f"{PUBLIC_COMMAND} repo-intel update --semantic",
        "stale_config": f"{PUBLIC_COMMAND} repo-intel update --full",
        "broken": f"{PUBLIC_COMMAND} repo-intel ensure",
        "disabled": "Enable repo_intel in config before using repo-intel commands.",
        "fresh": "No action needed.",
        "building": "Wait for the current build to finish or inspect the last_error field.",
    }
    return mapping.get(status, f"{PUBLIC_COMMAND} repo-intel status")


def _repo_intel_policy(repo_root: Path, *, config: dict[str, Any], status: str) -> dict[str, Any]:
    trusted = str(repo_root) in _trusted_repo_root_strings()
    enabled = bool(config.get("enabled", True))
    update_policy = str(config.get("update_policy") or "ensure").strip().lower()
    auto_ensure_on_entry = bool(enabled and trusted and update_policy == "ensure")
    default_mode = "repo-first" if enabled else "raw-search-fallback"
    graph_first_default = bool(enabled)
    agent_path: list[str] = []

    if not enabled:
        agent_path.extend(
            [
                "Repo-intel is disabled here, so use targeted raw-file reads inside the current repo.",
                f"Use `{PUBLIC_COMMAND} computer-intel ...` only when the target repo is unknown or the task is explicitly cross-repo.",
                "Keep the current local branch as the canonical place for commits and pushes; do not create a side branch unless the task explicitly needs it.",
            ]
        )
    else:
        agent_path.append("Treat the current repo as the default working universe; do not jump to whole-laptop search first.")
        if status == "fresh":
            agent_path.extend(
                [
                    "Read `graphify-out/GRAPH_REPORT.md` before broad raw-file search.",
                    f"Prefer `{PUBLIC_COMMAND} repo-intel query \"<question>\"` or `{PUBLIC_COMMAND} repo-intel serve` for architecture and path questions before wide grep.",
                    "Open targeted raw files only after graph routing or when exact verification/editing is needed.",
                ]
            )
        else:
            ensure_line = (
                f"Run `{PUBLIC_COMMAND} repo-intel ensure` before broad raw-file search so this repo can stay graph-first by default."
                if auto_ensure_on_entry or trusted
                else f"Run `{PUBLIC_COMMAND} repo-intel status` and `{PUBLIC_COMMAND} repo-intel ensure` before broad raw-file search when this repo should stay graph-backed."
            )
            agent_path.extend(
                [
                    ensure_line,
                    "Until repo-intel is healthy, stay inside the current repo with targeted raw-file reads instead of escalating to machine-wide search.",
                ]
            )
        agent_path.append(f"Use `{PUBLIC_COMMAND} computer-intel ...` only when the target repo is unknown or the task is explicitly cross-repo.")
        agent_path.append(f"If `{PUBLIC_COMMAND}` or `loopsmith` is not on PATH, repair the public launcher with the bundle-local `agentctl.py doctor --fix` path before continuing; do not replace a requested loop with docs-only tracking.")
        agent_path.append("Treat the current local branch as canonical for normal solo work; do not create or switch branches just to preserve agent changes.")
        agent_path.append("Treat Codex-managed worktrees as temporary isolation only; if work should be kept and pushed, continue from the local checkout so local commits and pushes do not require merging a worktree branch back.")
        agent_path.append("Create a separate branch only when explicitly requested or when a real PR flow or parallel-agent workflow needs branch isolation.")

    return {
        "default_mode": default_mode,
        "trusted_repo": trusted,
        "graph_first_default": graph_first_default,
        "update_policy": update_policy,
        "auto_ensure_on_entry": auto_ensure_on_entry,
        "computer_intel_role": "exception-only",
        "agent_path": agent_path,
    }


def _default_workspace_registry() -> dict[str, Any]:
    return {
        "schema_version": WORKSPACE_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "repos": [],
    }


def _normalize_workspace_registry(payload: Any) -> dict[str, Any]:
    default = _default_workspace_registry()
    if not isinstance(payload, dict):
        return default
    repos = payload.get("repos")
    cleaned_repos: list[dict[str, Any]] = []
    if isinstance(repos, list):
        for item in repos:
            if not isinstance(item, dict):
                continue
            repo_root = item.get("repo_root")
            if not isinstance(repo_root, str) or not repo_root.strip():
                continue
            cleaned_repos.append(item)
    return {
        "schema_version": WORKSPACE_SCHEMA_VERSION,
        "generated_at": payload.get("generated_at") if isinstance(payload.get("generated_at"), str) else default["generated_at"],
        "repos": cleaned_repos,
    }


def _parse_workspace_registry(raw: str) -> tuple[dict[str, Any], bool]:
    try:
        return _normalize_workspace_registry(json.loads(raw)), False
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        stripped = raw.lstrip()
        try:
            payload, end = decoder.raw_decode(stripped)
        except json.JSONDecodeError:
            return _default_workspace_registry(), True
        trailing = stripped[end:].strip()
        return _normalize_workspace_registry(payload), bool(trailing)


def _workspace_registry() -> dict[str, Any]:
    path = WORKSPACE_REGISTRY_PATH.resolve()
    default = _default_workspace_registry()
    if not path.exists():
        return default
    registry, repaired = _parse_workspace_registry(path.read_text(encoding="utf-8"))
    if repaired:
        save_json(path, registry)
    return registry


def _save_workspace_registry(payload: dict[str, Any]) -> None:
    payload["generated_at"] = utc_now()
    save_json(WORKSPACE_REGISTRY_PATH, payload)


def _workspace_entry(payload: dict[str, Any]) -> dict[str, Any]:
    manifest = payload.get("manifest") or {}
    return {
        "repo_root": payload["repo_root"],
        "repo_name": payload["repo_name"],
        "status": payload["status"],
        "graph_json": payload["graph_paths"]["graph_json"],
        "graph_report": payload["graph_paths"]["graph_report"],
        "manifest_path": payload["manifest_path"],
        "graphify_version": manifest.get("graphify_version"),
        "last_successful_build_at": manifest.get("last_successful_build_at"),
        "obsidian_export_path": manifest.get("obsidian_export_path"),
        "last_audited_at": utc_now(),
    }


def _sync_workspace_registry(status_payload: dict[str, Any]) -> None:
    trusted_roots = _trusted_repo_root_strings()
    registry = _workspace_registry()
    repos = {
        item["repo_root"]: item
        for item in registry.get("repos", [])
        if isinstance(item, dict) and item.get("repo_root") in trusted_roots
    }
    if status_payload["repo_root"] in trusted_roots:
        repos[status_payload["repo_root"]] = _workspace_entry(status_payload)
    registry["schema_version"] = WORKSPACE_SCHEMA_VERSION
    registry["repos"] = [repos[key] for key in sorted(repos)]
    _save_workspace_registry(registry)


def _repo_intel_manifest(
    repo_root: Path,
    *,
    config: dict[str, Any],
    graphify: dict[str, Any],
    code_fingerprint: dict[str, Any],
    semantic_fingerprint: dict[str, Any],
    graph_paths: dict[str, str],
    obsidian_export_path: str | None,
    last_error: str | None = None,
    last_successful_build_at: str | None = None,
    last_successful_code_build_at: str | None = None,
    last_successful_semantic_build_at: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "repo_root": str(repo_root),
        "repo_name": repo_root.name,
        "graphify_version": graphify.get("version"),
        "status": "fresh",
        "last_successful_build_at": last_successful_build_at or utc_now(),
        "last_successful_code_build_at": last_successful_code_build_at or utc_now(),
        "last_successful_semantic_build_at": last_successful_semantic_build_at or utc_now(),
        "last_built_commit": _git_value(repo_root, "rev-parse", "HEAD"),
        "last_built_branch": _git_value(repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
        "graph_paths": graph_paths,
        "obsidian_export_path": obsidian_export_path,
        "ignore_hash": _ignore_hash(repo_root),
        "config_hash": _config_hash(config),
        "code_fingerprint": code_fingerprint,
        "semantic_fingerprint": semantic_fingerprint,
        "last_error": last_error,
    }


def _ensure_graphifyignore(repo_root: Path) -> Path | None:
    path = repo_root / ".graphifyignore"
    if path.exists():
        return None
    path.write_text(GRAPHIFYIGNORE_TEMPLATE, encoding="utf-8")
    return path


def _gitignore_hygiene_current(repo_root: Path) -> bool:
    path = repo_root / ".gitignore"
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    if GITIGNORE_START not in content or GITIGNORE_END not in content:
        return False
    before, remainder = content.split(GITIGNORE_START, 1)
    current_block, _ = remainder.split(GITIGNORE_END, 1)
    actual = (GITIGNORE_START + current_block + GITIGNORE_END).strip()
    expected = GITIGNORE_TEMPLATE.strip()
    return actual == expected


def _ensure_gitignore_hygiene(repo_root: Path) -> Path | None:
    path = repo_root / ".gitignore"
    block = GITIGNORE_TEMPLATE.strip()
    if path.exists():
        content = path.read_text(encoding="utf-8")
        if GITIGNORE_START in content and GITIGNORE_END in content:
            before, remainder = content.split(GITIGNORE_START, 1)
            _, after = remainder.split(GITIGNORE_END, 1)
            updated = before.rstrip() + "\n\n" + block + "\n" + after.lstrip("\n")
            if updated == content:
                return None
            path.write_text(updated.rstrip() + "\n", encoding="utf-8")
            return path
        if block in content:
            return None
        path.write_text(content.rstrip() + "\n\n" + block + "\n", encoding="utf-8")
        return path
    path.write_text(block + "\n", encoding="utf-8")
    return path


def _repo_intel_agents_block() -> str:
    return "\n".join(
        [
            AGENTS_START,
            "## Repo Intelligence",
            "",
            f"- Treat the current repo as the default working universe; use `{PUBLIC_COMMAND} computer-intel ...` only when the target repo is unknown or the task is explicitly cross-repo.",
            f"- On repo entry or before broad raw-file search, run `{PUBLIC_COMMAND} repo-intel status`; if repo-intel is missing, stale, or broken for a trusted repo, run `{PUBLIC_COMMAND} repo-intel ensure`.",
            "- If `graphify-out/GRAPH_REPORT.md` exists and repo-intel is healthy, read it before broad raw-file search.",
            f"- Prefer `{PUBLIC_COMMAND} repo-intel query \"<question>\"` or `{PUBLIC_COMMAND} repo-intel serve` for architecture and path questions before wide grep; open targeted raw files only after graph routing.",
            f"- If `{PUBLIC_COMMAND}` or `loopsmith` is not available on PATH, repair the public launcher with the bundle-local `agentctl.py doctor --fix` path before continuing; do not replace requested loops with docs-only tracking.",
            "- Treat the current local branch as the canonical place for normal solo work; do not create or switch branches just to preserve agent changes.",
            "- Treat Codex-managed worktrees as temporary isolation only; if work should be kept and pushed, continue from the local checkout so local commits and pushes do not require merging a worktree branch back.",
            "- Create a separate branch only when explicitly requested or when a real PR flow or parallel-agent workflow needs branch isolation.",
            AGENTS_END,
            "",
        ]
    )


def _agents_hint_current(repo_root: Path, config: dict[str, Any]) -> bool:
    if not config.get("write_agents_hint", True):
        return True
    path = repo_root / "AGENTS.md"
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    if AGENTS_START not in content or AGENTS_END not in content:
        return False
    before, remainder = content.split(AGENTS_START, 1)
    current_block, _ = remainder.split(AGENTS_END, 1)
    actual = (AGENTS_START + current_block + AGENTS_END).strip()
    expected = _repo_intel_agents_block().strip()
    return actual == expected


def _ensure_agents_hint(repo_root: Path) -> Path | None:
    path = repo_root / "AGENTS.md"
    block = _repo_intel_agents_block().strip()
    if path.exists():
        content = path.read_text(encoding="utf-8")
        if AGENTS_START in content and AGENTS_END in content:
            before, remainder = content.split(AGENTS_START, 1)
            _, after = remainder.split(AGENTS_END, 1)
            updated = before.rstrip() + "\n\n" + block + "\n" + after.lstrip("\n")
            if updated == content:
                return None
            path.write_text(updated.rstrip() + "\n", encoding="utf-8")
            return path
        if block in content:
            return None
        path.write_text(content.rstrip() + "\n\n" + block + "\n", encoding="utf-8")
        return path
    path.write_text(block + "\n", encoding="utf-8")
    return path


def repo_intel_status(repo: str | Path | None = None) -> dict[str, Any]:
    repo_root = _repo_root(repo)
    config = _repo_intel_config(repo_root)
    graphify = detect_graphify_runtime()
    obsidian = detect_obsidian_runtime()
    graph_paths = repo_intel_graph_paths(repo_root)
    graph_json = Path(graph_paths["graph_json"])
    graph_report = Path(graph_paths["graph_report"])
    manifest_path = repo_intel_manifest_path(repo_root)
    manifest = load_json(manifest_path, default={})
    code_files, semantic_files = _iter_repo_files(repo_root)
    code_fingerprint = _fingerprint(code_files, repo_root)
    semantic_fingerprint = _fingerprint(semantic_files, repo_root)
    ignore_hash = _ignore_hash(repo_root)
    config_hash = _config_hash(config)
    obsidian_export_path = _obsidian_export_path(repo_root, config)

    status = "missing"
    detail = "Repo graph has not been built yet."
    artifact_ok, artifact_error = _artifact_readability(graph_json, graph_report)

    if not config.get("enabled", True):
        status = "disabled"
        detail = "Repo intelligence is disabled in config."
    elif manifest.get("status") == "building":
        status = "building"
        detail = "A repo-intel build is already marked as in progress."
    elif not graph_json.exists() or not graph_report.exists():
        status = "missing"
        detail = artifact_error or "Required graph artifacts are missing."
    elif not artifact_ok:
        status = "broken"
        detail = artifact_error or "Graph artifacts are unreadable."
    elif not manifest_path.exists():
        status = "broken"
        detail = "Graph artifacts exist but the repo-intel manifest is missing."
    elif manifest.get("schema_version") != SCHEMA_VERSION:
        status = "broken"
        detail = "Repo-intel manifest schema is unsupported."
    elif not _gitignore_hygiene_current(repo_root):
        status = "stale_config"
        detail = "Repo hygiene `.gitignore` defaults are missing or outdated."
    elif not _agents_hint_current(repo_root, config):
        status = "stale_config"
        detail = "Repo-intel AGENTS guidance is missing or outdated."
    elif manifest.get("ignore_hash") != ignore_hash or manifest.get("config_hash") != config_hash:
        status = "stale_config"
        detail = "Repo-intel config or ignore rules changed since the last successful build."
    elif manifest.get("graphify_version") != graphify.get("version"):
        status = "stale_config"
        detail = "Graphify runtime signature changed since the last successful build."
    elif (manifest.get("code_fingerprint") or {}).get("sha1") != code_fingerprint.get("sha1"):
        status = "stale_code"
        detail = "Code-bearing files changed since the last successful build."
    elif (manifest.get("semantic_fingerprint") or {}).get("sha1") != semantic_fingerprint.get("sha1"):
        status = "stale_semantic"
        detail = "Docs or semantic sources changed since the last successful build."
    else:
        status = "fresh"
        detail = "Repo graph exists and matches the current repo state."
    policy = _repo_intel_policy(repo_root, config=config, status=status)

    payload = {
        "kind": "repo-intel-status",
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "repo_root": str(repo_root),
        "repo_name": repo_root.name,
        "status": status,
        "trusted": policy["trusted_repo"],
        "detail": detail,
        "recommended_action": _recommended_action(status),
        "manifest_path": str(manifest_path),
        "graph_paths": graph_paths,
        "graphify_runtime": graphify,
        "obsidian_runtime": obsidian,
        "config": {
            "enabled": bool(config.get("enabled", True)),
            "graph_dir": str(config.get("graph_dir") or DEFAULT_GRAPH_DIRNAME),
            "manifest_dir": str(config.get("manifest_dir") or MANIFEST_DIRNAME),
            "update_policy": str(config.get("update_policy") or "ensure"),
            "write_agents_hint": bool(config.get("write_agents_hint", True)),
            "obsidian_export": bool(config.get("obsidian_export", False)),
            "obsidian_vault_root": str(config.get("obsidian_vault_root") or ""),
        },
        "artifacts": {
            "graph_json_exists": graph_json.exists(),
            "graph_report_exists": graph_report.exists(),
            "graph_html_exists": Path(graph_paths["graph_html"]).exists(),
            "artifact_health": "ok" if artifact_ok else "error",
            "gitignore_path": str(repo_root / ".gitignore"),
            "gitignore_hygiene": "ok" if _gitignore_hygiene_current(repo_root) else "drift",
        },
        "fingerprints": {
            "code": code_fingerprint,
            "semantic": semantic_fingerprint,
            "ignore_hash": ignore_hash,
            "config_hash": config_hash,
        },
        "manifest": manifest if isinstance(manifest, dict) else {},
        "obsidian_export_path": obsidian_export_path,
        "policy": policy,
    }
    _sync_workspace_registry(payload)
    return payload


def _graphify_build_command(repo_root: Path, config: dict[str, Any]) -> list[str]:
    python_command = _graphify_python_command(repo_root, config)
    if python_command is None:
        raise RuntimeError("Could not resolve a Python runtime that can import Graphify for a repo-intel build.")
    return python_command


def _graphify_update_command(repo_root: Path) -> list[str]:
    return ["graphify", "update", str(repo_root)]


def _graphify_python_command(repo_root: Path, config: dict[str, Any]) -> list[str] | None:
    export_path = _obsidian_export_path(repo_root, config) or ""
    inline = (
        "import json, sys; "
        "from pathlib import Path; "
        "from graphify.watch import _rebuild_code; "
        "from graphify.export import to_obsidian; "
        "from networkx.readwrite import json_graph; "
        "sys.setrecursionlimit(max(sys.getrecursionlimit(), 50000)); "
        "root = Path(sys.argv[1]).resolve(); "
        "obsidian_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 and sys.argv[2] else None; "
        "ok = _rebuild_code(root); "
        "sys.exit(1) if not ok else None; "
        "graph_path = root / 'graphify-out' / 'graph.json'; "
        "raw = json.loads(graph_path.read_text(encoding='utf-8')); "
        "G = json_graph.node_link_graph(raw, edges='links') if 'links' in raw else json_graph.node_link_graph(raw); "
        "communities = {}; "
        "[communities.setdefault(data.get('community'), []).append(nid) for nid, data in G.nodes(data=True) if data.get('community') is not None]; "
        "labels = {cid: f'Community {cid}' for cid in communities}; "
        "(obsidian_dir.mkdir(parents=True, exist_ok=True), to_obsidian(G, communities, str(obsidian_dir), community_labels=labels or None)) if obsidian_dir else None"
    )
    candidates = _python_candidates_for_graphify(command_path("graphify"))
    if not candidates:
        return None
    return [str(candidates[0]), "-c", inline, str(repo_root), export_path]


def _graphify_query_command(repo_root: Path, question: str, *, budget: int, dfs: bool) -> list[str]:
    graph_json = Path(repo_intel_graph_paths(repo_root)["graph_json"])
    command = ["graphify", "query", question, "--graph", str(graph_json), "--budget", str(budget)]
    if dfs:
        command.append("--dfs")
    return command


def _python_candidates_for_graphify(graphify_path: str | None) -> list[Path]:
    candidates = [Path(sys.executable)]
    if graphify_path:
        graphify_bin = Path(graphify_path)
        candidates.extend(
            [
                graphify_bin.parent / "python.exe",
                graphify_bin.parent / "python",
                graphify_bin.parent / "python3.exe",
                graphify_bin.parent / "python3",
                graphify_bin.parent.parent / "python.exe",
                graphify_bin.parent.parent / "python",
            ]
        )
    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        candidate_str = str(candidate)
        if candidate_str in seen or not candidate.exists():
            continue
        seen.add(candidate_str)
        unique.append(candidate)
    return unique


def _graphify_serve_command(graphify: dict[str, Any], graph_json: Path) -> list[str] | None:
    for candidate in _python_candidates_for_graphify(graphify.get("path")):
        result = run_command([str(candidate), "-c", "import graphify.serve"], timeout=20)
        if result["ok"]:
            return [str(candidate), "-m", "graphify.serve", str(graph_json)]
    return None


def _stream_command(command: list[str], *, cwd: Path) -> dict[str, Any]:
    try:
        completed = subprocess.run(command, cwd=str(cwd), check=False)
    except FileNotFoundError:
        return {"ok": False, "returncode": 127, "stderr": "command not found"}
    return {"ok": completed.returncode == 0, "returncode": completed.returncode, "stderr": ""}


def _artifacts_refreshed_since(repo_root: Path, *, started_ns: int) -> bool:
    graph_paths = repo_intel_graph_paths(repo_root)
    graph_json = Path(graph_paths["graph_json"])
    graph_report = Path(graph_paths["graph_report"])
    artifact_ok, _ = _artifact_readability(graph_json, graph_report)
    if not artifact_ok:
        return False
    try:
        return graph_json.stat().st_mtime_ns >= started_ns and graph_report.stat().st_mtime_ns >= started_ns
    except OSError:
        return False


def _write_building_manifest(repo_root: Path, *, config: dict[str, Any], graphify: dict[str, Any]) -> Path:
    manifest_path = repo_intel_manifest_path(repo_root)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "repo_root": str(repo_root),
        "repo_name": repo_root.name,
        "graphify_version": graphify.get("version"),
        "status": "building",
        "last_error": None,
        "graph_paths": repo_intel_graph_paths(repo_root),
        "ignore_hash": _ignore_hash(repo_root),
        "config_hash": _config_hash(config),
    }
    return save_json(manifest_path, payload)


def _write_broken_manifest(repo_root: Path, *, config: dict[str, Any], graphify: dict[str, Any], error: str) -> Path:
    manifest_path = repo_intel_manifest_path(repo_root)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "repo_root": str(repo_root),
        "repo_name": repo_root.name,
        "graphify_version": graphify.get("version"),
        "status": "broken",
        "last_error": error,
        "graph_paths": repo_intel_graph_paths(repo_root),
        "ignore_hash": _ignore_hash(repo_root),
        "config_hash": _config_hash(config),
    }
    return save_json(manifest_path, payload)


def _persist_success_manifest(repo_root: Path, *, config: dict[str, Any], graphify: dict[str, Any], mode: str) -> dict[str, Any]:
    code_files, semantic_files = _iter_repo_files(repo_root)
    code_fingerprint = _fingerprint(code_files, repo_root)
    semantic_fingerprint = _fingerprint(semantic_files, repo_root)
    graph_paths = repo_intel_graph_paths(repo_root)
    previous = load_json(repo_intel_manifest_path(repo_root), default={})
    now = utc_now()
    manifest = _repo_intel_manifest(
        repo_root,
        config=config,
        graphify=graphify,
        code_fingerprint=code_fingerprint,
        semantic_fingerprint=semantic_fingerprint,
        graph_paths=graph_paths,
        obsidian_export_path=_obsidian_export_path(repo_root, config),
        last_error=None,
        last_successful_build_at=now,
        last_successful_code_build_at=now,
        last_successful_semantic_build_at=(previous.get("last_successful_semantic_build_at") if mode == "code" else now),
    )
    if mode == "code" and previous.get("last_successful_semantic_build_at"):
        manifest["last_successful_semantic_build_at"] = previous["last_successful_semantic_build_at"]
    save_json(repo_intel_manifest_path(repo_root), manifest)
    return manifest


def repo_intel_ensure(repo: str | Path | None = None) -> dict[str, Any]:
    repo_root = _repo_root(repo)
    config = _repo_intel_config(repo_root)
    created: list[str] = []
    if (created_path := _ensure_graphifyignore(repo_root)) is not None:
        created.append(str(created_path))
    if (created_path := _ensure_gitignore_hygiene(repo_root)) is not None:
        created.append(str(created_path))
    if config.get("write_agents_hint", True):
        agents_path = _ensure_agents_hint(repo_root)
        if agents_path is not None:
            created.append(str(agents_path))

    before = repo_intel_status(repo_root)
    graphify = before["graphify_runtime"]
    if before["status"] == "disabled":
        return {**before, "kind": "repo-intel-ensure", "action": "noop", "created": created}
    if before["status"] == "fresh":
        return {**before, "kind": "repo-intel-ensure", "action": "noop", "created": created}
    if graphify.get("status") != "ok":
        return {
            **before,
            "kind": "repo-intel-ensure",
            "action": "blocked",
            "created": created,
            "detail": "Graphify is required to build or refresh repo intelligence for this repo.",
        }

    mode = "code" if before["status"] == "stale_code" else "full"
    if mode == "code" and not config.get("obsidian_export"):
        command = _graphify_update_command(repo_root)
    else:
        try:
            command = _graphify_build_command(repo_root, config)
        except RuntimeError as exc:
            return {
                **before,
                "kind": "repo-intel-ensure",
                "action": "blocked",
                "created": created,
                "detail": str(exc),
            }
    _write_building_manifest(repo_root, config=config, graphify=graphify)
    build_started_ns = time.time_ns()
    result = _stream_command(command, cwd=repo_root)
    if not result["ok"]:
        if _artifacts_refreshed_since(repo_root, started_ns=build_started_ns):
            manifest = _persist_success_manifest(repo_root, config=config, graphify=graphify, mode=mode)
            after = repo_intel_status(repo_root)
            return {
                **after,
                "kind": "repo-intel-ensure",
                "action": "updated-no-viz" if mode == "code" else "built-no-viz",
                "created": created,
                "command": command,
                "manifest": manifest,
            }
        _write_broken_manifest(repo_root, config=config, graphify=graphify, error=f"Graphify command failed with exit code {result['returncode']}.")
        failed = repo_intel_status(repo_root)
        return {
            **failed,
            "kind": "repo-intel-ensure",
            "action": "failed",
            "created": created,
            "command": command,
        }

    manifest = _persist_success_manifest(repo_root, config=config, graphify=graphify, mode=mode)
    after = repo_intel_status(repo_root)
    return {
        **after,
        "kind": "repo-intel-ensure",
        "action": "updated" if mode == "code" else "built",
        "created": created,
        "command": command,
        "manifest": manifest,
    }


def repo_intel_update(
    repo: str | Path | None = None,
    *,
    mode: str = "auto",
) -> dict[str, Any]:
    repo_root = _repo_root(repo)
    config = _repo_intel_config(repo_root)
    before = repo_intel_status(repo_root)
    graphify = before["graphify_runtime"]
    if before["status"] == "disabled":
        return {**before, "kind": "repo-intel-update", "action": "noop"}
    if graphify.get("status") != "ok":
        return {
            **before,
            "kind": "repo-intel-update",
            "action": "blocked",
            "detail": "Graphify is required to update repo intelligence.",
        }

    resolved_mode = mode
    if mode == "auto":
        if before["status"] == "fresh":
            return {**before, "kind": "repo-intel-update", "action": "noop"}
        if before["status"] == "stale_code":
            resolved_mode = "code"
        else:
            resolved_mode = "full"

    if resolved_mode == "semantic":
        resolved_mode = "full"
    if before["status"] == "missing" and resolved_mode == "code":
        resolved_mode = "full"

    if resolved_mode == "code" and not config.get("obsidian_export"):
        command = _graphify_update_command(repo_root)
    else:
        try:
            command = _graphify_build_command(repo_root, config)
        except RuntimeError as exc:
            return {
                **before,
                "kind": "repo-intel-update",
                "action": "blocked",
                "detail": str(exc),
            }
    _write_building_manifest(repo_root, config=config, graphify=graphify)
    build_started_ns = time.time_ns()
    result = _stream_command(command, cwd=repo_root)
    if not result["ok"]:
        if _artifacts_refreshed_since(repo_root, started_ns=build_started_ns):
            manifest = _persist_success_manifest(repo_root, config=config, graphify=graphify, mode=resolved_mode)
            after = repo_intel_status(repo_root)
            return {
                **after,
                "kind": "repo-intel-update",
                "action": "updated-no-viz" if resolved_mode == "code" else "rebuilt-no-viz",
                "command": command,
                "manifest": manifest,
            }
        _write_broken_manifest(repo_root, config=config, graphify=graphify, error=f"Graphify command failed with exit code {result['returncode']}.")
        failed = repo_intel_status(repo_root)
        return {**failed, "kind": "repo-intel-update", "action": "failed", "command": command}

    manifest = _persist_success_manifest(repo_root, config=config, graphify=graphify, mode=resolved_mode)
    after = repo_intel_status(repo_root)
    return {
        **after,
        "kind": "repo-intel-update",
        "action": "updated" if resolved_mode == "code" else "rebuilt",
        "command": command,
        "manifest": manifest,
    }


def repo_intel_query(
    question: str,
    *,
    repo: str | Path | None = None,
    budget: int = 1500,
    dfs: bool = False,
) -> dict[str, Any]:
    repo_root = _repo_root(repo)
    status_payload = repo_intel_status(repo_root)
    if status_payload["status"] in {"missing", "broken", "disabled", "building"}:
        return {
            **status_payload,
            "kind": "repo-intel-query",
            "action": "blocked",
            "question": question,
        }
    graphify = status_payload["graphify_runtime"]
    if graphify.get("status") != "ok":
        return {
            **status_payload,
            "kind": "repo-intel-query",
            "action": "blocked",
            "question": question,
            "detail": "Graphify CLI is required to query the repo graph.",
        }
    command = _graphify_query_command(repo_root, question, budget=budget, dfs=dfs)
    result = run_command(command, cwd=repo_root, timeout=120)
    return {
        **status_payload,
        "kind": "repo-intel-query",
        "action": "queried" if result["ok"] else "failed",
        "question": question,
        "budget": budget,
        "dfs": dfs,
        "command": command,
        "query_result": {
            "ok": result["ok"],
            "returncode": result["returncode"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
        },
    }


def repo_intel_serve(repo: str | Path | None = None, *, launch: bool = False) -> dict[str, Any]:
    repo_root = _repo_root(repo)
    status_payload = repo_intel_status(repo_root)
    graph_json = Path(status_payload["graph_paths"]["graph_json"])
    if status_payload["status"] in {"missing", "broken", "disabled", "building"}:
        return {
            **status_payload,
            "kind": "repo-intel-serve",
            "action": "blocked",
        }
    command = _graphify_serve_command(status_payload["graphify_runtime"], graph_json)
    if not command:
        return {
            **status_payload,
            "kind": "repo-intel-serve",
            "action": "blocked",
            "detail": "Could not resolve a Python runtime that can import graphify.serve.",
        }
    payload = {
        **status_payload,
        "kind": "repo-intel-serve",
        "action": "ready",
        "command": command,
    }
    if launch:
        raise SystemExit(subprocess.call(command, cwd=str(repo_root)))
    return payload


def repo_intel_audit(
    *,
    repo: str | Path | None = None,
    all_trusted: bool = False,
    all_discovered: bool = False,
    fix: bool = False,
) -> dict[str, Any]:
    if all_trusted or all_discovered:
        targets_map: dict[str, Path] = {}
        if all_trusted:
            for path in trusted_repo_paths():
                targets_map[str(path)] = path
        if all_discovered:
            for path in discovered_repo_paths():
                targets_map[str(path)] = path
        targets = [targets_map[key] for key in sorted(targets_map)]
    else:
        targets = [_repo_root(repo)]
    trusted_roots = _trusted_repo_root_strings()
    reports: list[dict[str, Any]] = []
    for target in targets:
        if fix and str(target) in trusted_roots:
            report = repo_intel_ensure(target)
        else:
            report = repo_intel_status(target)
            if fix and str(target) not in trusted_roots:
                report = {
                    **report,
                    "detail": f"{report['detail']} Auto-fix skipped because this repo is not trusted.",
                    "recommended_action": "agentcli repo-intel ensure --repo <path> after trusting the repo" if report["status"] != "disabled" else report["recommended_action"],
                }
        reports.append(
            {
                "repo_root": report["repo_root"],
                "repo_name": report["repo_name"],
                "status": report["status"],
                "detail": report["detail"],
                "recommended_action": report["recommended_action"],
                "graph_json": report["graph_paths"]["graph_json"],
                "trusted": str(target) in trusted_roots,
            }
        )
    counts: dict[str, int] = {}
    for report in reports:
        counts[report["status"]] = counts.get(report["status"], 0) + 1
    summary_status = "ok" if all(status in OK_STATES for status in counts) else "degraded"
    if "broken" in counts:
        summary_status = "error"
    return {
        "kind": "repo-intel-audit",
        "generated_at": utc_now(),
        "summary": {
            "status": summary_status,
            "repo_count": len(reports),
            "counts": counts,
            "fix": fix,
        },
        "repos": sorted(reports, key=lambda item: item["repo_root"].lower()),
        "workspace_registry_path": str(WORKSPACE_REGISTRY_PATH),
    }


def print_repo_intel_human(payload: dict[str, Any], *, as_json: bool = False) -> None:
    if as_json:
        print_json(payload)
        return

    kind = payload.get("kind", "repo-intel")
    if kind == "repo-intel-audit":
        summary = payload["summary"]
        print(f"Status: {summary['status']}")
        print(f"Repos: {summary['repo_count']}")
        for status, count in sorted(summary.get("counts", {}).items()):
            print(f"- {status}: {count}")
        print("")
        print("Repos")
        for item in payload.get("repos", []):
            print(f"- {item['repo_name']} [{item['status']}]")
            print(f"  - {item['detail']}")
            print(f"  - Next: {item['recommended_action']}")
        return

    print(f"Status: {payload['status']}")
    print(f"Repo: {payload['repo_name']}")
    print(f"Root: {payload['repo_root']}")
    print(f"Detail: {payload['detail']}")
    if payload.get("action"):
        print(f"Action: {payload['action']}")
    print(f"Next: {payload['recommended_action']}")
    print("")
    print("Agent posture")
    policy = payload.get("policy", {})
    print(f"- default mode: {policy.get('default_mode', 'unknown')}")
    print(f"- trusted repo: {payload.get('trusted', False)}")
    print(f"- update policy: {policy.get('update_policy', 'unknown')}")
    print(f"- computer-intel role: {policy.get('computer_intel_role', 'unknown')}")
    for item in policy.get("agent_path", []):
        print(f"- {item}")
    print("")
    print("Artifacts")
    print(f"- graph.json: {payload['graph_paths']['graph_json']}")
    print(f"- GRAPH_REPORT.md: {payload['graph_paths']['graph_report']}")
    print(f"- Manifest: {payload['manifest_path']}")
    print("")
    print("Runtime")
    print(f"- Graphify: {payload['graphify_runtime']['status']}")
    if payload["graphify_runtime"].get("path"):
        print(f"  - Path: {payload['graphify_runtime']['path']}")
    print(f"- Obsidian: {payload['obsidian_runtime']['status']}")
    if payload["obsidian_runtime"].get("path"):
        print(f"  - Path: {payload['obsidian_runtime']['path']}")
    if payload.get("command"):
        print("")
        print("Command")
        print(f"- {' '.join(payload['command'])}")
    if payload.get("created"):
        print("")
        print("Created")
        for item in payload["created"]:
            print(f"- {item}")
    if payload.get("query_result"):
        print("")
        print("Query")
        if payload["query_result"]["ok"]:
            print(payload["query_result"]["stdout"])
        else:
            print(payload["query_result"]["stderr"] or "query failed")
