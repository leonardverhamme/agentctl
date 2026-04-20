from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from . import config_layers as config_layers_module
from . import guidance as guidance_module
from . import inventory as inventory_module
from .branding import COMPATIBILITY_COMMAND, PUBLIC_COMMAND, PUBLIC_DISPLAY_NAME, PUBLIC_DOCS_DIRNAME, PUBLIC_PRODUCT_NAME
from .capabilities import CAPABILITY_GROUPS, build_capabilities_report, capability_detail, capability_doc_path, capability_keys
from .common import load_json, print_json, save_json, save_text, utc_now
from .config_layers import _load_toml
from .guidance import GUIDANCE_SCHEMA_VERSION, refresh_guidance_snapshot
from .inventory import INVENTORY_SCHEMA_VERSION, refresh_inventory_snapshot
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
    GUIDANCE_PATH,
    INVENTORY_PATH,
    LEGACY_AGENTCTL_MAINTENANCE_SKILL_DIR,
    LEGACY_AGENTCTL_PLUGIN_ROUTER_SKILL_DIR,
    LEGACY_MAINTENANCE_STATE_PATH,
    MAINTENANCE_CONTRACT_REFERENCE_PATH,
    MAINTENANCE_REPORT_PATH,
    MAINTENANCE_STATE_PATH,
    MaintenanceWorkspace,
    SKILLS_DIR,
    SOURCE_REPO_ROOT,
    STATE_SCHEMA_REFERENCE_PATH,
    WORKFLOW_REGISTRY_PATH,
    maintenance_workspace,
)
from .skill_map import write_skill_map_docs


