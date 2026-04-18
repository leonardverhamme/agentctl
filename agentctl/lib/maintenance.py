from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from .capabilities import build_capabilities_report, capability_detail, capability_doc_path, capability_keys
from .common import load_json, print_json, save_json, save_text, utc_now
from .paths import (
    AGENTCTL_CAPABILITIES_DOCS_DIR,
    AGENTCTL_DOCS_DIR,
    AGENTCTL_HOME,
    AGENTCTL_MAINTENANCE_SKILL_DIR,
    AGENTCTL_PLUGIN_DIR,
    AGENTCTL_PLUGIN_MANIFEST_PATH,
    AGENTCTL_PLUGIN_NAME,
    AGENTCTL_PLUGIN_ROUTER_SKILL_DIR,
    CAPABILITIES_PATH,
    CAPABILITY_REGISTRY_REFERENCE_PATH,
    CLOUD_READINESS_REFERENCE_PATH,
    CONFIG_PATH,
    DOCTOR_REPORT_PATH,
    MAINTENANCE_CONTRACT_REFERENCE_PATH,
    MAINTENANCE_REPORT_PATH,
    MAINTENANCE_STATE_PATH,
    STATE_SCHEMA_REFERENCE_PATH,
    WORKFLOW_REGISTRY_PATH,
)


