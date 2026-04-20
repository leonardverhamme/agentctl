from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .branding import PUBLIC_COMMAND
from .common import print_json, run_command, save_json, slugify, utc_now
from .config_layers import effective_config
from .paths import CODEX_HOME, INVENTORY_PATH, PLUGINS_DIR, SKILLS_DIR


INVENTORY_SCHEMA_VERSION = 1
TOOL_KIND = "tool"
SKILL_KIND = "skill"
PLUGIN_KIND = "plugin"
MCP_KIND = "mcp"
SYSTEM_SCOPE = "system"
USER_SCOPE = "user"
REPO_SCOPE = "repo"
PLUGIN_SCOPE = "plugin"


def _capability_specs() -> list[dict[str, Any]]:
    from . import capabilities as caps

    return list(caps.CAPABILITY_SPECS)


def _front_door_maps() -> dict[str, dict[str, str]]:
    tool_map: dict[str, str] = {}
    skill_map: dict[str, str] = {}
    plugin_map: dict[str, str] = {}
    mcp_map: dict[str, str] = {}
    bucket_map: dict[str, str] = {}

    for spec in _capability_specs():
        bucket_map[spec["key"]] = spec["group"]
        for skill_name in spec.get("skills", []):
            skill_map.setdefault(skill_name, spec["front_door"])
        for identifier in spec.get("interfaces", []):
            kind, name = identifier.split(":", 1)
            if kind == "tool":
                tool_map.setdefault(name, spec["front_door"])
            elif kind == "plugin":
                plugin_map.setdefault(name, spec["front_door"])
            elif kind == "mcp":
                mcp_map.setdefault(name, spec["front_door"])
    return {
        TOOL_KIND: tool_map,
        SKILL_KIND: skill_map,
        PLUGIN_KIND: plugin_map,
        MCP_KIND: mcp_map,
        "bucket": bucket_map,
    }


def _menu_bucket(kind: str, scope: str) -> str:
    return f"{kind}:{scope}"


def _item_id(kind: str, name: str, scope: str) -> str:
    return f"{kind}:{name}@{scope}"


def _inventory_item(
    *,
    kind: str,
    name: str,
    source_scope: str,
    status: str,
    front_door_candidate: str | None,
    menu_bucket: str,
    installed: bool | None = None,
    configured: bool | None = None,
    version: str | None = None,
    source_path: str | None = None,
    source_hint: str | None = None,
    hidden_reason: str | None = None,
) -> dict[str, Any]:
    payload = {
        "id": _item_id(kind, name, source_scope),
        "kind": kind,
        "name": name,
        "source_scope": source_scope,
        "status": status,
        "front_door_candidate": front_door_candidate,
        "menu_bucket": menu_bucket,
        "hidden_reason": hidden_reason,
    }
    if installed is not None:
        payload["installed"] = installed
    if configured is not None:
        payload["configured"] = configured
    if version:
        payload["version"] = version
    if source_path:
        payload["source_path"] = source_path
    if source_hint:
        payload["source_hint"] = source_hint
    return payload


def _detect_tools() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    from . import capabilities as caps

    gh = caps._detect_gh()
    gh_extensions = caps._gh_extensions() if gh.get("installed") else {}
    tools = {
        "python": {
            "name": "python",
            "command": "python",
            "path": caps.sys.executable,
            "installed": True,
            "status": "ok",
            "version": caps.sys.version.splitlines()[0],
        },
        "node": caps._tool_record("node", command="node", version_args=["--version"]),
        "npx": caps._tool_record("npx", command="npx", version_args=["--version"]),
        "docker": caps._tool_record("docker", command="docker", version_args=["--version"]),
        "skills": caps._detect_skills_cli(),
        "codex": caps.detect_codex_runtime(),
        "gh": gh,
        "gh-codeql": caps._detect_gh_codeql(gh_extensions, gh),
        "ghas-cli": caps._detect_ghas_cli(),
        "coderabbit": caps._tool_record("coderabbit", command="coderabbit", version_args=["--version"]),
        "aws": caps._tool_record("aws", command="aws", version_args=["--version"], detect_only=True),
        "az": caps._tool_record("az", command="az", version_args=["--version"], detect_only=True),
        "gcloud": caps._tool_record("gcloud", command="gcloud", version_args=["--version"], detect_only=True),
        "firebase": caps._tool_record("firebase", command="firebase", version_args=["--version"], detect_only=True),
        "plugin-eval": caps._detect_plugin_eval(),
        "supabase": caps._tool_record("supabase", command="supabase", version_args=["--version"]),
        "vercel": caps._tool_record("vercel", command="vercel", version_args=["--version"]),
        "playwright": caps._detect_playwright(),
    }

    maps = _front_door_maps()
    items: list[dict[str, Any]] = []
    for name, payload in tools.items():
        hidden_reason = None
        if not maps[TOOL_KIND].get(name):
            hidden_reason = "detected for diagnostics only; no curated front door is registered yet."
        items.append(
            _inventory_item(
                kind=TOOL_KIND,
                name=name,
                source_scope=SYSTEM_SCOPE,
                status=payload.get("status", "missing"),
                installed=bool(payload.get("installed")),
                version=payload.get("version"),
                source_path=payload.get("path"),
                source_hint=payload.get("command"),
                front_door_candidate=maps[TOOL_KIND].get(name),
                menu_bucket=_menu_bucket(TOOL_KIND, SYSTEM_SCOPE),
                hidden_reason=hidden_reason,
            )
        )

    source_status = "ok"
    if any(item["status"] == "error" for item in items):
        source_status = "error"
    return tools, items, [{"name": "tools", "status": source_status, "detail": f"{len(items)} detected tools"}]


