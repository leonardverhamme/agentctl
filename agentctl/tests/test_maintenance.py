from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import maintenance


class MaintenanceTests(unittest.TestCase):
    def _patch_paths(self, root: Path) -> list[mock._patch]:
        agentctl_home = root / "agentctl"
        docs_dir = root / "docs" / "agentctl"
        capability_docs_dir = docs_dir / "capabilities"
        refs_dir = agentctl_home / "references"
        plugin_dir = root / "plugins" / "agentctl"
        patches = [
            mock.patch.object(maintenance, "AGENTCTL_HOME", agentctl_home),
            mock.patch.object(maintenance, "AGENTCTL_DOCS_DIR", docs_dir),
            mock.patch.object(maintenance, "AGENTCTL_CAPABILITIES_DOCS_DIR", capability_docs_dir),
            mock.patch.object(maintenance, "CAPABILITIES_PATH", agentctl_home / "state" / "capabilities.json"),
            mock.patch.object(maintenance, "DOCTOR_REPORT_PATH", agentctl_home / "state" / "doctor-report.json"),
            mock.patch.object(maintenance, "MAINTENANCE_REPORT_PATH", docs_dir / "maintenance-report.json"),
            mock.patch.object(maintenance, "MAINTENANCE_STATE_PATH", root / ".codex-workflows" / "agentctl-maintenance" / "state.json"),
            mock.patch.object(maintenance, "STATE_SCHEMA_REFERENCE_PATH", refs_dir / "state-schema.md"),
            mock.patch.object(maintenance, "CAPABILITY_REGISTRY_REFERENCE_PATH", refs_dir / "capability-registry.md"),
            mock.patch.object(maintenance, "MAINTENANCE_CONTRACT_REFERENCE_PATH", refs_dir / "maintenance-contract.md"),
            mock.patch.object(maintenance, "CLOUD_READINESS_REFERENCE_PATH", refs_dir / "cloud-readiness.md"),
            mock.patch.object(maintenance, "CONFIG_PATH", root / "config.toml"),
            mock.patch.object(maintenance, "WORKFLOW_REGISTRY_PATH", root / "workflow-state" / "registry.json"),
            mock.patch.object(maintenance, "AGENTCTL_PLUGIN_DIR", plugin_dir),
            mock.patch.object(maintenance, "AGENTCTL_PLUGIN_MANIFEST_PATH", plugin_dir / ".codex-plugin" / "plugin.json"),
            mock.patch.object(maintenance, "AGENTCTL_PLUGIN_ROUTER_SKILL_DIR", plugin_dir / "skills" / "agentctl-router"),
            mock.patch.object(maintenance, "AGENTCTL_MAINTENANCE_SKILL_DIR", root / "skills" / "agentctl-maintenance-engineer"),
            mock.patch.dict(
                maintenance.MAINTENANCE_DOCS,
                {
                    "overview": docs_dir / "overview.md",
                    "command-map": docs_dir / "command-map.md",
                    "state-schema": docs_dir / "state-schema.md",
                    "capability-registry": docs_dir / "capability-registry.md",
                    "cloud-readiness": docs_dir / "cloud-readiness.md",
                    "maintenance": docs_dir / "maintenance.md",
                },
                clear=True,
            ),
            mock.patch.dict(
                maintenance.REFERENCE_DOCS,
                {
                    "state-schema": refs_dir / "state-schema.md",
                    "capability-registry": refs_dir / "capability-registry.md",
                    "maintenance-contract": refs_dir / "maintenance-contract.md",
                    "cloud-readiness": refs_dir / "cloud-readiness.md",
                },
                clear=True,
            ),
        ]
        return patches

    def _capabilities_report(self, *, status: str = "ok") -> dict:
        return {
            "summary": {"status": status},
            "tools": {
                "gh": {"installed": True, "skill_supported": True},
                "codex": {"installed": True, "worker_runtime_ready": False},
                "playwright": {"status": "ok"},
            },
            "capabilities": [
                {"key": "browser-automation", "status": "ok", "front_door": "$playwright", "overlap_policy": "test"},
                {"key": "research", "status": "ok", "front_door": "agentctl research", "overlap_policy": "test"},
            ],
            "overlap_analysis": [],
            "detect_only_tools": [],
        }

    def test_build_report_surfaces_missing_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            refs_dir = root / "agentctl" / "references"
            refs_dir.mkdir(parents=True, exist_ok=True)
            for name in ("state-schema.md", "capability-registry.md", "maintenance-contract.md", "cloud-readiness.md"):
                (refs_dir / name).write_text("reference\n", encoding="utf-8")
            skill_dir = root / "skills" / "agentctl-maintenance-engineer"
            skill_dir.mkdir(parents=True, exist_ok=True)

            patches = self._patch_paths(root)
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(maintenance, "build_capabilities_report", return_value=self._capabilities_report()))
                for patcher in patches:
                    stack.enter_context(patcher)
                report = maintenance.build_maintenance_report()

            finding_ids = {finding["id"] for finding in report["findings"]}
            self.assertIn("doc-missing-overview", finding_ids)
            self.assertIn("plugin-missing", finding_ids)
            self.assertEqual(report["summary"]["status"], "error")

    def test_fix_docs_writes_docs_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            refs_dir = root / "agentctl" / "references"
            refs_dir.mkdir(parents=True, exist_ok=True)
            for name in ("state-schema.md", "capability-registry.md", "maintenance-contract.md", "cloud-readiness.md"):
                (refs_dir / name).write_text("reference\n", encoding="utf-8")

            skill_dir = root / "skills" / "agentctl-maintenance-engineer"
            skill_dir.mkdir(parents=True, exist_ok=True)
            plugin_manifest = root / "plugins" / "agentctl" / ".codex-plugin" / "plugin.json"
            plugin_manifest.parent.mkdir(parents=True, exist_ok=True)
            plugin_manifest.write_text(json.dumps({"name": "agentctl"}), encoding="utf-8")
            tests_dir = root / "agentctl" / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            for name in (
                "test_browser_smoke.py",
                "test_capabilities.py",
                "test_cli_output.py",
                "test_codex_runtime.py",
                "test_install_bundle.py",
                "test_research.py",
                "test_skills_ops.py",
                "test_workflows.py",
                "test_maintenance.py",
            ):
                (tests_dir / name).write_text("pass\n", encoding="utf-8")
            router_skill = root / "plugins" / "agentctl" / "skills" / "agentctl-router" / "SKILL.md"
            router_skill.parent.mkdir(parents=True, exist_ok=True)
            router_skill.write_text("---\nname: agentctl-router\ndescription: test\n---\n", encoding="utf-8")
            (root / "config.toml").write_text('[plugins."agentctl"]\nenabled = true\n', encoding="utf-8")
            docs_dir = root / "docs" / "agentctl"
            docs_dir.mkdir(parents=True, exist_ok=True)
            (root / "README.md").write_text("# agentctl\n", encoding="utf-8")
            for name in (
                "zero-touch-setup.md",
                "install-on-another-computer.md",
                "unattended-worker-setup.md",
                "maintainer-guide.md",
                "skill-governance.md",
            ):
                (docs_dir / name).write_text(f"# {name}\n", encoding="utf-8")

            patches = self._patch_paths(root)
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(maintenance, "build_capabilities_report", return_value=self._capabilities_report()))
                for patcher in patches:
                    stack.enter_context(patcher)
                report = maintenance.maintenance_fix_docs()

                overview = (root / "docs" / "agentctl" / "overview.md").read_text(encoding="utf-8")
                capability_page = (root / "docs" / "agentctl" / "capabilities" / "research.md").read_text(encoding="utf-8")
                state = json.loads((root / ".codex-workflows" / "agentctl-maintenance" / "state.json").read_text(encoding="utf-8"))

            self.assertIn("agentctl:auto-generated", overview)
            self.assertIn("# Research", capability_page)
            self.assertEqual(report["summary"]["status"], "ok")
            self.assertTrue(state["ready_allowed"])
            self.assertEqual(state["status"], "complete")
            self.assertTrue(any("AGENTCTL_CODEX_WORKER_TEMPLATE" in item for item in report["known_limitations"]))


if __name__ == "__main__":
    unittest.main()