SCHEMA_VERSION = 1
AUTO_MARKER = "<!-- agentctl:auto-generated -->"
MAINTENANCE_WORKFLOW_NAME = "agentctl-maintenance"
MAINTENANCE_SKILL_NAME = "agentctl-maintenance-engineer"
MAINTENANCE_DOCS: dict[str, Path] = {
    "overview": AGENTCTL_DOCS_DIR / "overview.md",
    "command-map": AGENTCTL_DOCS_DIR / "command-map.md",
    "state-schema": AGENTCTL_DOCS_DIR / "state-schema.md",
    "capability-registry": AGENTCTL_DOCS_DIR / "capability-registry.md",
    "cloud-readiness": AGENTCTL_DOCS_DIR / "cloud-readiness.md",
    "maintenance": AGENTCTL_DOCS_DIR / "maintenance.md",
}
REFERENCE_DOCS: dict[str, Path] = {
    "state-schema": STATE_SCHEMA_REFERENCE_PATH,
    "capability-registry": CAPABILITY_REGISTRY_REFERENCE_PATH,
    "maintenance-contract": MAINTENANCE_CONTRACT_REFERENCE_PATH,
    "cloud-readiness": CLOUD_READINESS_REFERENCE_PATH,
}
PLUGIN_CONFIG_KEYS = (AGENTCTL_PLUGIN_NAME, f"{AGENTCTL_PLUGIN_NAME}@local")
COMMAND_GROUPS = [
    {
        "group": "core",
        "items": [
            {"command": "doctor", "usage": "agentctl doctor [--json]", "summary": "Check installed tools, wrappers, auth health, and browser readiness."},
            {"command": "capabilities", "usage": "agentctl capabilities [--json]", "summary": "Emit the machine-readable capability inventory and preferred interfaces."},
            {"command": "capability", "usage": "agentctl capability <key> [--json]", "summary": "Show the drill-down page for a single capability."},
            {"command": "status", "usage": "agentctl status [--repo <path>] [--all] [--json]", "summary": "Inspect repo-local or registry-backed deep workflow state."},
            {"command": "run", "usage": "agentctl run <workflow> [--repo <path>] [--worker-command <cmd>]", "summary": "Launch or resume a deep workflow through the shared runner."},
        ],
    },
    {
        "group": "research",
        "items": [
            {"command": "research web", "usage": "agentctl research web <query> [--limit N]", "summary": "Research current public web sources through the shared evidence contract."},
            {"command": "research github", "usage": "agentctl research github <query> [--limit N]", "summary": "Research GitHub repositories, code, issues, and releases through gh-first routing."},
            {"command": "research scout", "usage": "agentctl research scout <query> [--limit N]", "summary": "Run web and GitHub research together and merge them into one evidence envelope."},
        ],
    },
    {
        "group": "skills",
        "items": [
            {"command": "skills list", "usage": "agentctl skills list [--project] [--json]", "summary": "List installed skills through the official skills CLI."},
            {"command": "skills add", "usage": "agentctl skills add <source> [--skill <name>] [--ref <ref>] [--project]", "summary": "Install skills with provenance recording and optional pinning."},
            {"command": "skills check", "usage": "agentctl skills check [--project] [--json]", "summary": "Compare installed skills with the local provenance lock file."},
            {"command": "skills update", "usage": "agentctl skills update [--project] [--json]", "summary": "Refresh tracked skills from the lock file without broad unsafe updates."},
        ],
    },
    {
        "group": "maintenance",
        "items": [
            {"command": "maintenance check", "usage": "agentctl maintenance check [--json]", "summary": "Check command/docs/plugin drift and write a machine-readable maintenance report."},
            {"command": "maintenance audit", "usage": "agentctl maintenance audit [--json]", "summary": "Run the full maintenance pass, refresh docs, and update maintenance state."},
            {"command": "maintenance fix-docs", "usage": "agentctl maintenance fix-docs [--json]", "summary": "Regenerate the human-facing agentctl docs from current machine state."},
            {"command": "maintenance render-report", "usage": "agentctl maintenance render-report [--json]", "summary": "Render the maintenance Markdown page and JSON report without regenerating every doc."},
        ],
    },
]
CLOUD_READINESS = [
    {
        "name": "agentctl core",
        "classification": "cloud-ready-with-setup",
        "requirements": ["Python 3.12+", "agentctl files under $CODEX_HOME", "write access to workflow state"],
        "notes": "Pure Python stdlib control plane. Safe once the environment installs the home bundle.",
    },
    {
        "name": "skills wrapper layer",
        "classification": "cloud-ready-with-setup",
        "requirements": ["Node.js and npx", "skills CLI availability", "network access if installing from remotes"],
        "notes": "agentctl wraps official skills tooling rather than replacing it.",
    },
    {
        "name": "research web",
        "classification": "cloud-ready-with-setup",
        "requirements": ["network access", "public web reachability"],
        "notes": "Uses public web fetches and the shared evidence envelope.",
    },
    {
        "name": "research github",
        "classification": "cloud-ready-with-setup",
        "requirements": ["gh installed", "GitHub auth available in the environment"],
        "notes": "Prefers gh and only falls back to browser/web when GitHub CLI cannot answer the question.",
    },
    {
        "name": "research scout",
        "classification": "cloud-ready-with-setup",
        "requirements": ["web reachability", "gh installed", "GitHub auth"],
        "notes": "Runs web and GitHub tracks separately, then merges the evidence.",
    },
    {
        "name": "Playwright CLI",
        "classification": "cloud-ready-with-setup",
        "requirements": ["Node.js", "Playwright package", "Chromium or a compatible browser binary"],
        "notes": "Preferred browser adapter when a browser-capable CLI environment exists.",
    },
    {
        "name": "Playwright MCP",
        "classification": "cloud-ready-with-setup",
        "requirements": ["Playwright MCP server config", "browser runtime support"],
        "notes": "Peer browser interface to the CLI path; use whichever structured interface fits the task.",
    },
    {
        "name": "gh",
        "classification": "cloud-ready-with-setup",
        "requirements": ["GitHub CLI", "GitHub auth"],
        "notes": "Authoritative interface for GitHub-first workflows.",
    },
    {
        "name": "vercel",
        "classification": "cloud-ready-with-setup",
        "requirements": ["Vercel CLI", "Vercel auth"],
        "notes": "Detected now and suitable for later richer adapters once usage patterns are stable.",
    },
    {
        "name": "supabase",
        "classification": "cloud-ready-with-setup",
        "requirements": ["Supabase CLI", "project/auth context"],
        "notes": "First-class dual-route capability locally. Cloud use still depends on CLI plus MCP auth/setup being available.",
    },
    {
        "name": "firebase",
        "classification": "cloud-ready-with-setup",
        "requirements": ["Firebase CLI", "project/auth context"],
        "notes": "Detect-only in v1.",
    },
    {
        "name": "gcloud",
        "classification": "cloud-ready-with-setup",
        "requirements": ["gcloud CLI", "auth context", "project configuration"],
        "notes": "Detect-only in v1.",
    },
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _record_file(name: str, path: Path, *, require_marker: bool = True) -> dict[str, Any]:
    content = _read_text(path)
    has_marker = AUTO_MARKER in content if content else False
    return {
        "name": name,
        "path": str(path),
        "exists": path.exists(),
        "auto_generated": has_marker if require_marker else None,
        "size": len(content),
    }


def _record_reference(name: str, path: Path) -> dict[str, Any]:
    content = _read_text(path)
    return {
        "name": name,
        "path": str(path),
        "exists": path.exists(),
        "size": len(content),
    }


def _capability_docs(report: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key in capability_keys(report["capabilities_snapshot"]):
        path = AGENTCTL_CAPABILITIES_DOCS_DIR / f"{key}.md"
        items.append(_record_file(f"capability:{key}", path))
    return items


def _plugin_config_status() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {"path": str(CONFIG_PATH), "present": False, "enabled": False, "entry": None}
    payload = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    plugins = payload.get("plugins", {})
    entry = None
    enabled = False
    if isinstance(plugins, dict):
        for key in PLUGIN_CONFIG_KEYS:
            config = plugins.get(key)
            if isinstance(config, dict):
                entry = key
                enabled = bool(config.get("enabled"))
                break
    return {"path": str(CONFIG_PATH), "present": True, "enabled": enabled, "entry": entry}


def _plugin_status() -> dict[str, Any]:
    plugin_manifest = load_json(AGENTCTL_PLUGIN_MANIFEST_PATH, default={})
    router_skill = AGENTCTL_PLUGIN_ROUTER_SKILL_DIR / "SKILL.md"
    return {
        "name": AGENTCTL_PLUGIN_NAME,
        "path": str(AGENTCTL_PLUGIN_DIR),
        "exists": AGENTCTL_PLUGIN_DIR.exists(),
        "manifest_path": str(AGENTCTL_PLUGIN_MANIFEST_PATH),
        "manifest_exists": AGENTCTL_PLUGIN_MANIFEST_PATH.exists(),
        "manifest_name": plugin_manifest.get("name"),
        "router_skill_path": str(router_skill),
        "router_skill_exists": router_skill.exists(),
        "config": _plugin_config_status(),
    }


def _skills_status() -> list[dict[str, Any]]:
    return [
        {
            "name": MAINTENANCE_SKILL_NAME,
            "path": str(AGENTCTL_MAINTENANCE_SKILL_DIR),
            "exists": AGENTCTL_MAINTENANCE_SKILL_DIR.exists(),
        }
    ]


def _tests_status() -> list[dict[str, Any]]:
    tests = [
        AGENTCTL_HOME / "tests" / "test_capabilities.py",
        AGENTCTL_HOME / "tests" / "test_research.py",
        AGENTCTL_HOME / "tests" / "test_skills_ops.py",
        AGENTCTL_HOME / "tests" / "test_workflows.py",
        AGENTCTL_HOME / "tests" / "test_maintenance.py",
    ]
    return [{"name": path.name, "path": str(path), "exists": path.exists()} for path in tests]


def _add_finding(findings: list[dict[str, Any]], *, finding_id: str, title: str, severity: str, detail: str, path: str | None = None) -> None:
    findings.append(
        {
            "id": finding_id,
            "title": title,
            "severity": severity,
            "detail": detail,
            "path": path,
        }
    )


def _known_limitations(capabilities: dict[str, Any]) -> list[str]:
    limitations: list[str] = []
    gh = capabilities.get("tools", {}).get("gh", {})
    if gh.get("installed") and not gh.get("skill_supported"):
        limitations.append("`gh skill` is not available locally, so publish/preview wrappers remain disabled.")
    codex = capabilities.get("tools", {}).get("codex", {})
    if codex.get("installed") and not codex.get("worker_runtime_ready"):
        limitations.append(
            "The default local Codex runtime is not callable here. "
            "Use `agentctl run --worker-command ...` or configure `AGENTCTL_CODEX_WORKER_TEMPLATE` for unattended deep runs."
        )
    elif not codex.get("installed"):
        limitations.append(
            "Codex CLI is not detected locally. Unattended deep runs still work through explicit worker commands, "
            "but there is no auto-resolved Codex runtime."
        )
    browser = capabilities.get("tools", {}).get("playwright", {})
    if browser.get("status") != "ok":
        limitations.append("Playwright is available, but browser readiness is degraded until a Chromium or compatible browser binary is present.")
    for name in capabilities.get("detect_only_tools", []):
        limitations.append(f"`{name}` is detected but intentionally remains detect-only in v1.")
    return limitations


def _build_findings(
    *,
    docs: list[dict[str, Any]],
    references: list[dict[str, Any]],
    plugin: dict[str, Any],
    skills: list[dict[str, Any]],
    tests: list[dict[str, Any]],
    capabilities: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for record in docs:
        if not record["exists"]:
            _add_finding(
                findings,
                finding_id=f"doc-missing-{record['name']}",
                title=f"Missing doc: {record['name']}",
                severity="warn",
                detail="Required agentctl maintenance doc is missing and should be regenerated.",
                path=record["path"],
            )
        elif record["auto_generated"] is False:
            _add_finding(
                findings,
                finding_id=f"doc-stale-{record['name']}",
                title=f"Non-generated doc: {record['name']}",
                severity="warn",
                detail="Doc exists but does not carry the auto-generated marker, so drift cannot be trusted.",
                path=record["path"],
            )

    for record in references:
        if not record["exists"]:
            _add_finding(
                findings,
                finding_id=f"reference-missing-{record['name']}",
                title=f"Missing reference: {record['name']}",
                severity="warn",
                detail="A required agentctl reference file is missing.",
                path=record["path"],
            )

    if not plugin["exists"] or not plugin["manifest_exists"]:
        _add_finding(
            findings,
            finding_id="plugin-missing",
            title="Plugin packaging is incomplete",
            severity="error",
            detail="The local agentctl plugin directory or manifest is missing.",
            path=plugin["manifest_path"],
        )
    if plugin["exists"] and not plugin["router_skill_exists"]:
        _add_finding(
            findings,
            finding_id="plugin-router-missing",
            title="Plugin router skill is missing",
            severity="warn",
            detail="The local plugin exists but does not expose the router skill that makes agentctl discoverable in Codex.",
            path=plugin["router_skill_path"],
        )
    if plugin["manifest_exists"] and plugin.get("manifest_name") != AGENTCTL_PLUGIN_NAME:
        _add_finding(
            findings,
            finding_id="plugin-name-drift",
            title="Plugin manifest name drift",
            severity="error",
            detail="The plugin manifest name no longer matches the expected local plugin identity.",
            path=plugin["manifest_path"],
        )
    if not plugin["config"]["enabled"]:
        _add_finding(
            findings,
            finding_id="plugin-not-enabled",
            title="Plugin is not enabled in config.toml",
            severity="warn",
            detail="The local plugin exists but is not explicitly enabled in the Codex config.",
            path=plugin["config"]["path"],
        )

    for record in skills:
        if not record["exists"]:
            _add_finding(
                findings,
                finding_id=f"skill-missing-{record['name']}",
                title=f"Missing skill: {record['name']}",
                severity="error",
                detail="The maintenance skill is missing and the control plane cannot self-audit cleanly.",
                path=record["path"],
            )

    for record in tests:
        if not record["exists"]:
            _add_finding(
                findings,
                finding_id=f"test-missing-{record['name']}",
                title=f"Missing test: {record['name']}",
                severity="warn",
                detail="The agentctl platform test surface is incomplete.",
                path=record["path"],
            )

    capabilities_status = capabilities.get("summary", {}).get("status", "unknown")
    if capabilities_status == "error":
        _add_finding(
            findings,
            finding_id="tooling-error",
            title="Capability report has errors",
            severity="error",
            detail="agentctl doctor/capabilities currently report an error state. Fix the control plane before trusting automation.",
            path=str(CAPABILITIES_PATH),
        )
    elif capabilities_status == "degraded":
        _add_finding(
            findings,
            finding_id="tooling-degraded",
            title="Capability report is degraded",
            severity="warn",
            detail="At least one tool or browser route is degraded. Keep the limitation documented and explicit.",
            path=str(CAPABILITIES_PATH),
        )

    return findings


def build_maintenance_report() -> dict[str, Any]:
    capabilities = build_capabilities_report()
    docs = [_record_file(name, path) for name, path in MAINTENANCE_DOCS.items()]
    docs.extend(_capability_docs({"capabilities_snapshot": capabilities}))
    references = [_record_reference(name, path) for name, path in REFERENCE_DOCS.items()]
    plugin = _plugin_status()
    skills = _skills_status()
    tests = _tests_status()
    findings = _build_findings(
        docs=docs,
        references=references,
        plugin=plugin,
        skills=skills,
        tests=tests,
        capabilities=capabilities,
    )

    total_checks = len(docs) + len(references) + len(skills) + len(tests) + 3
    blocked_findings = [item for item in findings if item["severity"] == "error"]
    open_findings = len(findings)
    passed_checks = max(total_checks - open_findings, 0)
    status = "error" if blocked_findings else "degraded" if findings else "ok"

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "root": str(AGENTCTL_HOME),
        "summary": {
            "status": status,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "open_findings": open_findings,
            "blocked_findings": len(blocked_findings),
        },
        "command_surface": COMMAND_GROUPS,
        "artifacts": {
            "capabilities": str(CAPABILITIES_PATH),
            "doctor": str(DOCTOR_REPORT_PATH),
            "maintenance_report": str(MAINTENANCE_REPORT_PATH),
            "maintenance_state": str(MAINTENANCE_STATE_PATH),
        },
        "docs": docs,
        "references": references,
        "skills": skills,
        "plugin": plugin,
        "tests": tests,
        "cloud_readiness": CLOUD_READINESS,
        "capabilities_snapshot": capabilities,
        "known_limitations": _known_limitations(capabilities),
        "findings": findings,
    }


def _remaining_items(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, finding in enumerate(findings, start=1):
        items.append(
            {
                "id": finding["id"],
                "title": finding["title"],
                "line": index,
                "blocked": finding["severity"] == "error",
            }
        )
    return items


def _save_workflow_registry(state: dict[str, Any]) -> None:
    registry = load_json(WORKFLOW_REGISTRY_PATH, default={})
    key = f"{state['repo_root']}::{state['workflow_name']}"
    registry[key] = {
        "schema_version": state.get("schema_version", SCHEMA_VERSION),
        "workflow_name": state["workflow_name"],
        "skill_name": state["skill_name"],
        "repo_root": state["repo_root"],
        "checklist_path": state["checklist_path"],
        "progress_path": state["progress_path"],
        "status": state["status"],
        "iteration": state["iteration"],
        "tasks_total": state["tasks_total"],
        "tasks_done": state["tasks_done"],
        "tasks_open": state["tasks_open"],
        "tasks_blocked": state["tasks_blocked"],
        "ready_allowed": state.get("ready_allowed", False),
        "updated_at": state["updated_at"],
    }
    save_json(WORKFLOW_REGISTRY_PATH, registry)


def _maintenance_state(report: dict[str, Any]) -> dict[str, Any]:
    findings = report["findings"]
    blocked_items = [item for item in findings if item["severity"] == "error"]
    status = "complete" if not findings else "blocked" if blocked_items else "running"
    return {
        "schema_version": SCHEMA_VERSION,
        "workflow_name": MAINTENANCE_WORKFLOW_NAME,
        "skill_name": MAINTENANCE_SKILL_NAME,
        "repo_root": str(AGENTCTL_HOME.parent),
        "checklist_path": str(MAINTENANCE_DOCS["maintenance"]),
        "progress_path": str(MAINTENANCE_REPORT_PATH),
        "status": status,
        "iteration": 1,
        "max_iterations": 1,
        "stagnant_iterations": 0,
        "max_stagnant_iterations": 1,
        "tasks_total": report["summary"]["total_checks"],
        "tasks_done": report["summary"]["passed_checks"],
        "tasks_open": report["summary"]["open_findings"],
        "tasks_blocked": report["summary"]["blocked_findings"],
        "last_batch": ["Refreshed agentctl maintenance report"],
        "last_validation": {
            "maintenance_status": report["summary"]["status"],
            "capabilities_status": report["capabilities_snapshot"]["summary"]["status"],
            "plugin_enabled": report["plugin"]["config"]["enabled"],
        },
        "last_error": {},
        "ready_allowed": report["summary"]["open_findings"] == 0,
        "remaining_items": _remaining_items(findings),
        "blocked_items": _remaining_items(blocked_items),
        "evidence": [
            {"kind": "file", "path": str(CAPABILITIES_PATH)},
            {"kind": "file", "path": str(DOCTOR_REPORT_PATH)},
            {"kind": "file", "path": str(MAINTENANCE_REPORT_PATH)},
        ],
        "updated_at": report["generated_at"],
    }


def _render_overview(report: dict[str, Any]) -> str:
    lines = [
        AUTO_MARKER,
        "# Agentctl Overview",
        "",
        "## Purpose",
        "",
        "`agentctl` is the thin Codex-first control plane for discovery, routing, health checks, deep-workflow launch, and machine-readable state.",
        "",
        "## Layers",
        "",
        "1. Repo guidance in `AGENTS.md` and a small set of stable docs.",
        "2. Skills for repeated workflows such as UI, testing, refactor, docs, research, and maintenance.",
        "3. `agentctl` as the runtime control plane above those skills and above authoritative vendor interfaces.",
        "4. Plugin packaging so the system can be installed and surfaced consistently.",
        "",
        "## Current Status",
        "",
        f"- Maintenance status: `{report['summary']['status']}`",
        f"- Checks passed: {report['summary']['passed_checks']} / {report['summary']['total_checks']}",
        f"- Open findings: {report['summary']['open_findings']}",
        f"- Blocked findings: {report['summary']['blocked_findings']}",
        "",
        "## Authoritative Interfaces",
        "",
        "- Skill installation and update stay with the official `skills` CLI and `gh skill` when available.",
        "- Vendor CLIs remain authoritative for their own platforms.",
        "- Playwright remains the browser authority.",
        "- Codex remains the execution engine for local and cloud work.",
        "",
        "## First Things To Read",
        "",
        "- Start with `agentctl doctor` when you need a compact health check.",
        "- Use `agentctl capabilities` when you need the full capability menu and preferred front doors.",
        "- Use `agentctl capability <key>` when you need the drill-down page for a specific capability or vendor surface.",
        "- Use `agentctl status --all` to see which durable deep workflows are active now.",
        "- Use `agentctl maintenance audit` after changing command surface, packaging, state contracts, or docs generators.",
        "",
        "## Common Agent Flows",
        "",
        "- Capability discovery: `agentctl doctor` then `agentctl capabilities` if a broader inventory is needed.",
        "- External research: `agentctl research web|github|scout <query>` and carry the JSON evidence + brief into implementation.",
        "- Deep remediation: `agentctl run <workflow>` and trust `.codex-workflows/<workflow>/state.json` over chat history.",
        "- Autonomous deep remediation only counts when a real worker command exists. The runner loop is deterministic; the worker must be real.",
        "- Control-plane upkeep: `$agentctl-maintenance-engineer` or `agentctl maintenance audit`.",
        "",
        "## Verified Workflow Guarantees",
        "",
        "- The shared runner is covered for `complete`, `stalled`, and `blocked` terminal states.",
        "- The CLI front door is covered end-to-end with `agentctl run ...` plus `agentctl status --json` in a temp repo.",
        "- Explicit worker-command execution is a supported and tested path for unattended deep runs.",
        "- Registry writes are protected against transient Windows rename contention and against parallel shared-registry updates.",
        "- Fresh bundle installs are smoke-tested and allowed to finish `ok` when only degraded-but-documented capabilities remain.",
        "- The remaining environment-specific limitation is the default local Codex runtime on this machine; if that runtime is unavailable, use an explicit worker command or `AGENTCTL_CODEX_WORKER_TEMPLATE`.",
        "",
        "## Capability-First Rule",
        "",
        "Agents should choose a capability front door first and ignore transport details unless the capability itself is degraded.",
        "",
        "- Good: \"use the research capability\" or \"use the browser capability\".",
        "- Bad: \"start by choosing between CLI, MCP, or plugin\".",
        "",
        "The capability registry exists to collapse those overlaps into one stable route.",
        "",
        "## Key Files",
        "",
        "- Control plane home: `agentctl/`",
        "- Capabilities snapshot: `agentctl/state/capabilities.json`",
        "- Maintenance report: `docs/agentctl/maintenance-report.json`",
        "- Maintenance state: `.codex-workflows/agentctl-maintenance/state.json`",
        "",
        "## What Agentctl Does Not Own",
        "",
        "- It does not replace the official `skills` CLI or `gh skill`.",
        "- It does not replace vendor CLIs such as `gh`, `vercel`, or `supabase`.",
        "- It does not replace Playwright as the browser runtime.",
        "- It does not replace Codex execution or cloud environments.",
        "",
    ]
    if report["known_limitations"]:
        lines.extend(["## Known Limitations", ""])
        for item in report["known_limitations"]:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_command_map() -> str:
    lines = [
        AUTO_MARKER,
        "# Agentctl Command Map",
        "",
        "This is the frozen v1 command surface that maintenance checks expect.",
        "",
        "## Quick Routing Rules",
        "",
        "- `doctor` is the shortest health-oriented entrypoint.",
        "- `capabilities` is the full menu for capability discovery.",
        "- `capability <key>` is the drill-down page for a single capability and should be preferred before choosing lower-level vendor tools.",
        "- `status` is for workflow progress, not general health.",
        "- `run` is only for deep workflows that use the shared runner/state contract.",
        "- `run` should prefer a real worker runtime such as Codex CLI or an explicit worker command, not chat-only repetition.",
        "- `research` is for evidence creation, not implementation.",
        "- `skills` wraps official install/update tooling and provenance checks.",
        "- `maintenance` is only for the control plane itself.",
        "",
        "## Verification Notes",
        "",
        "- `run` is tested at two levels: the shared workflow runner directly and the public `agentctl run` CLI path.",
        "- Shared state transitions are expected to end as `complete`, `blocked`, or `stalled`; `ready_allowed` must gate any `complete` state.",
        "- Shared-registry updates are expected to tolerate concurrent deep workflows without losing entries.",
        "",
    ]
    for group in COMMAND_GROUPS:
        lines.extend([f"## {group['group'].title()}", ""])
        for item in group["items"]:
            lines.append(f"- `{item['usage']}`")
            lines.append(f"  - {item['summary']}")
        lines.append("")
        if group["group"] == "core":
            lines.extend(
                [
                    "Typical sequence:",
                    "",
                    "- `agentctl doctor`",
                    "- `agentctl capabilities` if you need the full menu",
                    "- `agentctl status --all` if you need workflow progress",
                    "- `agentctl run <workflow>` only when a deep workflow is the right shape",
                    "- If no worker runtime is healthy, configure `--worker-command` or `AGENTCTL_CODEX_WORKER_TEMPLATE` before treating the run as unattended",
                ]
            )
        elif group["group"] == "research":
            lines.extend(
                [
                    "Typical sequence:",
                    "",
                    "- `agentctl research web <query>` for current official docs or standards",
                    "- `agentctl research github <query>` for field practice and repository evidence",
                    "- `agentctl research scout <query>` when both are needed before implementation",
                ]
            )
        elif group["group"] == "skills":
            lines.extend(
                [
                    "Typical sequence:",
                    "",
                    "- `agentctl skills list` to inspect current installs",
                    "- `agentctl skills check` to inspect provenance and local-vs-external management",
                    "- `agentctl skills add ...` only when you are intentionally extending the skill surface",
                ]
            )
        elif group["group"] == "maintenance":
            lines.extend(
                [
                    "Typical sequence:",
                    "",
                    "- `agentctl maintenance check` for a quick control-plane inspection",
                    "- `agentctl maintenance audit` after code or contract changes",
                    "- `agentctl maintenance fix-docs` only when the docs need regeneration without broader change",
                ]
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_state_schema(report: dict[str, Any]) -> str:
    reference = _read_text(STATE_SCHEMA_REFERENCE_PATH).strip()
    if reference.startswith("# "):
        reference_lines = reference.splitlines()
        reference = "\n".join(reference_lines[1:]).lstrip()
    lines = [
        AUTO_MARKER,
        "# Agentctl State Schema",
        "",
        "## Deep Workflow State",
        "",
        "The shared deep-workflow schema lives at `agentctl/references/state-schema.md` and is the canonical contract for repo-local workflow state.",
        "",
        "## Maintenance Report Schema",
        "",
        "The maintenance report is stored at `docs/agentctl/maintenance-report.json` and is mirrored into `.codex-workflows/agentctl-maintenance/state.json`.",
        "",
        "Top-level report fields:",
        "",
        "- `schema_version`",
        "- `generated_at`",
        "- `root`",
        "- `summary`",
        "- `command_surface`",
        "- `artifacts`",
        "- `docs`",
        "- `references`",
        "- `skills`",
        "- `plugin`",
        "- `tests`",
        "- `cloud_readiness`",
        "- `capabilities_snapshot`",
        "- `known_limitations`",
        "- `findings`",
        "",
        "## Lifecycle Semantics",
        "",
        "- Repo-local workflow state is canonical; the global registry is only a convenience mirror.",
        "- `ready_allowed` is the completion gate. A workflow must not claim `complete` unless this is `true`.",
        "- `remaining_items` and `blocked_items` should always be derivable from the current checklist, not chat memory.",
        "- `last_validation` should capture the smallest real validation that supports the last completed batch.",
        "- Shared-registry writes must remain concurrency-safe because multiple deep workflows may update the registry at the same time.",
        "",
        "## Status Meanings",
        "",
        "- `initializing`: state exists but the first meaningful batch has not completed yet.",
        "- `running`: the workflow is active and more work remains.",
        "- `complete`: all tracked work is done and the ready gate passes.",
        "- `blocked`: remaining work exists but a real blocker currently prevents completion.",
        "- `stalled`: repeated attempts failed to make meaningful progress.",
        "- `error`: the state itself is malformed or execution failed before a valid workflow step completed.",
        "",
        "## Current Shared Workflow Fields",
        "",
    ]
    if reference:
        lines.append(reference)
        lines.append("")
    lines.extend(
        [
            "## Current Maintenance Summary",
            "",
            "```json",
            json.dumps(report["summary"], indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _render_capability_registry(report: dict[str, Any]) -> str:
    capability_items = report["capabilities_snapshot"].get("capabilities", [])
    lines = [
        AUTO_MARKER,
        "# Agentctl Capability Registry",
        "",
        "The machine-readable registry lives at `agentctl/state/capabilities.json`.",
        "",
        "## How To Use This Registry",
        "",
        "- Treat `front_door` as the default interface an agent should choose first.",
        "- Treat `backing_interfaces` as implementation detail and health metadata.",
        "- Only care about raw CLI/MCP/plugin distinctions if a capability is degraded or missing.",
        "- Use `overlap_policy` to understand why multiple interfaces collapse into one capability.",
        "",
        "## Capability Menu",
        "",
    ]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for payload in capability_items:
        grouped.setdefault(payload.get("group", "other"), []).append(payload)
    for group_key in ("control-plane", "workflow-skills", "research-and-verification", "integrations"):
        items = grouped.get(group_key, [])
        if not items:
            continue
        lines.append(f"### {group_key.replace('-', ' ').title()}")
        lines.append("")
        for payload in items:
            lines.append(f"- `{payload.get('key', 'unknown')}` uses `{payload.get('front_door', 'unknown')}` and is currently `{payload.get('status', 'unknown')}`.")
            lines.append(f"  - Overlap policy: {payload.get('overlap_policy', 'Not documented.')}")
            if payload.get("advisory"):
                lines.append(f"  - Advisory: {payload['advisory']}")
            lines.append(f"  - Page: `docs/agentctl/capabilities/{payload.get('key', 'unknown')}.md`")
        lines.append("")
    lines.extend(
        [
            "## Registry Shape",
            "",
            "- `schema_version`",
            "- `generated_at`",
            "- `summary`",
            "- `installed_skills`",
            "- `local_skills`",
            "- `plugins`",
            "- `mcp_servers`",
            "- `tools`",
            "- `capabilities`",
            "- `overlap_analysis`",
            "- `detect_only_tools`",
            "",
            "## Current Summary",
            "",
            "```json",
            json.dumps(
                {
                    "status": report["capabilities_snapshot"]["summary"].get("status", "unknown"),
                    "installed_skill_count": report["capabilities_snapshot"]["summary"].get("installed_skill_count", 0),
                    "local_skill_count": report["capabilities_snapshot"]["summary"].get("local_skill_count", 0),
                    "enabled_plugin_count": report["capabilities_snapshot"]["summary"].get("enabled_plugin_count", 0),
                    "configured_mcp_count": report["capabilities_snapshot"]["summary"].get("configured_mcp_count", 0),
                    "required_capability_count": report["capabilities_snapshot"]["summary"].get("required_capability_count", 0),
                    "optional_capability_count": report["capabilities_snapshot"]["summary"].get("optional_capability_count", 0),
                    "optional_attention_count": report["capabilities_snapshot"]["summary"].get("optional_attention_count", 0),
                },
                indent=2,
                sort_keys=True,
            ),
            "```",
            "",
        ]
    )
    overlap_items = report["capabilities_snapshot"].get("overlap_analysis", [])
    if overlap_items:
        lines.extend(["## Overlap Decisions", ""])
        for item in overlap_items:
            lines.append(f"- `{item['capability']}`: {item['policy']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_capability_page(report: dict[str, Any], key: str) -> str:
    detail = capability_detail(report["capabilities_snapshot"], key)
    if detail is None:
        raise KeyError(f"unknown capability: {key}")

    lines = [
        AUTO_MARKER,
        f"# {detail['label']}",
        "",
        f"- Key: `{detail['key']}`",
        f"- Group: `{detail['group']}`",
        f"- Status: `{detail['status']}`",
        f"- Front door: `{detail['front_door']}`",
        "",
        "## Summary",
        "",
        detail["summary"],
        "",
    ]

    if detail.get("skills"):
        lines.extend(["## Navigation Skills", ""])
        for name in detail["skills"]:
            lines.append(f"- `{name}`")
        lines.append("")

    if detail.get("entrypoints"):
        lines.extend(["## Entry Points", ""])
        for entry in detail["entrypoints"]:
            lines.append(f"- `{entry}`")
        lines.append("")

    if detail.get("routing_notes"):
        lines.extend(["## Routing Notes", ""])
        for note in detail["routing_notes"]:
            lines.append(f"- {note}")
        lines.append("")

    if detail.get("advisory"):
        lines.extend(["## Advisory", "", f"- {detail['advisory']}", ""])

    if detail.get("backing_interfaces"):
        lines.extend(["## Backing Interfaces", ""])
        for item in detail["backing_interfaces"]:
            extras: list[str] = []
            if "enabled" in item:
                extras.append(f"enabled={str(item['enabled']).lower()}")
            if "configured" in item:
                extras.append(f"configured={str(item['configured']).lower()}")
            suffix = f" ({', '.join(extras)})" if extras else ""
            lines.append(f"- `{item['kind']}` `{item['name']}` [{item['status']}]"+suffix)
        lines.append("")

    if detail.get("cloud_readiness"):
        lines.extend(["## Cloud Readiness", ""])
        for item in detail["cloud_readiness"]:
            lines.append(f"- `{item['name']}`: `{item['classification']}`")
            lines.append(f"  - Requirements: {', '.join(item['requirements'])}")
            lines.append(f"  - Notes: {item['notes']}")
        lines.append("")

    lines.extend(["## Overlap Policy", "", f"- {detail['overlap_policy']}", ""])
    return "\n".join(lines).rstrip() + "\n"


def _render_cloud_readiness(report: dict[str, Any]) -> str:
    capabilities_by_key = {
        item["key"]: item for item in report["capabilities_snapshot"].get("capabilities", [])
    }
    browser_status = capabilities_by_key.get("browser-automation", {}).get("status", "unknown")
    lines = [
        AUTO_MARKER,
        "# Agentctl Cloud Readiness",
        "",
        "Cloud support is explicit, not assumed. A plugin install is not enough without a cloud environment that provides the required tools and auth.",
        "",
        "## Minimum Cloud Bundle",
        "",
        "- Python 3.12+ for `agentctl` itself",
        "- Node.js and `npx` for the skills wrapper layer",
        "- Playwright plus a Chromium-capable browser route if browser automation is required",
        "- Auth and configuration for any vendor CLI you expect to use in cloud",
        "- Write access to repo-local `.codex-workflows/` state and any generated docs/evidence paths",
        "",
        "## Readiness Matrix",
        "",
    ]
    for item in CLOUD_READINESS:
        lines.append(f"- `{item['name']}`: `{item['classification']}`")
        lines.append(f"  - Requirements: {', '.join(item['requirements'])}")
        lines.append(f"  - Notes: {item['notes']}")
    lines.extend(
        [
            "",
            "## Cloud Bring-Up Checklist",
            "",
            "- Install the `agentctl` bundle under `$CODEX_HOME`.",
            "- Verify `agentctl doctor` is healthy in the cloud environment itself.",
            "- Verify vendor CLI auth before relying on GitHub-, Vercel-, or Supabase-backed flows.",
        "- Verify the browser route before relying on research, UI, or test workflows that need runtime inspection.",
        "- Verify the deep-run worker route before relying on unattended checklist completion. A checklist alone is not a worker.",
        "- Treat any capability not explicitly marked healthy in cloud as unsupported until proven otherwise.",
            "",
            "## Current Local Signals",
            "",
            f"- Capability summary: `{report['capabilities_snapshot']['summary']['status']}`",
            f"- Browser route: `{browser_status}`",
            f"- GitHub CLI skill support: `{str(report['capabilities_snapshot']['tools']['gh'].get('skill_supported', False)).lower()}`",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _render_maintenance(report: dict[str, Any]) -> str:
    lines = [
        AUTO_MARKER,
        "# Agentctl Maintenance",
        "",
        "## Last Run",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Status: `{report['summary']['status']}`",
        f"- Checks passed: {report['summary']['passed_checks']} / {report['summary']['total_checks']}",
        f"- Open findings: {report['summary']['open_findings']}",
        f"- Blocked findings: {report['summary']['blocked_findings']}",
        "",
        "## When to Run Maintenance",
        "",
        "- After changing `agentctl` commands, adapters, or state contracts.",
        "- After changing plugin metadata, plugin skills, or packaging layout.",
        "- After adding or removing supported CLIs or browser routes.",
        "- Before trusting cloud-readiness assumptions for a new workflow.",
        "",
        "## Operator Runbook",
        "",
        "1. Run `agentctl maintenance check` for a quick signal.",
        "2. If command surface, docs, or packaging changed, run `agentctl maintenance audit`.",
        "3. Read `maintenance.md`, `maintenance-report.json`, and `.codex-workflows/agentctl-maintenance/state.json` together.",
        "4. If findings are doc-only, prefer `agentctl maintenance fix-docs` over hand edits.",
        "5. Re-run the relevant tests and smoke checks before trusting a green maintenance state.",
        "",
        "## What Must Be Updated After Changes",
        "",
        "- Refresh `docs/agentctl/*.md` from machine state.",
        "- Keep `state-schema.md`, `capability-registry.md`, and `maintenance-contract.md` aligned with code.",
        "- Re-run tests for `agentctl` and the shared workflow tools.",
        "- Re-run at least one CLI-level deep-workflow smoke after changing runner/state/guard behavior.",
        "- Keep `AGENTS.md` aligned with the intended front door.",
        "",
        "## Verification Expectations",
        "",
        "- `python -m unittest discover -s agentctl/tests -p \"test_*.py\"` passes.",
        "- `python -m unittest discover -s workflow-tools/tests -p \"test_*.py\"` passes.",
        "- A temp-repo `agentctl run <workflow>` smoke can reach a correct terminal state with a real or explicit worker command.",
        "- Fresh bundle install smoke keeps `bootstrap-report.json` truthful and does not fail purely on documented degraded capabilities.",
        "",
        "## Clean State Expectations",
        "",
        "- `maintenance-report.json` has `status: ok`.",
        "- `.codex-workflows/agentctl-maintenance/state.json` has `status: complete` and `ready_allowed: true`.",
        "- `agentctl doctor` stays compact and health-focused.",
        "- `agentctl capabilities` stays capability-first.",
        "- `agentctl status --all` surfaces durable active workflows and hides stale temp history by default.",
        "",
        "## Maintenance Checklist",
        "",
    ]
    if report["findings"]:
        for finding in report["findings"]:
            lines.append(f"- [ ] {finding['title']}")
            lines.append(f"  - Severity: `{finding['severity']}`")
            lines.append(f"  - Detail: {finding['detail']}")
            if finding.get("path"):
                lines.append(f"  - Path: `{finding['path']}`")
    else:
        lines.append("- [x] No open maintenance findings remain.")
    lines.extend(["", "## Known Limitations", ""])
    if report["known_limitations"]:
        for item in report["known_limitations"]:
            lines.append(f"- {item}")
    else:
        lines.append("- None recorded.")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_docs(report: dict[str, Any], *, include_all: bool, include_maintenance_page: bool) -> None:
    if include_all:
        save_text(MAINTENANCE_DOCS["overview"], _render_overview(report))
        save_text(MAINTENANCE_DOCS["command-map"], _render_command_map())
        save_text(MAINTENANCE_DOCS["state-schema"], _render_state_schema(report))
        save_text(MAINTENANCE_DOCS["capability-registry"], _render_capability_registry(report))
        save_text(MAINTENANCE_DOCS["cloud-readiness"], _render_cloud_readiness(report))
        AGENTCTL_CAPABILITIES_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        for key in capability_keys(report["capabilities_snapshot"]):
            save_text(AGENTCTL_CAPABILITIES_DOCS_DIR / f"{key}.md", _render_capability_page(report, key))
    if include_all or include_maintenance_page:
        save_text(MAINTENANCE_DOCS["maintenance"], _render_maintenance(report))


def _persist(report: dict[str, Any]) -> dict[str, Any]:
    save_json(CAPABILITIES_PATH, report["capabilities_snapshot"])
    save_json(DOCTOR_REPORT_PATH, report["capabilities_snapshot"])
    save_json(MAINTENANCE_REPORT_PATH, report)
    state = _maintenance_state(report)
    save_json(MAINTENANCE_STATE_PATH, state)
    _save_workflow_registry(state)
    return report


def maintenance_check() -> dict[str, Any]:
    return _persist(build_maintenance_report())


def maintenance_render_report() -> dict[str, Any]:
    report = build_maintenance_report()
    _write_docs(report, include_all=False, include_maintenance_page=True)
    final_report = build_maintenance_report()
    _write_docs(final_report, include_all=False, include_maintenance_page=True)
    return _persist(final_report)


def maintenance_fix_docs() -> dict[str, Any]:
    report = build_maintenance_report()
    _write_docs(report, include_all=True, include_maintenance_page=True)
    final_report = build_maintenance_report()
    _write_docs(final_report, include_all=True, include_maintenance_page=True)
    return _persist(final_report)


def maintenance_audit() -> dict[str, Any]:
    return maintenance_fix_docs()


def print_maintenance_human(payload: dict[str, Any], *, as_json: bool = False) -> None:
    if as_json:
        print_json(payload)
        return

    summary = payload["summary"]
    print(f"Status: {summary['status']}")
    print(f"Checks: {summary['passed_checks']} / {summary['total_checks']}")
    print(f"Open findings: {summary['open_findings']}")
    print(f"Blocked findings: {summary['blocked_findings']}")
    print("")
    print("Artifacts")
    print(f"- Maintenance report: {payload['artifacts']['maintenance_report']}")
    print(f"- Maintenance state: {payload['artifacts']['maintenance_state']}")
    print("")
    print("Plugin")
    print(f"- Path: {payload['plugin']['path']}")
    print(f"- Manifest: {'ok' if payload['plugin']['manifest_exists'] else 'missing'}")
    print(f"- Config enabled: {str(payload['plugin']['config']['enabled']).lower()}")
    print("")
    print("Findings")
    if not payload["findings"]:
        print("- none")
    else:
        for finding in payload["findings"]:
            print(f"- [{finding['severity']}] {finding['title']}")