SCHEMA_VERSION = 1
AUTO_MARKER = f"<!-- {PUBLIC_PRODUCT_NAME}:auto-generated -->"
MAINTENANCE_WORKFLOW_NAME = "agentcli-maintenance"
LEGACY_MAINTENANCE_WORKFLOW_NAME = "agentctl-maintenance"
MAINTENANCE_SKILL_NAME = "agentcli-maintenance-engineer"
LEGACY_MAINTENANCE_SKILL_NAME = "agentctl-maintenance-engineer"
LEGACY_MAINTENANCE_CAPABILITY_KEY = "agentctl-maintenance"
MAINTENANCE_DOCS: dict[str, Path] = {
    "overview": AGENTCTL_DOCS_DIR / "overview.md",
    "command-map": AGENTCTL_DOCS_DIR / "command-map.md",
    "inventory": AGENTCTL_DOCS_DIR / "inventory.md",
    "skill-map": AGENTCTL_DOCS_DIR / "skill-map.md",
    "state-schema": AGENTCTL_DOCS_DIR / "state-schema.md",
    "capability-registry": AGENTCTL_DOCS_DIR / "capability-registry.md",
    "cloud-readiness": AGENTCTL_DOCS_DIR / "cloud-readiness.md",
    "maintenance": AGENTCTL_DOCS_DIR / "maintenance.md",
}
GENERATED_BINARY_ASSETS: dict[str, Path] = {
    "skill-map-pdf": AGENTCTL_DOCS_DIR / "skill-map.pdf",
}
REFERENCE_DOCS: dict[str, Path] = {
    "state-schema": STATE_SCHEMA_REFERENCE_PATH,
    "capability-registry": CAPABILITY_REGISTRY_REFERENCE_PATH,
    "maintenance-contract": MAINTENANCE_CONTRACT_REFERENCE_PATH,
    "cloud-readiness": CLOUD_READINESS_REFERENCE_PATH,
}
SAFE_MAINTENANCE_ROOTS = (SOURCE_REPO_ROOT,)
PLUGIN_CONFIG_KEYS = (AGENTCTL_PLUGIN_NAME, f"{AGENTCTL_PLUGIN_NAME}@local")
COMMAND_GROUPS = [
    {
        "group": "core",
        "items": [
            {"command": "doctor", "usage": f"{PUBLIC_COMMAND} doctor [--fix] [--json]", "summary": "Check installed tools, wrappers, auth health, and browser readiness, with optional local repair."},
            {"command": "capabilities", "usage": f"{PUBLIC_COMMAND} capabilities [--json]", "summary": "Show the compact grouped capability menu, not the raw installed inventory."},
            {"command": "capability", "usage": f"{PUBLIC_COMMAND} capability <key> [--json]", "summary": "Show the drill-down page for a capability group or a single capability."},
            {"command": "skill-map", "usage": f"{PUBLIC_COMMAND} skill-map [--json]", "summary": "Generate the human-facing skill/menu map and the matching one-page PDF."},
            {"command": "status", "usage": f"{PUBLIC_COMMAND} status [--repo <path>] [--all] [--json]", "summary": "Inspect repo-local or registry-backed deep workflow state."},
            {"command": "run", "usage": f"{PUBLIC_COMMAND} run <workflow> [--repo <path>] [--worker-command <cmd>]", "summary": "Launch or resume a deep workflow through the shared runner."},
            {"command": "loop", "usage": f"{PUBLIC_COMMAND} loop <name> [--repo <path>] (--task <text> | --task-file <path>)", "summary": "Launch a generic long task through the shared disk-backed loop when no dedicated deep workflow already fits."},
            {"command": "self-check", "usage": f"{PUBLIC_COMMAND} self-check [--json]", "summary": "Compare wrapper version, bundle version, config schema, and plugin health."},
            {"command": "version", "usage": f"{PUBLIC_COMMAND} version [--json]", "summary": "Show wrapper and bundle version information."},
            {"command": "upgrade", "usage": f"{PUBLIC_COMMAND} upgrade [--version <tag>] [--json]", "summary": "Upgrade the installed bundle from its recorded release source."},
        ],
    },
    {
        "group": "research",
        "items": [
            {"command": "research web", "usage": f"{PUBLIC_COMMAND} research web <query> [--limit N]", "summary": "Research current public web sources through the shared evidence contract."},
            {"command": "research github", "usage": f"{PUBLIC_COMMAND} research github <query> [--limit N]", "summary": "Research GitHub repositories, code, issues, and releases through gh-first routing."},
            {"command": "research scout", "usage": f"{PUBLIC_COMMAND} research scout <query> [--limit N]", "summary": "Run web and GitHub research together and merge them into one evidence envelope."},
        ],
    },
    {
        "group": "inventory",
        "items": [
            {"command": "inventory refresh", "usage": f"{PUBLIC_COMMAND} inventory refresh [--repo <path>] [--json]", "summary": "Refresh and persist the raw autodetected inventory snapshot."},
            {"command": "inventory show", "usage": f"{PUBLIC_COMMAND} inventory show [--kind tools|skills|plugins|mcp|all] [--scope user|repo|all] [--json]", "summary": "Inspect the raw autodetected inventory behind the curated capability menu."},
            {"command": "inventory item", "usage": f"{PUBLIC_COMMAND} inventory item <kind>:<name> [--json]", "summary": "Show one raw inventory record."},
        ],
    },
    {
        "group": "config",
        "items": [
            {"command": "config show", "usage": f"{PUBLIC_COMMAND} config show [--repo <path>] [--json]", "summary": "Show bundled, user, repo, and effective config layers."},
            {"command": "config path", "usage": f"{PUBLIC_COMMAND} config path [--scope bundled|user|repo] [--json]", "summary": "Show the path for one config scope."},
            {"command": "config set", "usage": f"{PUBLIC_COMMAND} config set <key> <value> [--scope user|repo] [--json]", "summary": "Set a structured config key in the user or repo layer."},
            {"command": "config unset", "usage": f"{PUBLIC_COMMAND} config unset <key> [--scope user|repo] [--json]", "summary": "Remove a structured config key from the user or repo layer."},
        ],
    },
    {
        "group": "skills",
        "items": [
            {"command": "skills list", "usage": f"{PUBLIC_COMMAND} skills list [--project] [--json]", "summary": "List installed skills through the official skills CLI."},
            {"command": "skills add", "usage": f"{PUBLIC_COMMAND} skills add <source> [--skill <name>] [--ref <ref>] [--project]", "summary": "Install skills with provenance recording and optional pinning."},
            {"command": "skills check", "usage": f"{PUBLIC_COMMAND} skills check [--project] [--json]", "summary": "Compare installed skills with the local provenance lock file."},
            {"command": "skills update", "usage": f"{PUBLIC_COMMAND} skills update [--project] [--json]", "summary": "Refresh tracked skills from the lock file without broad unsafe updates."},
        ],
    },
    {
        "group": "maintenance",
        "items": [
            {"command": "maintenance check", "usage": f"{PUBLIC_COMMAND} maintenance check [--json]", "summary": "Check command/docs/plugin drift and write a machine-readable maintenance report."},
            {"command": "maintenance audit", "usage": f"{PUBLIC_COMMAND} maintenance audit [--json]", "summary": "Run the full maintenance pass, refresh docs, and update maintenance state."},
            {"command": "maintenance fix-docs", "usage": f"{PUBLIC_COMMAND} maintenance fix-docs [--json]", "summary": f"Regenerate the human-facing {PUBLIC_DISPLAY_NAME} docs from current machine state."},
            {"command": "maintenance render-report", "usage": f"{PUBLIC_COMMAND} maintenance render-report [--json]", "summary": "Render the maintenance Markdown page and JSON report without regenerating every doc."},
        ],
    },
]
CLOUD_READINESS = [
    {
        "name": "agent-cli-os core",
        "classification": "cloud-ready-with-setup",
        "requirements": ["Python 3.12+", "Agent CLI OS bundle files under $CODEX_HOME", "write access to workflow state"],
        "notes": "Pure Python stdlib control plane. Safe once the environment installs the home bundle.",
    },
    {
        "name": "skills wrapper layer",
        "classification": "cloud-ready-with-setup",
        "requirements": ["Node.js and npx", "skills CLI availability", "network access if installing from remotes"],
        "notes": f"{PUBLIC_DISPLAY_NAME} wraps official skills tooling rather than replacing it.",
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
        "name": "gh-codeql",
        "classification": "cloud-ready-with-setup",
        "requirements": ["GitHub CLI", "github/gh-codeql extension", "GitHub auth"],
        "notes": "Official GitHub CLI extension for managing and invoking the CodeQL CLI.",
    },
    {
        "name": "ghas-cli",
        "classification": "cloud-ready-with-setup",
        "requirements": ["Python 3.9+", "callable ghas-cli build", "GitHub token or auth context"],
        "notes": "Useful for GHAS enablement and rollout at scale, but local Windows packaging should be verified before you rely on it as the primary path.",
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
AUTOMATION_CORE_PATTERN = "automation" + "-core"
CAPABILITY_SKILL_LINE_BUDGET = 160
UTF8_BOM = b"\xef\xbb\xbf"
SKILLS_LOADER_TIMEOUT_SECONDS = 60


def _maintenance_docs_map(docs_dir: Path) -> dict[str, Path]:
    return {
        "overview": docs_dir / "overview.md",
        "command-map": docs_dir / "command-map.md",
        "inventory": docs_dir / "inventory.md",
        "skill-map": docs_dir / "skill-map.md",
        "state-schema": docs_dir / "state-schema.md",
        "capability-registry": docs_dir / "capability-registry.md",
        "cloud-readiness": docs_dir / "cloud-readiness.md",
        "maintenance": docs_dir / "maintenance.md",
    }


def _generated_binary_assets_map(docs_dir: Path) -> dict[str, Path]:
    return {
        "skill-map-pdf": docs_dir / "skill-map.pdf",
    }


def _reference_docs_map(workspace: MaintenanceWorkspace) -> dict[str, Path]:
    return {
        "state-schema": workspace.state_schema_reference_path,
        "capability-registry": workspace.capability_registry_reference_path,
        "maintenance-contract": workspace.maintenance_contract_reference_path,
        "cloud-readiness": workspace.cloud_readiness_reference_path,
    }


def _workspace_bindings(workspace: MaintenanceWorkspace) -> dict[str, Path]:
    return {
        "AGENTCTL_HOME": workspace.agentctl_home,
        "AGENTCTL_DOCS_DIR": workspace.docs_dir,
        "AGENTCTL_CAPABILITIES_DOCS_DIR": workspace.capabilities_docs_dir,
        "CAPABILITIES_PATH": workspace.capabilities_path,
        "DOCTOR_REPORT_PATH": workspace.doctor_report_path,
        "INVENTORY_PATH": workspace.inventory_path,
        "GUIDANCE_PATH": workspace.guidance_path,
        "MAINTENANCE_REPORT_PATH": workspace.maintenance_report_path,
        "MAINTENANCE_STATE_PATH": workspace.maintenance_state_path,
        "LEGACY_MAINTENANCE_STATE_PATH": workspace.legacy_maintenance_state_path,
        "STATE_SCHEMA_REFERENCE_PATH": workspace.state_schema_reference_path,
        "CAPABILITY_REGISTRY_REFERENCE_PATH": workspace.capability_registry_reference_path,
        "MAINTENANCE_CONTRACT_REFERENCE_PATH": workspace.maintenance_contract_reference_path,
        "CLOUD_READINESS_REFERENCE_PATH": workspace.cloud_readiness_reference_path,
        "CONFIG_PATH": workspace.config_path,
        "WORKFLOW_REGISTRY_PATH": workspace.workflow_registry_path,
        "SKILLS_DIR": workspace.skills_dir,
        "AGENTCTL_PLUGIN_DIR": workspace.plugin_dir,
        "AGENTCTL_PLUGIN_MANIFEST_PATH": workspace.plugin_manifest_path,
        "AGENTCTL_PLUGIN_ROUTER_SKILL_DIR": workspace.plugin_router_skill_dir,
        "LEGACY_AGENTCTL_PLUGIN_ROUTER_SKILL_DIR": workspace.legacy_plugin_router_skill_dir,
        "AGENTCTL_MAINTENANCE_SKILL_DIR": workspace.maintenance_skill_dir,
        "LEGACY_AGENTCTL_MAINTENANCE_SKILL_DIR": workspace.legacy_maintenance_skill_dir,
    }


@contextmanager
def _maintenance_workspace_context(cwd: str | Path | None = None):
    if cwd is None:
        yield None
        return

    workspace = maintenance_workspace(cwd)
    if workspace.mode == "source" and workspace.root not in SAFE_MAINTENANCE_ROOTS:
        raise RuntimeError(f"unsafe source maintenance target: {workspace.root}")

    bindings = _workspace_bindings(workspace)
    original = {name: globals()[name] for name in bindings}
    original_docs = dict(MAINTENANCE_DOCS)
    original_assets = dict(GENERATED_BINARY_ASSETS)
    original_refs = dict(REFERENCE_DOCS)
    module_bindings = (
        (config_layers_module, "CONFIG_PATH", workspace.config_path),
        (config_layers_module, "CODEX_HOME", workspace.root),
        (guidance_module, "CODEX_HOME", workspace.root),
        (guidance_module, "GUIDANCE_PATH", workspace.guidance_path),
        (inventory_module, "PLUGINS_DIR", workspace.plugins_dir),
        (inventory_module, "SKILLS_DIR", workspace.skills_dir),
        (inventory_module, "INVENTORY_PATH", workspace.inventory_path),
    )
    original_module_values = [(module, name, getattr(module, name)) for module, name, _ in module_bindings]
    try:
        globals().update(bindings)
        MAINTENANCE_DOCS.clear()
        MAINTENANCE_DOCS.update(_maintenance_docs_map(workspace.docs_dir))
        GENERATED_BINARY_ASSETS.clear()
        GENERATED_BINARY_ASSETS.update(_generated_binary_assets_map(workspace.docs_dir))
        REFERENCE_DOCS.clear()
        REFERENCE_DOCS.update(_reference_docs_map(workspace))
        for module, name, value in module_bindings:
            setattr(module, name, value)
        yield workspace
    finally:
        for module, name, value in original_module_values:
            setattr(module, name, value)
        globals().update(original)
        MAINTENANCE_DOCS.clear()
        MAINTENANCE_DOCS.update(original_docs)
        GENERATED_BINARY_ASSETS.clear()
        GENERATED_BINARY_ASSETS.update(original_assets)
        REFERENCE_DOCS.clear()
        REFERENCE_DOCS.update(original_refs)


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


def _record_binary_asset(name: str, path: Path) -> dict[str, Any]:
    return {
        "name": name,
        "path": str(path),
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else 0,
    }


def _manual_guides_map() -> dict[str, Path]:
    repo_root = AGENTCTL_HOME.parent
    return {
        "readme": repo_root / "README.md",
        "zero-touch-setup": AGENTCTL_DOCS_DIR / "zero-touch-setup.md",
        "install-on-another-computer": AGENTCTL_DOCS_DIR / "install-on-another-computer.md",
        "unattended-worker-setup": AGENTCTL_DOCS_DIR / "unattended-worker-setup.md",
        "maintainer-guide": AGENTCTL_DOCS_DIR / "maintainer-guide.md",
        "pypi-publishing": AGENTCTL_DOCS_DIR / "pypi-publishing.md",
        "skill-governance": AGENTCTL_DOCS_DIR / "skill-governance.md",
    }


def _record_manual_guide(name: str, path: Path) -> dict[str, Any]:
    content = _read_text(path)
    return {
        "name": name,
        "path": str(path),
        "exists": path.exists(),
        "size": len(content),
    }


def _manual_guides_status() -> list[dict[str, Any]]:
    return [_record_manual_guide(name, path) for name, path in _manual_guides_map().items()]


def _capability_group_keys() -> list[str]:
    return [group["key"] for group in CAPABILITY_GROUPS]


def _capability_doc_keys(report: dict[str, Any]) -> list[str]:
    return [*_capability_group_keys(), *capability_keys(report["capabilities_snapshot"])]


def _capability_docs(report: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key in _capability_doc_keys(report):
        path = AGENTCTL_CAPABILITIES_DOCS_DIR / f"{key}.md"
        items.append(_record_file(f"capability:{key}", path))
    return items


def _capability_skill_budget() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not SKILLS_DIR.exists():
        return records
    for skill_path in sorted(SKILLS_DIR.glob("*-capability/SKILL.md")):
        line_count = len(skill_path.read_text(encoding="utf-8").splitlines())
        records.append(
            {
                "name": skill_path.parent.name,
                "path": str(skill_path),
                "line_count": line_count,
                "max_lines": CAPABILITY_SKILL_LINE_BUDGET,
                "within_budget": line_count <= CAPABILITY_SKILL_LINE_BUDGET,
            }
        )
    return records


def _skill_loader_health() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    roots = (SKILLS_DIR, AGENTCTL_PLUGIN_DIR / "skills")
    for root in roots:
        if not root.exists():
            continue
        for skill_path in sorted(root.rglob("SKILL.md")):
            raw = skill_path.read_bytes()
            records.append(
                {
                    "name": skill_path.parent.name,
                    "path": str(skill_path),
                    "scope": "plugin" if AGENTCTL_PLUGIN_DIR in skill_path.parents else "local",
                    "has_utf8_bom": raw.startswith(UTF8_BOM),
                    "frontmatter_at_byte_zero": raw.startswith(b"---"),
                    "loader_compatible": raw.startswith(b"---"),
                }
            )
    return records


def _top_level_skill_names() -> list[str]:
    names: list[str] = []
    if not SKILLS_DIR.exists():
        return names
    for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        relative = path.parent.relative_to(SKILLS_DIR)
        if relative.parts and relative.parts[0].startswith("."):
            continue
        names.append(path.parent.name)
    return names


def _official_skill_loader_health() -> dict[str, Any]:
    expected_names = _top_level_skill_names()
    if not expected_names:
        return {
            "status": "ok",
            "mode": "mirror-global-list",
            "command": "npx skills ls -g --json",
            "expected_names": [],
            "actual_names": [],
            "missing_names": [],
            "extra_names": [],
            "stderr": "",
        }

    try:
        with tempfile.TemporaryDirectory(prefix=f"{PUBLIC_COMMAND}-skills-loader-") as temp_dir:
            mirror_root = Path(temp_dir)
            mirror_skills_root = mirror_root / "skills"
            mirror_skills_root.mkdir(parents=True, exist_ok=True)
            for name in expected_names:
                shutil.copytree(SKILLS_DIR / name, mirror_skills_root / name)

            executable = shutil.which("npx") or "npx"
            suffix = Path(executable).suffix.lower()
            shell = suffix in {".cmd", ".bat", ".ps1"}
            command_args = [executable, "skills", "ls", "-g", "--json"]
            command: list[str] | str = subprocess.list2cmdline(command_args) if shell else command_args
            env = os.environ.copy()
            env["CODEX_HOME"] = str(mirror_root)
            env["PYTHONUTF8"] = "1"
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=SKILLS_LOADER_TIMEOUT_SECONDS,
                check=False,
                shell=shell,
                env=env,
            )

            stdout = (completed.stdout or "").strip()
            stderr = (completed.stderr or "").strip()
            if completed.returncode != 0:
                return {
                    "status": "error",
                    "mode": "mirror-global-list",
                    "command": "npx skills ls -g --json",
                    "expected_names": expected_names,
                    "actual_names": [],
                    "missing_names": expected_names,
                    "extra_names": [],
                    "stderr": stderr or stdout,
                }
            try:
                payload = json.loads(stdout or "[]")
            except json.JSONDecodeError as exc:
                return {
                    "status": "error",
                    "mode": "mirror-global-list",
                    "command": "npx skills ls -g --json",
                    "expected_names": expected_names,
                    "actual_names": [],
                    "missing_names": expected_names,
                    "extra_names": [],
                    "stderr": f"failed to parse skills output: {exc}",
                }

            actual_names = sorted(
                item["name"]
                for item in payload
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            )
            expected_set = set(expected_names)
            actual_set = set(actual_names)
            missing_names = sorted(expected_set - actual_set)
            extra_names = sorted(actual_set - expected_set)
            return {
                "status": "ok" if not missing_names else "error",
                "mode": "mirror-global-list",
                "command": "npx skills ls -g --json",
                "expected_names": expected_names,
                "actual_names": actual_names,
                "missing_names": missing_names,
                "extra_names": extra_names,
                "stderr": stderr,
            }
    except (FileNotFoundError, PermissionError, OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "error",
            "mode": "mirror-global-list",
            "command": "npx skills ls -g --json",
            "expected_names": expected_names,
            "actual_names": [],
            "missing_names": expected_names,
            "extra_names": [],
            "stderr": str(exc),
        }


def _repo_scan_files() -> list[Path]:
    repo_root = AGENTCTL_HOME.parent
    roots = [
        repo_root / "README.md",
        repo_root / "AGENTS.md",
        repo_root / "pyproject.toml",
        repo_root / "config.toml",
        repo_root / "scripts",
        repo_root / ".github" / "workflows",
        AGENTCTL_HOME,
        AGENTCTL_DOCS_DIR,
        AGENTCTL_PLUGIN_DIR,
    ]
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
            continue
        if root.is_dir():
            files.extend(path for path in root.rglob("*") if path.is_file())
    return sorted({path.resolve() for path in files})


def _automation_core_hits() -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    maintenance_source = Path(__file__).resolve()
    maintenance_report = (AGENTCTL_DOCS_DIR / "maintenance-report.json").resolve()
    machine_artifacts = {
        AGENTCTL_HOME / "state" / "bootstrap-report.json",
        CAPABILITIES_PATH,
        DOCTOR_REPORT_PATH,
        MAINTENANCE_REPORT_PATH,
        MAINTENANCE_STATE_PATH,
    }
    excluded_paths = {MAINTENANCE_DOCS["maintenance"].resolve(), maintenance_source, maintenance_report}
    excluded_paths.update(path.resolve() for path in machine_artifacts)
    for path in _repo_scan_files():
        if path in excluded_paths:
            continue
        if path.suffix.lower() not in {".md", ".py", ".toml", ".json", ".yml", ".yaml", ".cmd", ".sh"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if AUTOMATION_CORE_PATTERN not in content:
            continue
        for index, line in enumerate(content.splitlines(), start=1):
            if AUTOMATION_CORE_PATTERN in line:
                normalized = line.strip()
                if path == CONFIG_PATH.resolve() and normalized.startswith("[projects."):
                    continue
                if any(
                    marker in normalized
                    for marker in (
                        "automation-core-drift-",
                        "Leftover automation-core coupling",
                        "stale automation-core reference",
                    )
                ):
                    continue
                hits.append({"path": str(path), "line": index, "snippet": normalized})
    return hits


def _plugin_config_status() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {"path": str(CONFIG_PATH), "present": False, "enabled": False, "entry": None}
    payload = _load_toml(CONFIG_PATH)
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
        AGENTCTL_HOME / "tests" / "test_browser_smoke.py",
        AGENTCTL_HOME / "tests" / "test_capabilities.py",
        AGENTCTL_HOME / "tests" / "test_cli_output.py",
        AGENTCTL_HOME / "tests" / "test_codex_worker.py",
        AGENTCTL_HOME / "tests" / "test_codex_runtime.py",
        AGENTCTL_HOME / "tests" / "test_guidance.py",
        AGENTCTL_HOME / "tests" / "test_inventory.py",
        AGENTCTL_HOME / "tests" / "test_install_bundle.py",
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
    ghas_cli = capabilities.get("tools", {}).get("ghas-cli", {})
    if ghas_cli.get("installed") and ghas_cli.get("status") != "ok":
        limitations.append("`ghas-cli` is installed but not callable in this environment; prefer `gh api` and `gh codeql` until the GHAS CLI route is repaired or wrapped.")
    codex = capabilities.get("tools", {}).get("codex", {})
    if codex.get("installed") and not codex.get("worker_runtime_ready"):
        limitations.append(
            "The default local Codex runtime is not callable here. "
            f"Use `{PUBLIC_COMMAND} run --worker-command ...` or configure `AGENTCTL_CODEX_WORKER_TEMPLATE` for unattended deep runs."
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
    generated_assets: list[dict[str, Any]],
    references: list[dict[str, Any]],
    manual_guides: list[dict[str, Any]],
    plugin: dict[str, Any],
    skills: list[dict[str, Any]],
    tests: list[dict[str, Any]],
    capability_skill_budget: list[dict[str, Any]],
    skill_loader_health: list[dict[str, Any]],
    official_skill_loader: dict[str, Any],
    automation_core_hits: list[dict[str, Any]],
    inventory: dict[str, Any],
    guidance: dict[str, Any],
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
                detail="Required Agent CLI OS maintenance doc is missing and should be regenerated.",
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

    for record in generated_assets:
        if not record["exists"]:
            _add_finding(
                findings,
                finding_id=f"asset-missing-{record['name']}",
                title=f"Missing generated asset: {record['name']}",
                severity="warn",
                detail="Required generated Agent CLI OS artifact is missing and should be regenerated.",
                path=record["path"],
            )

    for record in references:
        if not record["exists"]:
            _add_finding(
                findings,
                finding_id=f"reference-missing-{record['name']}",
                title=f"Missing reference: {record['name']}",
                severity="warn",
                detail="A required Agent CLI OS reference file is missing.",
                path=record["path"],
            )

    for record in manual_guides:
        if not record["exists"]:
            _add_finding(
                findings,
                finding_id=f"manual-guide-missing-{record['name']}",
                title=f"Missing guide: {record['name']}",
                severity="warn",
                detail="A required hand-maintained Agent CLI OS guide is missing.",
                path=record["path"],
            )

    if not plugin["exists"] or not plugin["manifest_exists"]:
        _add_finding(
            findings,
            finding_id="plugin-missing",
            title="Plugin packaging is incomplete",
            severity="error",
            detail="The local Agent CLI OS plugin directory or manifest is missing.",
            path=plugin["manifest_path"],
        )
    if plugin["exists"] and not plugin["router_skill_exists"]:
        _add_finding(
            findings,
            finding_id="plugin-router-missing",
            title="Plugin router skill is missing",
            severity="warn",
            detail="The local plugin exists but does not expose the router skill that makes Agent CLI OS discoverable in Codex.",
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
                detail="The Agent CLI OS test surface is incomplete.",
                path=record["path"],
            )

    if inventory.get("schema_version") != INVENTORY_SCHEMA_VERSION:
        _add_finding(
            findings,
            finding_id="inventory-schema",
            title="Inventory schema drift",
            severity="error",
            detail="The persisted inventory snapshot does not match the expected schema version.",
            path=str(INVENTORY_PATH),
        )
    if inventory.get("summary", {}).get("status") == "error":
        _add_finding(
            findings,
            finding_id="inventory-error",
            title="Inventory refresh has errors",
            severity="error",
            detail="The autodetected inventory could not be refreshed cleanly.",
            path=str(INVENTORY_PATH),
        )
    elif inventory.get("summary", {}).get("status") == "degraded":
        _add_finding(
            findings,
            finding_id="inventory-degraded",
            title="Inventory refresh is degraded",
            severity="warn",
            detail="One or more inventory sources failed or only partially refreshed.",
            path=str(INVENTORY_PATH),
        )

    max_inventory_bucket = inventory.get("summary", {}).get("max_bucket_size", 0)
    if max_inventory_bucket > inventory.get("menu_budget", {}).get("max_items", 25):
        _add_finding(
            findings,
            finding_id="inventory-bucket-overflow",
            title="Raw inventory bucket exceeds budget",
            severity="error",
            detail="At least one raw inventory bucket exceeds the configured max items budget and should be split.",
            path=str(INVENTORY_PATH),
        )

    if guidance.get("schema_version") != GUIDANCE_SCHEMA_VERSION:
        _add_finding(
            findings,
            finding_id="guidance-schema",
            title="Guidance schema drift",
            severity="error",
            detail="The persisted guidance snapshot does not match the expected schema version.",
            path=str(GUIDANCE_PATH),
        )
    if not guidance.get("summary", {}).get("within_budget", True):
        _add_finding(
            findings,
            finding_id="guidance-budget",
            title="Personal guidance exceeds budget",
            severity="warn",
            detail="Personal guidance snippets exceed the configured file or total-line budget.",
            path=str(GUIDANCE_PATH),
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

    for record in capability_skill_budget:
        if not record["within_budget"]:
            _add_finding(
                findings,
                finding_id=f"skill-budget-{record['name']}",
                title=f"Capability skill exceeds budget: {record['name']}",
                severity="warn",
                detail=(
                    f"Thin capability skills should stay navigation-first and within {record['max_lines']} lines. "
                    f"This skill is {record['line_count']} lines."
                ),
                path=record["path"],
            )

    for record in skill_loader_health:
        if not record["loader_compatible"]:
            detail = (
                "The official skills loader requires `SKILL.md` frontmatter to start with `---` at byte zero. "
                "This file is skipped by `npx skills ls` and Codex Desktop."
            )
            if record["has_utf8_bom"]:
                detail += " It currently starts with a UTF-8 BOM."
            _add_finding(
                findings,
                finding_id=f"skill-loader-{record['name']}",
                title=f"Skill loader incompatibility: {record['name']}",
                severity="error",
                detail=detail,
                path=record["path"],
            )

    if official_skill_loader.get("status") != "ok":
        missing_names = official_skill_loader.get("missing_names", [])
        if missing_names:
            _add_finding(
                findings,
                finding_id="skills-cli-missing",
                title="Official skills loader skipped local skills",
                severity="error",
                detail=(
                    "The official `skills` CLI did not list every expected top-level local skill when run against a safe mirrored skill tree. "
                    f"Missing: {', '.join(missing_names)}."
                ),
                path=str(SKILLS_DIR),
            )
        else:
            _add_finding(
                findings,
                finding_id="skills-cli-error",
                title="Official skills loader check failed",
                severity="error",
                detail=(
                    "Agent CLI OS could not complete the safe mirrored `npx skills ls -g --json` check. "
                    f"Error: {official_skill_loader.get('stderr', 'unknown error')}"
                ),
                path=str(SKILLS_DIR),
            )

    menu_budget = capabilities.get("menu_budget", {})
    visible_group_count = capabilities.get("summary", {}).get("visible_group_count", 0)
    max_group_size = capabilities.get("summary", {}).get("max_group_size", 0)
    if visible_group_count > menu_budget.get("max_top_level_groups", 8):
        _add_finding(
            findings,
            finding_id="menu-budget-groups",
            title="Top-level capability groups exceed budget",
            severity="error",
            detail="Capability menu has too many top-level groups for the intended low-context navigation model.",
            path=str(CAPABILITIES_PATH),
        )
    if max_group_size > menu_budget.get("max_group_items", 9):
        _add_finding(
            findings,
            finding_id="menu-budget-items",
            title="Capability group exceeds item budget",
            severity="error",
            detail="At least one capability group has too many items and should be split into a sub-group or narrower menu.",
            path=str(CAPABILITIES_PATH),
        )

    if any("full menu" in _read_text(Path(record["path"])).lower() for record in docs if record["name"] in {"overview", "command-map"} and Path(record["path"]).exists()):
        _add_finding(
            findings,
            finding_id="menu-copy-leakage",
            title="Generated docs still describe capabilities as the full menu",
            severity="warn",
            detail="The default menu should stay compact and distinguish curated capability navigation from raw inventory inspection.",
            path=str(MAINTENANCE_DOCS["command-map"]),
        )

    for hit in automation_core_hits:
        _add_finding(
            findings,
            finding_id=f"automation-core-drift-{Path(hit['path']).name}-{hit['line']}",
            title="Leftover automation-core coupling",
            severity="error",
            detail=f"Found a stale automation-core reference: {hit['snippet']}",
            path=hit["path"],
        )

    return findings


def build_maintenance_report() -> dict[str, Any]:
    control_plane_root = AGENTCTL_HOME.parent
    inventory = refresh_inventory_snapshot(repo=control_plane_root, output_path=INVENTORY_PATH)
    guidance = refresh_guidance_snapshot(repo=control_plane_root, output_path=GUIDANCE_PATH)
    capabilities = build_capabilities_report(inventory_snapshot=inventory)
    docs = [_record_file(name, path) for name, path in MAINTENANCE_DOCS.items()]
    docs.extend(_capability_docs({"capabilities_snapshot": capabilities}))
    generated_assets = [_record_binary_asset(name, path) for name, path in GENERATED_BINARY_ASSETS.items()]
    references = [_record_reference(name, path) for name, path in REFERENCE_DOCS.items()]
    manual_guides = _manual_guides_status()
    plugin = _plugin_status()
    skills = _skills_status()
    tests = _tests_status()
    capability_skill_budget = _capability_skill_budget()
    skill_loader_health = _skill_loader_health()
    official_skill_loader = _official_skill_loader_health()
    automation_core_hits = _automation_core_hits()
    findings = _build_findings(
        docs=docs,
        generated_assets=generated_assets,
        references=references,
        manual_guides=manual_guides,
        plugin=plugin,
        skills=skills,
        tests=tests,
        capability_skill_budget=capability_skill_budget,
        skill_loader_health=skill_loader_health,
        official_skill_loader=official_skill_loader,
        automation_core_hits=automation_core_hits,
        inventory=inventory,
        guidance=guidance,
        capabilities=capabilities,
    )

    total_checks = len(docs) + len(generated_assets) + len(references) + len(manual_guides) + len(skills) + len(tests) + len(capability_skill_budget) + len(skill_loader_health) + 10
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
            "inventory": str(INVENTORY_PATH),
            "guidance": str(GUIDANCE_PATH),
            "maintenance_report": str(MAINTENANCE_REPORT_PATH),
            "maintenance_state": str(MAINTENANCE_STATE_PATH),
            "skill_map_pdf": str(GENERATED_BINARY_ASSETS["skill-map-pdf"]),
        },
        "docs": docs,
        "generated_assets": generated_assets,
        "references": references,
        "manual_guides": manual_guides,
        "skills": skills,
        "capability_skill_budget": capability_skill_budget,
        "skill_loader_health": skill_loader_health,
        "official_skill_loader": official_skill_loader,
        "plugin": plugin,
        "tests": tests,
        "cloud_readiness": CLOUD_READINESS,
        "automation_core_hits": automation_core_hits,
        "inventory_snapshot": inventory,
        "guidance_snapshot": guidance,
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
    legacy_key = f"{state['repo_root']}::{LEGACY_MAINTENANCE_WORKFLOW_NAME}"
    if legacy_key != key:
        registry.pop(legacy_key, None)
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
        "last_batch": [f"Refreshed {PUBLIC_DISPLAY_NAME} maintenance report"],
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
            {"kind": "file", "path": str(INVENTORY_PATH)},
            {"kind": "file", "path": str(GUIDANCE_PATH)},
            {"kind": "file", "path": str(MAINTENANCE_REPORT_PATH)},
        ],
        "updated_at": report["generated_at"],
    }


def _cleanup_legacy_maintenance_surface() -> None:
    legacy_capability_doc = AGENTCTL_CAPABILITIES_DOCS_DIR / f"{LEGACY_MAINTENANCE_CAPABILITY_KEY}.md"
    for path in (LEGACY_MAINTENANCE_STATE_PATH, legacy_capability_doc):
        if path == MAINTENANCE_STATE_PATH or not path.exists():
            continue
        path.unlink()
        parent = path.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()


def _render_overview(report: dict[str, Any]) -> str:
    title = PUBLIC_DISPLAY_NAME
    lines = [
        AUTO_MARKER,
        f"# {title} Overview",
        "",
        "## Purpose",
        "",
        f"`{PUBLIC_COMMAND}` is the thin Codex-first control plane for capability discovery, routing, health checks, deep-workflow launch, and machine-readable state.",
        "",
        "## Layers",
        "",
        "1. Repo guidance in `AGENTS.md` and a small set of stable docs.",
        "2. Skills for repeated workflows such as UI, testing, refactor, docs, research, and maintenance.",
        f"3. `{PUBLIC_COMMAND}` as the runtime control plane above those skills and above authoritative vendor interfaces.",
        "4. Plugin packaging so the system can be installed and surfaced consistently.",
        "",
        "## Current Status",
        "",
        f"- Maintenance status: `{report['summary']['status']}`",
        f"- Checks passed: {report['summary']['passed_checks']} / {report['summary']['total_checks']}",
        f"- Open findings: {report['summary']['open_findings']}",
        f"- Blocked findings: {report['summary']['blocked_findings']}",
        "",
        "## First Things To Read",
        "",
        f"- `{PUBLIC_COMMAND} doctor` for a compact health check.",
        f"- `{PUBLIC_COMMAND} capabilities` for the grouped top-level capability menu.",
        f"- `{PUBLIC_COMMAND} capability <key>` for a group page or a single capability drill-down page.",
        f"- `{PUBLIC_COMMAND} skill-map` for the human one-page map of menu groups and local skills.",
        f"- `{PUBLIC_COMMAND} inventory show` when you need the raw autodetected inventory behind the curated menu.",
        f"- `{PUBLIC_COMMAND} status --all` for durable workflow state across repos.",
        f"- `{PUBLIC_COMMAND} maintenance audit` after command, packaging, config, or contract changes.",
        "",
        "## Guides And Maps",
        "",
        "- [Zero-touch setup](zero-touch-setup.md)",
        "- [Install on another computer](install-on-another-computer.md)",
        "- [Unattended worker setup](unattended-worker-setup.md)",
        "- [Maintainer guide](maintainer-guide.md)",
        "- [Control-plane governance](skill-governance.md)",
        "- [Inventory model](inventory.md)",
        "- [Skill map](skill-map.md)",
        "",
        "## Common Flows",
        "",
        f"- Capability discovery: `{PUBLIC_COMMAND} doctor` then `{PUBLIC_COMMAND} capabilities`.",
        f"- Human-facing map: `{PUBLIC_COMMAND} skill-map` or `docs/{PUBLIC_DOCS_DIRNAME}/skill-map.md`.",
        f"- Raw installed surface: `{PUBLIC_COMMAND} inventory show` then `{PUBLIC_COMMAND} inventory item <kind>:<name>`.",
        f"- External research: `{PUBLIC_COMMAND} research web|github|scout <query>`.",
        f"- Deep remediation: `{PUBLIC_COMMAND} run <workflow>` plus `.codex-workflows/<workflow>/state.json`.",
        f"- Generic long task: `$loopsmith` then `{PUBLIC_COMMAND} loop <name>` with a task brief on disk.",
        f"- Control-plane upkeep: `$agentcli-maintenance-engineer` or `{PUBLIC_COMMAND} maintenance audit`.",
        "",
        "## Compatibility",
        "",
        f"- `{PUBLIC_COMMAND}` is the canonical public command.",
        f"- `{COMPATIBILITY_COMMAND}` remains a compatibility alias for the current migration release.",
        "- The internal bundle path stays `agentctl/` for this release to avoid a risky filesystem and import break.",
        "",
        "## Verified Guarantees",
        "",
        "- Shared runner coverage exists for `complete`, `blocked`, and `stalled` terminal states.",
        f"- The CLI front door is covered end-to-end with `{PUBLIC_COMMAND} run ...` and `{PUBLIC_COMMAND} status --json` in temp repos.",
        "- Fresh installs are smoke-tested and allowed to finish `ok` when only degraded-but-documented optional capabilities remain.",
        "- The remaining environment-sensitive piece is the worker runtime itself; unattended runs still require a real callable worker route.",
        "",
        "## Key Files",
        "",
        "- Internal bundle path: `agentctl/`",
        "- Capabilities snapshot: `agentctl/state/capabilities.json`",
        "- Inventory snapshot: `agentctl/state/inventory.json`",
        "- Guidance snapshot: `agentctl/state/guidance.json`",
        f"- Maintenance report: `docs/{PUBLIC_DOCS_DIRNAME}/maintenance-report.json`",
        f"- Maintenance state: `.codex-workflows/{MAINTENANCE_WORKFLOW_NAME}/state.json`",
        "",
        f"## What {title} Does Not Own",
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
        f"# {PUBLIC_DISPLAY_NAME} Command Map",
        "",
        "This is the frozen v1 command surface that maintenance checks expect.",
        "",
        "## Quick Routing Rules",
        "",
        "- `doctor` is the shortest health-oriented entrypoint.",
        "- `capabilities` is the compact grouped menu for capability discovery.",
        "- `capability <key>` is the drill-down page for a single capability and should be preferred before choosing lower-level vendor tools.",
        "- `skill-map` is the human-facing one-pager for the grouped menu, local front-door skills, and plugin-family counts.",
        "- `inventory` is the raw autodetected surface for debugging, not the default front door.",
        "- `status` is for workflow progress, not general health.",
        "- `run` is only for deep workflows that use the shared runner/state contract.",
        "- `loop` is the generic long-task wrapper when there is no dedicated deep workflow for the job.",
        "- `run` should prefer a real worker runtime such as Codex CLI or an explicit worker command, not chat-only repetition.",
        "- `research` is for evidence creation, not implementation.",
        "- `skills` wraps official install/update tooling and provenance checks.",
        "- `maintenance` is only for the control plane itself.",
        "",
        "## Verification Notes",
        "",
        f"- `run` is tested at two levels: the shared workflow runner directly and the public `{PUBLIC_COMMAND} run` CLI path.",
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
                    f"- `{PUBLIC_COMMAND} doctor`",
                    f"- `{PUBLIC_COMMAND} capabilities` for the compact grouped menu",
                    f"- `{PUBLIC_COMMAND} skill-map` for the human one-page map of local front-door skills",
                    f"- `{PUBLIC_COMMAND} inventory show` only when you need the raw detected surface",
                    f"- `{PUBLIC_COMMAND} status --all` if you need workflow progress",
                    f"- `{PUBLIC_COMMAND} run <workflow>` when a dedicated deep workflow is the right shape",
                    f"- `{PUBLIC_COMMAND} loop <name>` when the task is large but does not cleanly map to a dedicated deep workflow",
                    "- If no worker runtime is healthy, configure `--worker-command` or `AGENTCTL_CODEX_WORKER_TEMPLATE` before treating the run as unattended",
                ]
            )
        elif group["group"] == "inventory":
            lines.extend(
                [
                    "Typical sequence:",
                    "",
                    f"- `{PUBLIC_COMMAND} inventory refresh` after local installs or config changes that affect detection",
                    f"- `{PUBLIC_COMMAND} inventory show --kind all --scope all` to inspect the raw detected surface",
                    f"- `{PUBLIC_COMMAND} inventory item tool:gh` or a similar selector when one record needs detail",
                ]
            )
        elif group["group"] == "research":
            lines.extend(
                [
                    "Typical sequence:",
                    "",
                    f"- `{PUBLIC_COMMAND} research web <query>` for current official docs or standards",
                    f"- `{PUBLIC_COMMAND} research github <query>` for field practice and repository evidence",
                    f"- `{PUBLIC_COMMAND} research scout <query>` when both are needed before implementation",
                ]
            )
        elif group["group"] == "skills":
            lines.extend(
                [
                    "Typical sequence:",
                    "",
                    f"- `{PUBLIC_COMMAND} skills list` to inspect current installs",
                    f"- `{PUBLIC_COMMAND} skills check` to inspect provenance and local-vs-external management",
                    f"- `{PUBLIC_COMMAND} skills add ...` only when you are intentionally extending the skill surface",
                ]
            )
        elif group["group"] == "maintenance":
            lines.extend(
                [
                    "Typical sequence:",
                    "",
                    f"- `{PUBLIC_COMMAND} maintenance check` for a quick control-plane inspection",
                    f"- `{PUBLIC_COMMAND} maintenance audit` after code or contract changes",
                    f"- `{PUBLIC_COMMAND} maintenance fix-docs` only when the docs need regeneration without broader change",
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
        f"# {PUBLIC_DISPLAY_NAME} State Schema",
        "",
        "## Deep Workflow State",
        "",
        "The shared deep-workflow schema lives at `agentctl/references/state-schema.md` and is the canonical contract for repo-local workflow state.",
        "",
        "## Maintenance Report Schema",
        "",
        f"The maintenance report is stored at `docs/{PUBLIC_DOCS_DIRNAME}/maintenance-report.json` and is mirrored into `.codex-workflows/{MAINTENANCE_WORKFLOW_NAME}/state.json`.",
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
        "- `inventory_snapshot`",
        "- `guidance_snapshot`",
        "- `official_skill_loader`",
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


def _render_inventory(report: dict[str, Any]) -> str:
    inventory = report["inventory_snapshot"]
    lines = [
        AUTO_MARKER,
        f"# {PUBLIC_DISPLAY_NAME} Inventory",
        "",
        "The raw autodetected inventory is stored at `agentctl/state/inventory.json`.",
        "",
        "## Purpose",
        "",
        "- Detect what is actually present on the machine and in Codex.",
        "- Keep raw installed surface separate from the curated capability menu.",
        "- Let `capabilities` stay compact while `inventory` remains the debugging and inspection layer.",
        "",
        "## Commands",
        "",
        f"- `{PUBLIC_COMMAND} inventory refresh`",
        f"- `{PUBLIC_COMMAND} inventory show --kind all --scope all`",
        f"- `{PUBLIC_COMMAND} inventory item <kind>:<name>`",
        "",
        "## Item Shape",
        "",
        "- `id`",
        "- `kind`",
        "- `name`",
        "- `source_scope`",
        "- `status`",
        "- `installed` or `configured`",
        "- `version` when available",
        "- `source_path` or `source_hint`",
        "- `front_door_candidate`",
        "- `menu_bucket`",
        "- `hidden_reason`",
        "",
        "## Menu Budget",
        "",
        f"- Raw inventory items per bucket: <= {inventory.get('menu_budget', {}).get('max_items', 25)}",
        "- Raw buckets split deterministically when the item budget is exceeded.",
        "",
        "## Current Summary",
        "",
        "```json",
        json.dumps(inventory.get("summary", {}), indent=2, sort_keys=True),
        "```",
        "",
    ]
    sources = inventory.get("sources", [])
    if sources:
        lines.extend(["## Detection Sources", ""])
        for source in sources:
            lines.append(f"- `{source['name']}`: `{source['status']}`")
            if source.get("detail"):
                lines.append(f"  - {source['detail']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_capability_registry(report: dict[str, Any]) -> str:
    capability_items = report["capabilities_snapshot"].get("capabilities", [])
    lines = [
        AUTO_MARKER,
        f"# {PUBLIC_DISPLAY_NAME} Capability Registry",
        "",
        "The machine-readable registry lives at `agentctl/state/capabilities.json` and is derived from the latest raw inventory snapshot.",
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
    for group in CAPABILITY_GROUPS:
        group_key = group["key"]
        items = grouped.get(group_key, [])
        if not items:
            continue
        lines.append(f"### {group['label']}")
        lines.append("")
        lines.append(group["summary"])
        lines.append("")
        for payload in items:
            lines.append(f"- `{payload.get('key', 'unknown')}` uses `{payload.get('front_door', 'unknown')}` and is currently `{payload.get('status', 'unknown')}`.")
            lines.append(f"  - Overlap policy: {payload.get('overlap_policy', 'Not documented.')}")
            if payload.get("advisory"):
                lines.append(f"  - Advisory: {payload['advisory']}")
            lines.append(f"  - Page: `docs/{PUBLIC_DOCS_DIRNAME}/capabilities/{payload.get('key', 'unknown')}.md`")
        lines.append("")
    lines.extend(
        [
            "## Registry Shape",
            "",
            "- `schema_version`",
            "- `generated_at`",
            "- `summary`",
            "- `inventory_path`",
            "- `inventory_summary`",
            "- `installed_skills`",
            "- `local_skills`",
            "- `plugins`",
            "- `mcp_servers`",
            "- `tools`",
            "- `capabilities`",
            "- `capability_groups`",
            "- `menu_budget`",
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
                    "visible_group_count": report["capabilities_snapshot"]["summary"].get("visible_group_count", 0),
                    "max_group_size": report["capabilities_snapshot"]["summary"].get("max_group_size", 0),
                },
                indent=2,
                sort_keys=True,
            ),
            "```",
            "",
        ]
    )
    lines.extend(
        [
            "## Menu Budgets",
            "",
            f"- Top-level groups: <= {report['capabilities_snapshot'].get('menu_budget', {}).get('max_top_level_groups', 8)}",
            f"- Items per group page: <= {report['capabilities_snapshot'].get('menu_budget', {}).get('max_group_items', 9)}",
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

    if detail.get("kind") == "group":
        lines = [
            AUTO_MARKER,
            f"# {detail['label']}",
            "",
            f"- Key: `{detail['key']}`",
            f"- Doc page: `docs/{PUBLIC_DOCS_DIRNAME}/capabilities/{detail['key']}.md`",
            "",
            detail["summary"],
            "",
            "## Items",
            "",
        ]
        for item in detail.get("items", []):
            optional_tag = " optional" if not item.get("required", True) else ""
            lines.append(f"- `{item['key']}` uses `{item['front_door']}` and is currently `{item['status']}`{optional_tag}.")
        lines.extend(
            [
                "",
                "## Menu Budget",
                "",
                f"- Top-level groups: <= {detail.get('menu_budget', {}).get('max_top_level_groups', 8)}",
                f"- Items per group page: <= {detail.get('menu_budget', {}).get('max_group_items', 9)}",
                "",
            ]
        )
        return "\n".join(lines).rstrip() + "\n"

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
        f"# {PUBLIC_DISPLAY_NAME} Cloud Readiness",
        "",
        "Cloud support is explicit, not assumed. A plugin install is not enough without a cloud environment that provides the required tools and auth.",
        "",
        "## Minimum Cloud Bundle",
        "",
        f"- Python 3.12+ for {PUBLIC_DISPLAY_NAME}",
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
        "- Install the internal `agentctl/` bundle under `$CODEX_HOME`.",
        f"- Verify `{PUBLIC_COMMAND} doctor` is healthy in the cloud environment itself.",
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
        f"# {PUBLIC_DISPLAY_NAME} Maintenance",
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
        f"- After changing {PUBLIC_DISPLAY_NAME} commands, adapters, or state contracts.",
        "- After changing plugin metadata, plugin skills, or packaging layout.",
        "- After adding or removing supported CLIs or browser routes.",
        "- Before trusting cloud-readiness assumptions for a new workflow.",
        "",
        "## Operator Runbook",
        "",
        f"1. Run `{PUBLIC_COMMAND} maintenance check` for a quick signal.",
        f"2. If command surface, docs, or packaging changed, run `{PUBLIC_COMMAND} maintenance audit`.",
        f"3. Read `maintenance.md`, `maintenance-report.json`, and `.codex-workflows/{MAINTENANCE_WORKFLOW_NAME}/state.json` together.",
        f"4. Inspect `{PUBLIC_COMMAND} inventory show` when a capability surface looks wrong or unexpectedly large.",
        "5. Remember that maintenance now includes a safe mirrored `npx skills ls -g --json` check for the current local skill tree.",
        f"6. Inspect `{PUBLIC_COMMAND} self-check` when config, guidance, or menu budgets may be part of the problem.",
        f"7. If findings are doc-only, prefer `{PUBLIC_COMMAND} maintenance fix-docs` over hand edits.",
        "8. Re-run the relevant tests and smoke checks before trusting a green maintenance state.",
        "",
        "## What Must Be Updated After Changes",
        "",
        f"- Refresh `docs/{PUBLIC_DOCS_DIRNAME}/*.md` from machine state.",
        "- Keep `agentctl/state/inventory.json` and `agentctl/state/guidance.json` healthy and within budget.",
        "- Review hand-maintained guides such as `README.md`, `zero-touch-setup.md`, `install-on-another-computer.md`, `unattended-worker-setup.md`, `maintainer-guide.md`, and `skill-governance.md` when behavior or setup expectations change.",
        "- Keep `state-schema.md`, `capability-registry.md`, and `maintenance-contract.md` aligned with code.",
        f"- Re-run tests for {PUBLIC_DISPLAY_NAME} and the shared workflow tools.",
        "- Re-run at least one CLI-level deep-workflow smoke after changing runner/state/guard behavior.",
        "- Keep `AGENTS.md` aligned with the intended front door.",
        "- If the skill surface changes, keep capability wrappers thin and update `skill-governance.md` in the same change.",
        "",
        "## Verification Expectations",
        "",
        "- `python -m unittest discover -s agentctl/tests -p \"test_*.py\"` passes.",
        "- `python -m unittest discover -s workflow-tools/tests -p \"test_*.py\"` passes.",
        f"- A temp-repo `{PUBLIC_COMMAND} run <workflow>` smoke can reach a correct terminal state with a real or explicit worker command.",
        "- Fresh bundle install smoke keeps `bootstrap-report.json` truthful and does not fail purely on documented degraded capabilities.",
        "",
        "## Clean State Expectations",
        "",
        "- `maintenance-report.json` has `status: ok`.",
        f"- `.codex-workflows/{MAINTENANCE_WORKFLOW_NAME}/state.json` has `status: complete` and `ready_allowed: true`.",
        f"- `{PUBLIC_COMMAND} doctor` stays compact and health-focused.",
        f"- `{PUBLIC_COMMAND} capabilities` stays capability-first.",
        f"- `{PUBLIC_COMMAND} status --all` surfaces durable active workflows and hides stale temp history by default.",
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
        save_text(MAINTENANCE_DOCS["inventory"], _render_inventory(report))
        write_skill_map_docs(
            report["capabilities_snapshot"],
            report["inventory_snapshot"],
            cwd=AGENTCTL_HOME.parent,
            docs_dir=AGENTCTL_DOCS_DIR,
        )
        save_text(MAINTENANCE_DOCS["state-schema"], _render_state_schema(report))
        save_text(MAINTENANCE_DOCS["capability-registry"], _render_capability_registry(report))
        save_text(MAINTENANCE_DOCS["cloud-readiness"], _render_cloud_readiness(report))
        AGENTCTL_CAPABILITIES_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        for key in _capability_doc_keys(report):
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
    _cleanup_legacy_maintenance_surface()
    return report


def maintenance_check(*, cwd: str | Path | None = None) -> dict[str, Any]:
    with _maintenance_workspace_context(cwd):
        return _persist(build_maintenance_report())


def maintenance_render_report(*, cwd: str | Path | None = None) -> dict[str, Any]:
    with _maintenance_workspace_context(cwd):
        report = build_maintenance_report()
        _write_docs(report, include_all=False, include_maintenance_page=True)
        final_report = build_maintenance_report()
        _write_docs(final_report, include_all=False, include_maintenance_page=True)
        return _persist(final_report)


def maintenance_fix_docs(*, cwd: str | Path | None = None) -> dict[str, Any]:
    with _maintenance_workspace_context(cwd):
        report = build_maintenance_report()
        _write_docs(report, include_all=True, include_maintenance_page=True)
        final_report = build_maintenance_report()
        _write_docs(final_report, include_all=True, include_maintenance_page=True)
        return _persist(final_report)


def maintenance_audit(*, cwd: str | Path | None = None) -> dict[str, Any]:
    return maintenance_fix_docs(cwd=cwd)


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
    print(f"- Inventory snapshot: {payload['artifacts']['inventory']}")
    print(f"- Guidance snapshot: {payload['artifacts']['guidance']}")
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