def _skills_cli_items(repo_root: Path | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from . import capabilities as caps

    maps = _front_door_maps()
    items: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []

    global_result = caps._installed_skills()
    sources.append({"name": "skills-global", "status": global_result.get("status", "unknown"), "detail": global_result.get("error", "")})
    for item in global_result.get("items", []):
        name = item.get("name") or item.get("slug") or "unknown-skill"
        hidden_reason = None
        if ":" in name and not maps[SKILL_KIND].get(name):
            hidden_reason = "plugin-provided skill is represented in raw inventory only."
        elif not maps[SKILL_KIND].get(name):
            hidden_reason = "skill is installed but not promoted into the curated front-door menu."
        items.append(
            _inventory_item(
                kind=SKILL_KIND,
                name=name,
                source_scope=USER_SCOPE,
                status="ok",
                installed=True,
                version=str(item.get("version") or ""),
                source_hint="npx skills ls -g",
                front_door_candidate=maps[SKILL_KIND].get(name),
                menu_bucket=_menu_bucket(SKILL_KIND, USER_SCOPE),
                hidden_reason=hidden_reason,
            )
        )

    if repo_root:
        project_result = run_command(["npx", "skills", "ls", "--json"], cwd=repo_root, timeout=60)
        if project_result["ok"]:
            try:
                project_items = json.loads(project_result["stdout"] or "[]")
                status = "ok"
                detail = f"{len(project_items)} project skills"
            except json.JSONDecodeError as exc:
                project_items = []
                status = "error"
                detail = f"failed to parse project skills output: {exc}"
        else:
            project_items = []
            status = "ok"
            detail = "project-scoped skills are unavailable or not configured in this repo"
        sources.append({"name": "skills-project", "status": status, "detail": detail})
        for item in project_items:
            name = item.get("name") or item.get("slug") or "unknown-skill"
            hidden_reason = None
            if ":" in name and not maps[SKILL_KIND].get(name):
                hidden_reason = "plugin-provided skill is represented in raw inventory only."
            elif not maps[SKILL_KIND].get(name):
                hidden_reason = "skill is installed but not promoted into the curated front-door menu."
            items.append(
                _inventory_item(
                    kind=SKILL_KIND,
                    name=name,
                    source_scope=REPO_SCOPE,
                    status="ok",
                    installed=True,
                    version=str(item.get("version") or ""),
                    source_hint="npx skills ls",
                    front_door_candidate=maps[SKILL_KIND].get(name),
                    menu_bucket=_menu_bucket(SKILL_KIND, REPO_SCOPE),
                    hidden_reason=hidden_reason,
                )
            )
    return items, sources


def _local_skill_file_items(repo_root: Path | None) -> list[dict[str, Any]]:
    maps = _front_door_maps()
    items: list[dict[str, Any]] = []

    def collect(base: Path | None, scope: str) -> None:
        if base is None or not base.exists():
            return
        for path in sorted(base.glob("*/SKILL.md")):
            if path.parent.name == ".system":
                continue
            name = path.parent.name
            hidden_reason = None if maps[SKILL_KIND].get(name) else "skill file exists locally but is not part of the curated front-door menu."
            items.append(
                _inventory_item(
                    kind=SKILL_KIND,
                    name=name,
                    source_scope=scope,
                    status="ok",
                    installed=True,
                    source_path=str(path),
                    front_door_candidate=maps[SKILL_KIND].get(name),
                    menu_bucket=_menu_bucket(SKILL_KIND, scope),
                    hidden_reason=hidden_reason,
                )
            )

    collect(SKILLS_DIR, USER_SCOPE)
    if repo_root:
        collect(repo_root / ".agents" / "skills", REPO_SCOPE)
    return items


def _plugin_name_from_skill_path(path: Path) -> str | None:
    try:
        relative = path.relative_to(PLUGINS_DIR)
    except ValueError:
        return None
    parts = relative.parts
    if "skills" not in parts:
        return None
    if parts and parts[0] == "cache" and len(parts) >= 3:
        return parts[2]
    return parts[0] if parts else None


def _is_fixture_plugin_skill(path: Path) -> bool:
    try:
        relative = path.relative_to(PLUGINS_DIR)
    except ValueError:
        return False
    return "fixtures" in relative.parts or "tests" in relative.parts


def _plugin_items(config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    maps = _front_door_maps()
    items_by_name: dict[str, dict[str, Any]] = {}

    configured_plugins = config.get("plugins", {})
    if isinstance(configured_plugins, dict):
        for name, payload in configured_plugins.items():
            configured = isinstance(payload, dict)
            enabled = configured and bool(payload.get("enabled"))
            items_by_name[name] = _inventory_item(
                kind=PLUGIN_KIND,
                name=name,
                source_scope=USER_SCOPE,
                status="ok" if enabled else "disabled",
                installed=False,
                configured=configured,
                source_path=str(PLUGINS_DIR / name),
                front_door_candidate=maps[PLUGIN_KIND].get(name),
                menu_bucket=_menu_bucket(PLUGIN_KIND, USER_SCOPE),
                hidden_reason=None if maps[PLUGIN_KIND].get(name) else "plugin is detected for diagnostics only and is not auto-promoted into the curated menu.",
            )

    plugin_dirs: set[Path] = set()
    if PLUGINS_DIR.exists():
        plugin_dirs.update(path for path in PLUGINS_DIR.iterdir() if path.is_dir() and path.name != "cache")
        cache_root = PLUGINS_DIR / "cache"
        if cache_root.exists():
            for manifest in cache_root.glob("*/*/*/.codex-plugin/plugin.json"):
                plugin_dirs.add(manifest.parent.parent.parent)

    for plugin_dir in sorted(plugin_dirs):
        name = plugin_dir.name
        existing = items_by_name.get(name)
        if existing:
            existing["installed"] = True
            existing["source_path"] = str(plugin_dir)
            if existing["status"] == "disabled":
                existing["status"] = "degraded"
        else:
            items_by_name[name] = _inventory_item(
                kind=PLUGIN_KIND,
                name=name,
                source_scope=USER_SCOPE,
                status="ok",
                installed=True,
                configured=False,
                source_path=str(plugin_dir),
                front_door_candidate=maps[PLUGIN_KIND].get(name),
                menu_bucket=_menu_bucket(PLUGIN_KIND, USER_SCOPE),
                hidden_reason=None if maps[PLUGIN_KIND].get(name) else "plugin is installed but not promoted into the curated front-door menu.",
            )

    skill_items: list[dict[str, Any]] = []
    if PLUGINS_DIR.exists():
        for skill_path in sorted(PLUGINS_DIR.glob("**/skills/*/SKILL.md")):
            if _is_fixture_plugin_skill(skill_path):
                continue
            plugin_name = _plugin_name_from_skill_path(skill_path)
            if not plugin_name:
                continue
            skill_name = skill_path.parent.name
            full_name = f"{plugin_name}:{skill_name}"
            front_door_candidate = maps[SKILL_KIND].get(full_name)
            skill_items.append(
                _inventory_item(
                    kind=SKILL_KIND,
                    name=full_name,
                    source_scope=PLUGIN_SCOPE,
                    status="ok",
                    installed=True,
                    source_path=str(skill_path),
                    front_door_candidate=front_door_candidate,
                    menu_bucket=_menu_bucket(SKILL_KIND, PLUGIN_SCOPE),
                    hidden_reason=None if front_door_candidate else "plugin-provided skill is represented in raw inventory only.",
                )
            )
    return sorted(items_by_name.values(), key=lambda item: item["name"]), skill_items


def _mcp_items(config: dict[str, Any]) -> list[dict[str, Any]]:
    maps = _front_door_maps()
    items: list[dict[str, Any]] = []
    servers = config.get("mcp_servers", {})
    if not isinstance(servers, dict):
        return items

    for name, payload in sorted(servers.items()):
        if not isinstance(payload, dict):
            continue
        items.append(
            _inventory_item(
                kind=MCP_KIND,
                name=name,
                source_scope=USER_SCOPE,
                status="configured",
                configured=True,
                source_hint="mcp_servers config",
                front_door_candidate=maps[MCP_KIND].get(name),
                menu_bucket=_menu_bucket(MCP_KIND, USER_SCOPE),
                hidden_reason=None if maps[MCP_KIND].get(name) else "MCP server is configured for diagnostics only and is not auto-promoted into the curated menu.",
            )
        )
    return items


def _merge_duplicate_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in items:
        key = (item["kind"], item["name"], item["source_scope"])
        existing = merged.get(key)
        if existing is None:
            merged[key] = dict(item)
            continue
        for field in ("source_path", "source_hint", "version", "front_door_candidate"):
            if item.get(field) and not existing.get(field):
                existing[field] = item[field]
        if item.get("hidden_reason") and not existing.get("hidden_reason"):
            existing["hidden_reason"] = item["hidden_reason"]
        if "installed" in item:
            existing["installed"] = bool(existing.get("installed")) or bool(item.get("installed"))
        if "configured" in item:
            existing["configured"] = bool(existing.get("configured")) or bool(item.get("configured"))
        status_order = {"error": 4, "degraded": 3, "missing": 2, "disabled": 1, "configured": 0, "ok": 0}
        existing_status = existing.get("status", "ok")
        incoming_status = item.get("status", "ok")
        if status_order.get(incoming_status, 0) > status_order.get(existing_status, 0):
            existing["status"] = incoming_status
    return sorted(merged.values(), key=lambda item: (item["kind"], item["name"].lower(), item["source_scope"]))


def _bucket_range_label(chunk: list[dict[str, Any]]) -> str:
    def first_char(value: str) -> str:
        if not value:
            return "other"
        char = value[0].lower()
        return char if char.isalpha() else "other"

    start = first_char(chunk[0]["name"])
    end = first_char(chunk[-1]["name"])
    return start if start == end else f"{start}-{end}"


def _apply_bucket_splitting(items: list[dict[str, Any]], *, max_items: int) -> list[dict[str, Any]]:
    bucket_items: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        bucket_items.setdefault(item["menu_bucket"], []).append(item)

    buckets: list[dict[str, Any]] = []
    for base_bucket, grouped_items in sorted(bucket_items.items()):
        ordered = sorted(grouped_items, key=lambda item: (item["name"].lower(), item["source_scope"]))
        if len(ordered) <= max_items:
            bucket_key = base_bucket
            for item in ordered:
                item["menu_bucket"] = bucket_key
            buckets.append({"key": bucket_key, "base_bucket": base_bucket, "count": len(ordered), "item_ids": [item["id"] for item in ordered], "split": False})
            continue

        for index in range(0, len(ordered), max_items):
            chunk = ordered[index : index + max_items]
            label = _bucket_range_label(chunk)
            bucket_key = f"{base_bucket}:{label}"
            if any(bucket["key"] == bucket_key for bucket in buckets):
                bucket_key = f"{bucket_key}-{(index // max_items) + 1}"
            for item in chunk:
                item["menu_bucket"] = bucket_key
            buckets.append({"key": bucket_key, "base_bucket": base_bucket, "count": len(chunk), "item_ids": [item["id"] for item in chunk], "split": True})
    return buckets


def build_inventory_snapshot(repo: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(repo).resolve() if repo else Path.cwd().resolve()
    config = effective_config(repo_root)
    max_items = int(config.get("menus", {}).get("max_items", 25) or 25)

    tool_map, tool_items, sources = _detect_tools()
    skill_items, skill_sources = _skills_cli_items(repo_root)
    sources.extend(skill_sources)
    local_skill_items = _local_skill_file_items(repo_root)
    plugin_items, plugin_skill_items = _plugin_items(config)
    mcp_items = _mcp_items(config)

    all_items = _merge_duplicate_items(tool_items + skill_items + local_skill_items + plugin_items + plugin_skill_items + mcp_items)
    buckets = _apply_bucket_splitting(all_items, max_items=max_items)

    kind_counts: dict[str, int] = {}
    hidden_count = 0
    for item in all_items:
        kind_counts[item["kind"]] = kind_counts.get(item["kind"], 0) + 1
        if item.get("hidden_reason"):
            hidden_count += 1

    source_statuses = {source["status"] for source in sources}
    status = "error" if "error" in source_statuses else "degraded" if "degraded" in source_statuses else "ok"

    return {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "repo_root": str(repo_root),
        "summary": {
            "status": status,
            "total_items": len(all_items),
            "hidden_count": hidden_count,
            "kind_counts": kind_counts,
            "bucket_count": len(buckets),
            "max_bucket_size": max((bucket["count"] for bucket in buckets), default=0),
        },
        "sources": sources,
        "tool_map": tool_map,
        "items": sorted(all_items, key=lambda item: (item["kind"], item["menu_bucket"], item["name"].lower(), item["source_scope"])),
        "menu_budget": {
            "max_items": max_items,
        },
        "menu_buckets": buckets,
    }


def refresh_inventory_snapshot(repo: str | Path | None = None, *, output_path: str | Path | None = None) -> dict[str, Any]:
    snapshot = build_inventory_snapshot(repo)
    save_json(output_path or INVENTORY_PATH, snapshot)
    return snapshot


def load_inventory_snapshot(
    repo: str | Path | None = None,
    *,
    refresh: bool = False,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(output_path).resolve() if output_path else INVENTORY_PATH
    if refresh or not path.exists():
        return refresh_inventory_snapshot(repo, output_path=path)
    return json.loads(path.read_text(encoding="utf-8"))


def inventory_item(payload: dict[str, Any], selector: str) -> dict[str, Any] | None:
    if ":" not in selector:
        return None
    kind, name = selector.split(":", 1)
    matches = [item for item in payload.get("items", []) if item.get("kind") == kind and item.get("name") == name]
    if not matches:
        return None
    if len(matches) == 1:
        return {"kind": "item", "item": matches[0]}
    return {"kind": "matches", "matches": matches}


def filter_inventory_items(
    payload: dict[str, Any],
    *,
    kind: str = "all",
    scope: str = "all",
) -> dict[str, Any]:
    items = payload.get("items", [])
    if kind != "all":
        items = [item for item in items if item.get("kind") == kind.removesuffix("s")]
    if scope == "repo":
        items = [item for item in items if item.get("source_scope", "").startswith(REPO_SCOPE)]
    elif scope == "user":
        items = [item for item in items if not item.get("source_scope", "").startswith(REPO_SCOPE)]

    item_ids = {item["id"] for item in items}
    buckets = [bucket for bucket in payload.get("menu_buckets", []) if any(item_id in item_ids for item_id in bucket.get("item_ids", []))]
    return {
        "schema_version": payload.get("schema_version", INVENTORY_SCHEMA_VERSION),
        "generated_at": payload.get("generated_at"),
        "repo_root": payload.get("repo_root"),
        "summary": {
            "status": payload.get("summary", {}).get("status", "unknown"),
            "total_items": len(items),
            "bucket_count": len(buckets),
        },
        "menu_budget": payload.get("menu_budget", {}),
        "items": items,
        "menu_buckets": buckets,
    }


def print_inventory_human(payload: dict[str, Any], *, as_json: bool = False) -> None:
    if as_json:
        print_json(payload)
        return

    if payload.get("kind") == "item":
        item = payload["item"]
        print(f"{item['kind']}:{item['name']}")
        for key in (
            "source_scope",
            "status",
            "installed",
            "configured",
            "version",
            "front_door_candidate",
            "menu_bucket",
            "source_path",
            "source_hint",
            "hidden_reason",
        ):
            if key in item and item[key] not in (None, ""):
                print(f"- {key}: {item[key]}")
        return

    if payload.get("kind") == "matches":
        print("Multiple inventory items matched")
        for item in payload.get("matches", []):
            print(f"- {item['kind']}:{item['name']} @{item['source_scope']} [{item['status']}]")
        return

    summary = payload.get("summary", {})
    print(f"Status: {summary.get('status', 'unknown')}")
    print(f"Items: {summary.get('total_items', 0)}")
    print(f"Buckets: {summary.get('bucket_count', 0)}")
    print("")
    print("Inventory")
    bucket_map = {bucket["key"]: bucket for bucket in payload.get("menu_buckets", [])}
    items_by_bucket: dict[str, list[dict[str, Any]]] = {}
    for item in payload.get("items", []):
        items_by_bucket.setdefault(item["menu_bucket"], []).append(item)
    if not items_by_bucket:
        print("- none")
        return
    for bucket_key in sorted(items_by_bucket):
        bucket = bucket_map.get(bucket_key, {"count": len(items_by_bucket[bucket_key]), "split": False})
        split_tag = " split" if bucket.get("split") else ""
        print(f"- {bucket_key} [{bucket.get('count', 0)}{split_tag}]")
        for item in sorted(items_by_bucket[bucket_key], key=lambda entry: (entry["name"].lower(), entry["source_scope"])):
            hidden = " hidden" if item.get("hidden_reason") else ""
            print(f"  - {item['name']} [{item['status']}{hidden}]")
    print("")
    print(f"Use `{PUBLIC_COMMAND} inventory item <kind>:<name>` for one record.")
