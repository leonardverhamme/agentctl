from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

from .branding import PUBLIC_COMMAND, PUBLIC_DISPLAY_NAME, PUBLIC_DOCS_DIRNAME, PUBLIC_PRODUCT_NAME
from .capabilities import CAPABILITY_GROUPS
from .common import print_json, save_text, utc_now
from .paths import AGENTCTL_DOCS_DIR, maintenance_workspace


SCHEMA_VERSION = 1
AUTO_MARKER = f"<!-- {PUBLIC_PRODUCT_NAME}:auto-generated -->"
SKILL_MAP_DOC_NAME = "skill-map.md"
SKILL_MAP_PDF_NAME = "skill-map.pdf"
PREFERRED_EDIT_SKILL = "editskill"
LEGACY_EDIT_SKILL = "skill-edit-mode"


def _resolve_docs_dir(cwd: str | Path | None = None, *, docs_dir: str | Path | None = None) -> Path:
    if docs_dir is not None:
        return Path(docs_dir)
    try:
        return maintenance_workspace(cwd).docs_dir
    except Exception:
        return AGENTCTL_DOCS_DIR


def _parse_skill_front_matter(path: str | Path | None) -> dict[str, str]:
    if not path:
        return {}
    skill_path = Path(path)
    if not skill_path.exists():
        return {}
    text = skill_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    lines = text.splitlines()
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def _parse_openai_skill_metadata(path: str | Path | None) -> dict[str, str]:
    if not path:
        return {}
    skill_path = Path(path)
    yaml_path = skill_path.parent / "agents" / "openai.yaml"
    if not yaml_path.exists():
        return {}
    metadata: dict[str, str] = {}
    current_section: str | None = None
    for raw_line in yaml_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):
            if line.endswith(":"):
                current_section = line[:-1].strip()
            else:
                current_section = None
            continue
        if current_section != "interface":
            continue
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata


