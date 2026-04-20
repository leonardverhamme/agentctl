from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import maintenance


class MaintenanceTests(unittest.TestCase):
    def _workspace(self, root: Path, *, mode: str = "source") -> SimpleNamespace:
        agentctl_home = root / "agentctl"
        docs_dir = root / "docs" / "agent-cli-os"
        plugin_dir = root / "plugins" / "agent-cli-os"
        return SimpleNamespace(
            mode=mode,
            root=root,
            agentctl_home=agentctl_home,
            docs_dir=docs_dir,
            capabilities_docs_dir=docs_dir / "capabilities",
            state_dir=agentctl_home / "state",
            references_dir=agentctl_home / "references",
            workflow_registry_path=root / "workflow-state" / "registry.json",
            skills_dir=root / "skills",
            plugins_dir=root / "plugins",
            config_path=root / "config.toml",
            capabilities_path=agentctl_home / "state" / "capabilities.json",
            doctor_report_path=agentctl_home / "state" / "doctor-report.json",
            inventory_path=agentctl_home / "state" / "inventory.json",
            guidance_path=agentctl_home / "state" / "guidance.json",
            maintenance_report_path=docs_dir / "maintenance-report.json",
            maintenance_state_path=root / ".codex-workflows" / "agentcli-maintenance" / "state.json",
            legacy_maintenance_state_path=root / ".codex-workflows" / "agentctl-maintenance" / "state.json",
            state_schema_reference_path=agentctl_home / "references" / "state-schema.md",
            capability_registry_reference_path=agentctl_home / "references" / "capability-registry.md",
            maintenance_contract_reference_path=agentctl_home / "references" / "maintenance-contract.md",
            cloud_readiness_reference_path=agentctl_home / "references" / "cloud-readiness.md",
            plugin_dir=plugin_dir,
            plugin_manifest_path=plugin_dir / ".codex-plugin" / "plugin.json",
            plugin_router_skill_dir=plugin_dir / "skills" / "agentcli-router",
            legacy_plugin_router_skill_dir=plugin_dir / "skills" / "agentctl-router",
            maintenance_skill_dir=root / "skills" / "agentcli-maintenance-engineer",
            legacy_maintenance_skill_dir=root / "skills" / "agentctl-maintenance-engineer",
        )

    def _patch_paths(self, root: Path) -> list[mock._patch]:
        agentctl_home = root / "agentctl"
        docs_dir = root / "docs" / "agent-cli-os"
        capability_docs_dir = docs_dir / "capabilities"
        refs_dir = agentctl_home / "references"
        plugin_dir = root / "plugins" / "agent-cli-os"
        patches = [
            mock.patch.object(maintenance, "AGENTCTL_HOME", agentctl_home),
            mock.patch.object(maintenance, "AGENTCTL_DOCS_DIR", docs_dir),
            mock.patch.object(maintenance, "AGENTCTL_CAPABILITIES_DOCS_DIR", capability_docs_dir),
            mock.patch.object(maintenance, "CAPABILITIES_PATH", agentctl_home / "state" / "capabilities.json"),
            mock.patch.object(maintenance, "DOCTOR_REPORT_PATH", agentctl_home / "state" / "doctor-report.json"),
            mock.patch.object(maintenance, "INVENTORY_PATH", agentctl_home / "state" / "inventory.json"),
            mock.patch.object(maintenance, "GUIDANCE_PATH", agentctl_home / "state" / "guidance.json"),
            mock.patch.object(maintenance, "MAINTENANCE_REPORT_PATH", docs_dir / "maintenance-report.json"),
            mock.patch.object(maintenance, "MAINTENANCE_STATE_PATH", root / ".codex-workflows" / "agentcli-maintenance" / "state.json"),
            mock.patch.object(maintenance, "LEGACY_MAINTENANCE_STATE_PATH", root / ".codex-workflows" / "agentctl-maintenance" / "state.json"),
            mock.patch.object(maintenance, "STATE_SCHEMA_REFERENCE_PATH", refs_dir / "state-schema.md"),
            mock.patch.object(maintenance, "CAPABILITY_REGISTRY_REFERENCE_PATH", refs_dir / "capability-registry.md"),
            mock.patch.object(maintenance, "MAINTENANCE_CONTRACT_REFERENCE_PATH", refs_dir / "maintenance-contract.md"),
            mock.patch.object(maintenance, "CLOUD_READINESS_REFERENCE_PATH", refs_dir / "cloud-readiness.md"),
            mock.patch.object(maintenance, "CONFIG_PATH", root / "config.toml"),
            mock.patch.object(maintenance, "WORKFLOW_REGISTRY_PATH", root / "workflow-state" / "registry.json"),
            mock.patch.object(maintenance, "SKILLS_DIR", root / "skills"),
            mock.patch.object(maintenance, "AGENTCTL_PLUGIN_DIR", plugin_dir),
            mock.patch.object(maintenance, "AGENTCTL_PLUGIN_MANIFEST_PATH", plugin_dir / ".codex-plugin" / "plugin.json"),
            mock.patch.object(maintenance, "AGENTCTL_PLUGIN_ROUTER_SKILL_DIR", plugin_dir / "skills" / "agentcli-router"),
            mock.patch.object(maintenance, "LEGACY_AGENTCTL_PLUGIN_ROUTER_SKILL_DIR", plugin_dir / "skills" / "agentctl-router"),
            mock.patch.object(maintenance, "AGENTCTL_MAINTENANCE_SKILL_DIR", root / "skills" / "agentcli-maintenance-engineer"),
            mock.patch.object(maintenance, "LEGACY_AGENTCTL_MAINTENANCE_SKILL_DIR", root / "skills" / "agentctl-maintenance-engineer"),
            mock.patch.dict(
                maintenance.MAINTENANCE_DOCS,
                {
                    "overview": docs_dir / "overview.md",
                    "command-map": docs_dir / "command-map.md",
                    "inventory": docs_dir / "inventory.md",
                    "skill-map": docs_dir / "skill-map.md",
                    "state-schema": docs_dir / "state-schema.md",
                    "capability-registry": docs_dir / "capability-registry.md",
                    "cloud-readiness": docs_dir / "cloud-readiness.md",
                    "maintenance": docs_dir / "maintenance.md",
                },
                clear=True,
            ),
            mock.patch.dict(
                maintenance.GENERATED_BINARY_ASSETS,
                {
                    "skill-map-pdf": docs_dir / "skill-map.pdf",
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
            "inventory_summary": {"status": "ok"},
            "capabilities": [
                {"key": "browser-automation", "status": "ok", "front_door": "$playwright", "overlap_policy": "test", "group": "browser-design"},
                {"key": "research", "status": "ok", "front_door": "agentcli research", "overlap_policy": "test", "group": "research"},
            ],
            "capability_groups": [
                {"key": "research", "label": "Research", "count": 1},
                {"key": "browser-design", "label": "Browser & Design", "count": 1},
            ],
            "menu_budget": {"max_top_level_groups": 8, "max_group_items": 25},
            "overlap_analysis": [],
            "detect_only_tools": [],
        }

    def _inventory_report(self) -> dict:
        return {
            "schema_version": 1,
            "summary": {"status": "ok", "max_bucket_size": 2},
            "menu_budget": {"max_items": 25},
            "items": [],
            "menu_buckets": [],
            "tool_map": {},
        }

    def _guidance_report(self) -> dict:
        return {
            "schema_version": 1,
            "summary": {"status": "ok", "within_budget": True, "file_count": 0, "total_lines": 0},
            "items": [],
        }

    def _official_skill_loader_report(self, *, missing_names: list[str] | None = None, status: str | None = None) -> dict:
        names = ["agentcli-maintenance-engineer", "ui-skill"]
        missing = sorted(missing_names or [])
        actual = [name for name in names if name not in missing]
        return {
            "status": status or ("error" if missing else "ok"),
            "mode": "mirror-global-list",
            "command": "npx skills ls -g --json",
            "expected_names": names,
            "actual_names": actual,
            "missing_names": missing,
            "extra_names": [],
            "stderr": "" if not status or status == "ok" else "skills loader failed",
        }

    def test_build_report_surfaces_missing_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            refs_dir = root / "agentctl" / "references"
            refs_dir.mkdir(parents=True, exist_ok=True)
            for name in ("state-schema.md", "capability-registry.md", "maintenance-contract.md", "cloud-readiness.md"):
                (refs_dir / name).write_text("reference\n", encoding="utf-8")
            skill_dir = root / "skills" / "agentcli-maintenance-engineer"
            skill_dir.mkdir(parents=True, exist_ok=True)
            broken_skill = root / "skills" / "ui-skill" / "SKILL.md"
            broken_skill.parent.mkdir(parents=True, exist_ok=True)
            broken_skill.write_bytes(b"\xef\xbb\xbf---\nname: ui-skill\ndescription: test\n---\n")

            patches = self._patch_paths(root)
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(maintenance, "build_capabilities_report", return_value=self._capabilities_report()))
                stack.enter_context(mock.patch.object(maintenance, "refresh_inventory_snapshot", return_value=self._inventory_report()))
                stack.enter_context(mock.patch.object(maintenance, "refresh_guidance_snapshot", return_value=self._guidance_report()))
                stack.enter_context(mock.patch.object(maintenance, "_official_skill_loader_health", return_value=self._official_skill_loader_report()))
                for patcher in patches:
                    stack.enter_context(patcher)
                report = maintenance.build_maintenance_report()

            finding_ids = {finding["id"] for finding in report["findings"]}
            self.assertIn("doc-missing-overview", finding_ids)
            self.assertIn("plugin-missing", finding_ids)
            self.assertIn("skill-loader-ui-skill", finding_ids)
            self.assertEqual(report["summary"]["status"], "error")

    def test_fix_docs_writes_docs_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            refs_dir = root / "agentctl" / "references"
            refs_dir.mkdir(parents=True, exist_ok=True)
            for name in ("state-schema.md", "capability-registry.md", "maintenance-contract.md", "cloud-readiness.md"):
                (refs_dir / name).write_text("reference\n", encoding="utf-8")

            skill_dir = root / "skills" / "agentcli-maintenance-engineer"
            skill_dir.mkdir(parents=True, exist_ok=True)
            plugin_manifest = root / "plugins" / "agent-cli-os" / ".codex-plugin" / "plugin.json"
            plugin_manifest.parent.mkdir(parents=True, exist_ok=True)
            plugin_manifest.write_text(json.dumps({"name": "agent-cli-os"}), encoding="utf-8")
            tests_dir = root / "agentctl" / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            for name in (
                "test_guidance.py",
                "test_inventory.py",
                "test_browser_smoke.py",
                "test_capabilities.py",
                "test_cli_output.py",
                "test_codex_worker.py",
                "test_codex_runtime.py",
                "test_install_bundle.py",
                "test_research.py",
                "test_skills_ops.py",
                "test_workflows.py",
                "test_maintenance.py",
            ):
                (tests_dir / name).write_text("pass\n", encoding="utf-8")
            router_skill = root / "plugins" / "agent-cli-os" / "skills" / "agentcli-router" / "SKILL.md"
            router_skill.parent.mkdir(parents=True, exist_ok=True)
            router_skill.write_text("---\nname: agentcli-router\ndescription: test\n---\n", encoding="utf-8")
            (root / "config.toml").write_text('[plugins."agent-cli-os"]\nenabled = true\n', encoding="utf-8")
            docs_dir = root / "docs" / "agent-cli-os"
            docs_dir.mkdir(parents=True, exist_ok=True)
            (root / "README.md").write_text("# Agent CLI OS\n", encoding="utf-8")
            for name in (
                "zero-touch-setup.md",
                "install-on-another-computer.md",
                "unattended-worker-setup.md",
                "maintainer-guide.md",
                "pypi-publishing.md",
                "skill-governance.md",
            ):
                (docs_dir / name).write_text(f"# {name}\n", encoding="utf-8")

            patches = self._patch_paths(root)
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(maintenance, "build_capabilities_report", return_value=self._capabilities_report()))
                stack.enter_context(mock.patch.object(maintenance, "refresh_inventory_snapshot", return_value=self._inventory_report()))
                stack.enter_context(mock.patch.object(maintenance, "refresh_guidance_snapshot", return_value=self._guidance_report()))
                stack.enter_context(mock.patch.object(maintenance, "_official_skill_loader_health", return_value=self._official_skill_loader_report()))
                for patcher in patches:
                    stack.enter_context(patcher)
                report = maintenance.maintenance_fix_docs()

                overview = (root / "docs" / "agent-cli-os" / "overview.md").read_text(encoding="utf-8")
                capability_page = (root / "docs" / "agent-cli-os" / "capabilities" / "research.md").read_text(encoding="utf-8")
                inventory_page = (root / "docs" / "agent-cli-os" / "inventory.md").read_text(encoding="utf-8")
                skill_map_page = (root / "docs" / "agent-cli-os" / "skill-map.md").read_text(encoding="utf-8")
                state = json.loads((root / ".codex-workflows" / "agentcli-maintenance" / "state.json").read_text(encoding="utf-8"))

            self.assertIn("agent-cli-os:auto-generated", overview)
            self.assertIn("# Research", capability_page)
            self.assertIn("# Agent CLI OS Inventory", inventory_page)
            self.assertIn("# Agent CLI OS Skill Map", skill_map_page)
            self.assertTrue((root / "docs" / "agent-cli-os" / "skill-map.pdf").exists())
            self.assertEqual(report["summary"]["status"], "ok")
            self.assertTrue(state["ready_allowed"])
            self.assertEqual(state["status"], "complete")
            self.assertTrue(any("AGENTCTL_CODEX_WORKER_TEMPLATE" in item for item in report["known_limitations"]))

    def test_fix_docs_can_target_source_workspace_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = self._workspace(root)
            refs_dir = workspace.references_dir
            refs_dir.mkdir(parents=True, exist_ok=True)
            for name in ("state-schema.md", "capability-registry.md", "maintenance-contract.md", "cloud-readiness.md"):
                (refs_dir / name).write_text("reference\n", encoding="utf-8")

            workspace.maintenance_skill_dir.mkdir(parents=True, exist_ok=True)
            workspace.plugin_manifest_path.parent.mkdir(parents=True, exist_ok=True)
            workspace.plugin_manifest_path.write_text(json.dumps({"name": "agent-cli-os"}), encoding="utf-8")
            tests_dir = workspace.agentctl_home / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            for name in (
                "test_guidance.py",
                "test_inventory.py",
                "test_browser_smoke.py",
                "test_capabilities.py",
                "test_cli_output.py",
                "test_codex_worker.py",
                "test_codex_runtime.py",
                "test_install_bundle.py",
                "test_research.py",
                "test_skills_ops.py",
                "test_workflows.py",
                "test_maintenance.py",
            ):
                (tests_dir / name).write_text("pass\n", encoding="utf-8")
            router_skill = workspace.plugin_router_skill_dir / "SKILL.md"
            router_skill.parent.mkdir(parents=True, exist_ok=True)
            router_skill.write_text("---\nname: agentcli-router\ndescription: test\n---\n", encoding="utf-8")
            workspace.docs_dir.mkdir(parents=True, exist_ok=True)
            (root / "README.md").write_text("# Agent CLI OS\n", encoding="utf-8")
            for name in (
                "zero-touch-setup.md",
                "install-on-another-computer.md",
                "unattended-worker-setup.md",
                "maintainer-guide.md",
                "pypi-publishing.md",
                "skill-governance.md",
            ):
                (workspace.docs_dir / name).write_text(f"# {name}\n", encoding="utf-8")
            workspace.config_path.write_text('[plugins."agent-cli-os"]\nenabled = true\n', encoding="utf-8")

            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(maintenance, "build_capabilities_report", return_value=self._capabilities_report()))
                stack.enter_context(mock.patch.object(maintenance, "refresh_inventory_snapshot", return_value=self._inventory_report()))
                stack.enter_context(mock.patch.object(maintenance, "refresh_guidance_snapshot", return_value=self._guidance_report()))
                stack.enter_context(mock.patch.object(maintenance, "_official_skill_loader_health", return_value=self._official_skill_loader_report()))
                stack.enter_context(mock.patch.object(maintenance, "maintenance_workspace", return_value=workspace))
                stack.enter_context(mock.patch.object(maintenance, "SAFE_MAINTENANCE_ROOTS", (root,)))
                report = maintenance.maintenance_fix_docs(cwd=root)

            self.assertEqual(report["artifacts"]["maintenance_report"], str(workspace.maintenance_report_path))
            self.assertTrue(workspace.maintenance_report_path.exists())
            self.assertTrue((workspace.docs_dir / "overview.md").exists())
            self.assertTrue((workspace.docs_dir / "skill-map.md").exists())
            self.assertTrue((workspace.docs_dir / "skill-map.pdf").exists())
            self.assertTrue((workspace.capabilities_docs_dir / "research.md").exists())

    def test_build_findings_surfaces_official_loader_mismatch(self) -> None:
        findings = maintenance._build_findings(
            docs=[],
            generated_assets=[],
            references=[],
            manual_guides=[],
            plugin={
                "exists": True,
                "manifest_exists": True,
                "router_skill_exists": True,
                "manifest_name": "agent-cli-os",
                "manifest_path": "plugin.json",
                "router_skill_path": "router/SKILL.md",
                "config": {"enabled": True, "path": "config.toml"},
            },
            skills=[{"name": "agentcli-maintenance-engineer", "exists": True, "path": "skills/agentcli-maintenance-engineer"}],
            tests=[],
            capability_skill_budget=[],
            skill_loader_health=[],
            official_skill_loader=self._official_skill_loader_report(missing_names=["ui-skill"]),
            automation_core_hits=[],
            inventory=self._inventory_report(),
            guidance=self._guidance_report(),
            capabilities=self._capabilities_report(),
        )

        finding_ids = {finding["id"] for finding in findings}
        self.assertIn("skills-cli-missing", finding_ids)


if __name__ == "__main__":
    unittest.main()
