from __future__ import annotations

import os
from pathlib import Path


CODEX_HOME = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).resolve()
AGENTCTL_HOME = CODEX_HOME / "agentctl"
STATE_DIR = AGENTCTL_HOME / "state"
REFERENCES_DIR = AGENTCTL_HOME / "references"
DOCS_DIR = CODEX_HOME / "docs"
AGENTCTL_DOCS_DIR = DOCS_DIR / "agentctl"
AGENTCTL_CAPABILITIES_DOCS_DIR = AGENTCTL_DOCS_DIR / "capabilities"
WORKFLOW_TOOLS_DIR = CODEX_HOME / "workflow-tools"
WORKFLOW_REGISTRY_PATH = CODEX_HOME / "workflow-state" / "registry.json"
SKILLS_DIR = CODEX_HOME / "skills"
PLUGINS_DIR = CODEX_HOME / "plugins"
CONFIG_PATH = CODEX_HOME / "config.toml"
PLAYWRIGHT_WRAPPER = AGENTCTL_HOME / "playwright_cli.py"
PLAYWRIGHT_WRAPPER_CMD = AGENTCTL_HOME / "playwright.cmd"
CAPABILITIES_PATH = STATE_DIR / "capabilities.json"
DOCTOR_REPORT_PATH = STATE_DIR / "doctor-report.json"
SKILLS_LOCK_PATH = STATE_DIR / "skills-lock.json"
MAINTENANCE_REPORT_PATH = AGENTCTL_DOCS_DIR / "maintenance-report.json"
MAINTENANCE_STATE_PATH = CODEX_HOME / ".codex-workflows" / "agentctl-maintenance" / "state.json"
STATE_SCHEMA_REFERENCE_PATH = REFERENCES_DIR / "state-schema.md"
CAPABILITY_REGISTRY_REFERENCE_PATH = REFERENCES_DIR / "capability-registry.md"
MAINTENANCE_CONTRACT_REFERENCE_PATH = REFERENCES_DIR / "maintenance-contract.md"
CLOUD_READINESS_REFERENCE_PATH = REFERENCES_DIR / "cloud-readiness.md"
AGENTCTL_PLUGIN_NAME = "agentctl"
AGENTCTL_PLUGIN_DIR = PLUGINS_DIR / AGENTCTL_PLUGIN_NAME
AGENTCTL_PLUGIN_MANIFEST_PATH = AGENTCTL_PLUGIN_DIR / ".codex-plugin" / "plugin.json"
AGENTCTL_PLUGIN_ROUTER_SKILL_DIR = AGENTCTL_PLUGIN_DIR / "skills" / "agentctl-router"
AGENTCTL_MAINTENANCE_SKILL_DIR = SKILLS_DIR / "agentctl-maintenance-engineer"