def _preferred_skill_records(inventory_snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    priority = {"repo": 0, "user": 1, "plugin": 2, "system": 3}
    for item in inventory_snapshot.get("items", []):
        if item.get("kind") != "skill":
            continue
        if item.get("source_scope") == "plugin":
            continue
        name = item.get("name", "")
        if ":" in name:
            continue
        existing = records.get(name)
        candidate = dict(item)
        metadata = _parse_skill_front_matter(item.get("source_path"))
        openai_metadata = _parse_openai_skill_metadata(item.get("source_path"))
        if openai_metadata:
            for key, value in openai_metadata.items():
                metadata.setdefault(key, value)
        if metadata:
            candidate["metadata"] = metadata
        if existing is None:
            records[name] = candidate
            continue
        candidate_priority = priority.get(candidate.get("source_scope", "user"), 99)
        existing_priority = priority.get(existing.get("source_scope", "user"), 99)
        if candidate_priority < existing_priority:
            candidate.setdefault("source_hint", existing.get("source_hint"))
            records[name] = candidate
            continue
        if candidate.get("source_path") and not existing.get("source_path"):
            existing["source_path"] = candidate["source_path"]
            if candidate.get("metadata"):
                existing["metadata"] = candidate["metadata"]
        if candidate.get("source_hint") and not existing.get("source_hint"):
            existing["source_hint"] = candidate["source_hint"]
        if candidate.get("version") and not existing.get("version"):
            existing["version"] = candidate["version"]
        if candidate.get("hidden_reason") and not existing.get("hidden_reason"):
            existing["hidden_reason"] = candidate["hidden_reason"]
        existing["installed"] = bool(existing.get("installed")) or bool(candidate.get("installed"))
    return records


def _command_entry(entrypoints: list[str]) -> str | None:
    for entry in entrypoints:
        if entry.startswith(PUBLIC_COMMAND):
            return entry
    return None


def build_skill_map_payload(
    capabilities_snapshot: dict[str, Any],
    inventory_snapshot: dict[str, Any],
    *,
    cwd: str | Path | None = None,
    docs_dir: str | Path | None = None,
) -> dict[str, Any]:
    docs_dir = _resolve_docs_dir(cwd, docs_dir=docs_dir)
    capability_by_key = {
        item["key"]: item for item in capabilities_snapshot.get("capabilities", [])
    }
    local_skill_records = _preferred_skill_records(inventory_snapshot)
    capability_skill_names = {
        skill_name
        for capability in capabilities_snapshot.get("capabilities", [])
        for skill_name in capability.get("skills", [])
    }

    groups: list[dict[str, Any]] = []
    for group in capabilities_snapshot.get("capability_groups", []) or CAPABILITY_GROUPS:
        items: list[dict[str, Any]] = []
        group_keys = group.get("items") or [
            capability["key"]
            for capability in capabilities_snapshot.get("capabilities", [])
            if capability.get("group") == group["key"]
        ]
        for key in group_keys:
            capability = capability_by_key.get(key)
            if capability is None:
                continue
            label = capability.get("label", key.replace("-", " ").title())
            items.append(
                {
                    "key": capability["key"],
                    "label": label,
                    "front_door": capability.get("front_door", label),
                    "command": _command_entry(capability.get("entrypoints", [])),
                    "summary": capability.get("summary", label),
                    "status": capability.get("status", "unknown"),
                    "skills": [
                        {
                            "name": skill_name,
                            "description": (
                                local_skill_records.get(skill_name, {})
                                .get("metadata", {})
                                .get("description", "")
                            ),
                            "source_path": local_skill_records.get(skill_name, {}).get("source_path"),
                        }
                        for skill_name in capability.get("skills", [])
                    ],
                }
            )
        if items:
            groups.append(
                {
                    "key": group["key"],
                    "label": group.get("label", group["key"].replace("-", " ").title()),
                    "summary": group.get("summary", group.get("label", group["key"].replace("-", " ").title())),
                    "count": len(items),
                    "items": items,
                }
            )

    helper_skills: list[dict[str, Any]] = []
    for name, record in sorted(local_skill_records.items()):
        if name in capability_skill_names:
            continue
        description = record.get("metadata", {}).get("description", "")
        note = record.get("hidden_reason")
        preferred = False
        if name == PREFERRED_EDIT_SKILL:
            preferred = True
            note = "Preferred front door for intentional skill-system changes."
        elif name == LEGACY_EDIT_SKILL:
            note = "Legacy compatibility alias. Prefer `$editskill` in new chats."
        helper_skills.append(
            {
                "name": name,
                "description": description,
                "note": note,
                "preferred": preferred,
                "source_path": record.get("source_path"),
            }
        )

    plugin_counts: dict[str, int] = {}
    plugin_status: dict[str, str] = {}
    for item in inventory_snapshot.get("items", []):
        if item.get("kind") == "plugin":
            plugin_status[item["name"]] = item.get("status", "unknown")
        if item.get("kind") != "skill" or item.get("source_scope") != "plugin":
            continue
        name = item.get("name", "")
        family = name.split(":", 1)[0] if ":" in name else name
        plugin_counts[family] = plugin_counts.get(family, 0) + 1
    plugin_families = [
        {
            "name": name,
            "skill_count": plugin_counts[name],
            "status": plugin_status.get(name, "ok"),
        }
        for name in sorted(plugin_counts)
    ]

    notes = [
        "`$ui-skill` and `$ui-deep-audit` are still present. They live under `Workflows -> UI workflows`.",
        "`$context-skill` is still present. It lives under `Workflows -> Repo context workflows`.",
        "The `$` picker looks much larger because Codex also shows curated plugin skills, not just the local Agent CLI OS front-door skills.",
        "`$editskill` is the preferred direct helper for intentional skill-system changes. `$skill-edit-mode` stays as a legacy alias.",
        "If the active desktop thread still shows an old `$` list after a bundle sync, open a new thread or restart the app; the current session can keep a stale skill index.",
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "docs_dir": str(docs_dir),
        "markdown_path": str(docs_dir / SKILL_MAP_DOC_NAME),
        "pdf_path": str(docs_dir / SKILL_MAP_PDF_NAME),
        "summary": {
            "group_count": len(groups),
            "front_door_skill_count": len(capability_skill_names),
            "helper_skill_count": len(helper_skills),
            "plugin_family_count": len(plugin_families),
            "plugin_skill_count": sum(item["skill_count"] for item in plugin_families),
        },
        "menu_groups": groups,
        "helper_skills": helper_skills,
        "plugin_families": plugin_families,
        "inventory_summary": inventory_snapshot.get("summary", {}),
        "notes": notes,
    }


def _render_mermaid(payload: dict[str, Any]) -> str:
    lines = ["flowchart TD", '  root["agentcli capabilities"]']
    for group in payload.get("menu_groups", []):
        group_id = f"group_{group['key'].replace('-', '_')}"
        lines.append(f'  root --> {group_id}["{group["label"]}"]')
        for item in group.get("items", []):
            item_id = f'{group_id}_{item["key"].replace("-", "_")}'
            label = f'{item["label"]}\\n{item["front_door"]}'
            lines.append(f'  {group_id} --> {item_id}["{label}"]')
    return "\n".join(lines)


def render_skill_map_markdown(payload: dict[str, Any]) -> str:
    lines = [
        AUTO_MARKER,
        f"# {PUBLIC_DISPLAY_NAME} Skill Map",
        "",
        "This is the human-facing one-page map of the curated menu and the local front-door skills.",
        "",
        "## What This Explains",
        "",
    ]
    for note in payload.get("notes", []):
        lines.append(f"- {note}")
    lines.extend(
        [
            "",
            "## Menu Diagram",
            "",
            "```mermaid",
            _render_mermaid(payload),
            "```",
            "",
            "## Curated Menu",
            "",
        ]
    )

    for group in payload.get("menu_groups", []):
        lines.extend([f"### {group['label']}", "", group["summary"], "", "| Capability | Use first | Command |", "| --- | --- | --- |"])
        for item in group.get("items", []):
            skill_names = ", ".join(f"`{skill['name']}`" for skill in item.get("skills", [])) or "-"
            command = f"`{item['command']}`" if item.get("command") else "-"
            lines.append(f"| {item['label']} | {skill_names} | {command} |")
        lines.append("")

    lines.extend(["## Direct Local Helpers", "", "| Skill | Purpose | Note |", "| --- | --- | --- |"])
    for item in payload.get("helper_skills", []):
        note = item.get("note") or "-"
        description = item.get("description") or "-"
        lines.append(f"| `{item['name']}` | {description} | {note} |")
    lines.append("")

    lines.extend(["## Curated Plugin Catalog Summary", "", "| Plugin family | Skill count | Status |", "| --- | --- | --- |"])
    for item in payload.get("plugin_families", []):
        lines.append(f"| `{item['name']}` | {item['skill_count']} | `{item['status']}` |")
    lines.append("")

    lines.extend(
        [
            "## Raw Catalog",
            "",
            f"- `agentcli capabilities` is the compact front door.",
            f"- `agentcli capability ui-workflows` shows where the UI skills live.",
            f"- `agentcli capability context-workflows` shows where the context skill lives.",
            f"- `agentcli inventory show --kind skills` shows the raw installed skill catalog behind the compact menu.",
            f"- `agentcli skill-map` refreshes this page and the matching one-page PDF.",
            "",
            "## Current Counts",
            "",
            "```json",
            json.dumps(payload.get("summary", {}), indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _pdf_escape(value: str) -> str:
    clean = value.encode("latin-1", "replace").decode("latin-1")
    return clean.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_lines(payload: dict[str, Any]) -> list[str]:
    lines = [
        f"{PUBLIC_DISPLAY_NAME} Skill Map",
        "",
        "Curated local front-door skills:",
    ]
    for group in payload.get("menu_groups", []):
        lines.append(f"{group['label']}:")
        for item in group.get("items", []):
            names = ", ".join(f"${skill['name']}" for skill in item.get("skills", [])) or item["front_door"]
            command = item.get("command") or "-"
            lines.append(f"  - {item['label']}: {names} | {command}")
        lines.append("")
    lines.append("Direct local helpers:")
    for item in payload.get("helper_skills", []):
        note = item.get("note") or item.get("description") or "-"
        lines.append(f"  - ${item['name']}: {note}")
    lines.append("")
    lines.append("Curated plugin catalog summary:")
    for item in payload.get("plugin_families", []):
        lines.append(f"  - {item['name']}: {item['skill_count']} skills [{item['status']}]")
    lines.append("")
    lines.append("Key clarification:")
    for note in payload.get("notes", []):
        lines.append(f"  - {note}")
    lines.append("")
    lines.append(f"Commands: {PUBLIC_COMMAND} capabilities | {PUBLIC_COMMAND} capability <key> | {PUBLIC_COMMAND} inventory show --kind skills")
    lines.append(f"Generated: {payload['generated_at']}")

    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(textwrap.wrap(line, width=120, replace_whitespace=False) or [""])
    max_lines = 62
    if len(wrapped) > max_lines:
        wrapped = wrapped[: max_lines - 1] + ["... see skill-map.md for the full generated map."]
    return wrapped


def _write_text_pdf(path: Path, *, lines: list[str]) -> None:
    width = 842
    height = 595
    margin = 24
    font_size = 8
    leading = 9
    y_start = height - margin - font_size
    commands = ["BT", f"/F1 {font_size} Tf", f"{leading} TL", f"{margin} {y_start} Td"]
    for index, line in enumerate(lines):
        if index:
            commands.append("T*")
        commands.append(f"({_pdf_escape(line)}) Tj")
    commands.append("ET")
    stream = "\n".join(commands)
    stream_bytes = stream.encode("latin-1", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>".encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
        b"<< /Length " + str(len(stream_bytes)).encode("ascii") + b" >>\nstream\n" + stream_bytes + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF\n"
        ).encode("ascii")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pdf)


def write_skill_map_docs(
    capabilities_snapshot: dict[str, Any],
    inventory_snapshot: dict[str, Any],
    *,
    cwd: str | Path | None = None,
    docs_dir: str | Path | None = None,
) -> dict[str, Any]:
    payload = build_skill_map_payload(
        capabilities_snapshot,
        inventory_snapshot,
        cwd=cwd,
        docs_dir=docs_dir,
    )
    markdown_path = Path(payload["markdown_path"])
    pdf_path = Path(payload["pdf_path"])
    save_text(markdown_path, render_skill_map_markdown(payload))
    _write_text_pdf(pdf_path, lines=_pdf_lines(payload))
    return payload


def print_skill_map_human(payload: dict[str, Any], *, as_json: bool = False) -> None:
    if as_json:
        print_json(payload)
        return

    summary = payload.get("summary", {})
    print(f"Status: ok")
    print(f"Menu groups: {summary.get('group_count', 0)}")
    print(f"Front-door skills: {summary.get('front_door_skill_count', 0)}")
    print(f"Helper skills: {summary.get('helper_skill_count', 0)}")
    print(f"Plugin families: {summary.get('plugin_family_count', 0)}")
    print("")
    print("Clarifications")
    for note in payload.get("notes", []):
        print(f"- {note}")
    print("")
    print("Artifacts")
    print(f"- Markdown: {payload['markdown_path']}")
    print(f"- PDF: {payload['pdf_path']}")
