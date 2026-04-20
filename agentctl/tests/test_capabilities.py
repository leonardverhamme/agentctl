from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.capabilities import (
    CAPABILITY_SPECS,
    _detect_ghas_cli,
    _playwright_browser_binaries,
    _python_user_script_candidates,
    build_capabilities_report,
    capability_detail,
)


class CapabilitiesTests(unittest.TestCase):
    def _inventory(self) -> dict:
        return {
            "schema_version": 1,
            "generated_at": "2026-04-19T00:00:00+00:00",
            "summary": {"status": "ok", "total_items": 0, "max_bucket_size": 2},
            "menu_budget": {"max_items": 25},
            "tool_map": {
                "python": {"installed": True, "status": "ok", "version": "3.12.0"},
                "npx": {"installed": True, "status": "ok", "version": "10.0.0"},
                "skills": {"installed": True, "status": "ok", "version": "1.5.1"},
                "codex": {"installed": True, "status": "ok", "callable": True, "worker_runtime_ready": True},
                "gh": {"installed": True, "status": "ok", "version": "gh 2.0", "skill_supported": False},
                "gh-codeql": {"installed": True, "status": "ok"},
                "ghas-cli": {"installed": True, "status": "ok", "callable": True},
                "coderabbit": {"installed": True, "status": "ok", "version": "1.0.0"},
                "plugin-eval": {"installed": True, "status": "ok", "version": "bundled 0.1.0"},
                "vercel": {"installed": True, "status": "ok"},
                "supabase": {"installed": True, "status": "ok"},
                "firebase": {"installed": False, "status": "missing", "detect_only": True},
                "gcloud": {"installed": False, "status": "missing", "detect_only": True},
                "playwright": {"installed": True, "status": "ok", "wrapper_ready": True},
            },
            "items": [
                {"kind": "skill", "name": "loopsmith", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "autonomous-deep-runs-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "skills-management-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "agentcli-maintenance-engineer", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "research-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "internet-researcher", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "github-researcher", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "web-github-scout", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "context-skill", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "ui-skill", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "ui-deep-audit", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "test-skill", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "test-deep-audit", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "docs-skill", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "docs-deep-audit", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "refactor-skill", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "refactor-deep-audit", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "refactor-orchestrator", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "cicd-skill", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "cicd-deep-audit", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "coderabbit:coderabbit-review", "source_scope": "plugin", "status": "ok", "source_path": r"C:\plugins\coderabbit\skills\coderabbit-review\SKILL.md"},
                {"kind": "skill", "name": "plugin-eval:plugin-eval", "source_scope": "plugin", "status": "ok", "source_path": r"C:\plugins\plugin-eval\skills\plugin-eval\SKILL.md"},
                {"kind": "skill", "name": "github-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "github-security-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "browser-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "supabase-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "vercel-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "stripe-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "sentry-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "ios-development-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "macos-development-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "skill", "name": "android-testing-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                {"kind": "plugin", "name": "agent-cli-os", "source_scope": "user", "status": "ok", "enabled": True},
                {"kind": "plugin", "name": "coderabbit@openai-curated", "source_scope": "user", "status": "ok", "enabled": True},
                {"kind": "plugin", "name": "plugin-eval@openai-curated", "source_scope": "user", "status": "ok", "enabled": True},
                {"kind": "plugin", "name": "github@openai-curated", "source_scope": "user", "status": "ok", "enabled": True},
                {"kind": "mcp", "name": "supabase", "source_scope": "user", "status": "configured", "configured": True},
                {"kind": "mcp", "name": "playwright", "source_scope": "user", "status": "configured", "configured": True},
            ],
        }

    def test_report_contains_expected_capabilities(self) -> None:
        report = build_capabilities_report(inventory_snapshot=self._inventory())
        capability_keys = {item["key"] for item in report["capabilities"]}
        self.assertEqual(report["schema_version"], 2)
        self.assertIn("research", capability_keys)
        self.assertIn("browser-automation", capability_keys)
        self.assertIn("supabase-data", capability_keys)
        self.assertIn("github-advanced-security", capability_keys)
        self.assertIn("autonomous-deep-runs", capability_keys)
        self.assertIn("long-task-loops", capability_keys)
        self.assertIn("code-review", capability_keys)
        self.assertIn("plugin-evaluation", capability_keys)
        self.assertEqual(report["summary"]["installed_skill_count"], 30)
        self.assertEqual(report["inventory_summary"]["status"], "ok")

    def test_optional_integrations_do_not_degrade_baseline_summary(self) -> None:
        inventory = self._inventory()
        inventory["tool_map"]["gh"] = {"installed": False, "status": "missing", "skill_supported": False}
        inventory["tool_map"]["gh-codeql"] = {"installed": False, "status": "missing"}
        inventory["tool_map"]["ghas-cli"] = {"installed": False, "status": "missing"}
        inventory["tool_map"]["playwright"] = {"installed": False, "status": "missing", "wrapper_ready": False}
        report = build_capabilities_report(inventory_snapshot=inventory)
        self.assertEqual(report["summary"]["status"], "ok")
        self.assertGreater(report["summary"]["optional_attention_count"], 0)

    def test_autonomous_deep_runs_stays_ok_when_default_codex_runtime_is_unavailable(self) -> None:
        inventory = self._inventory()
        inventory["tool_map"]["codex"] = {
            "installed": True,
            "status": "degraded",
            "callable": False,
            "worker_runtime_ready": False,
        }
        report = build_capabilities_report(inventory_snapshot=inventory)
        capability = next(item for item in report["capabilities"] if item["key"] == "autonomous-deep-runs")
        self.assertEqual(report["summary"]["status"], "ok")
        self.assertEqual(capability["status"], "ok")
        self.assertIn("AGENTCTL_CODEX_WORKER_TEMPLATE", capability["advisory"])

    def test_capability_detail_exposes_long_task_loop_front_door(self) -> None:
        report = build_capabilities_report(inventory_snapshot=self._inventory())
        detail = capability_detail(report, "long-task-loops")
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail["front_door"], "$loopsmith")
        self.assertIn("agentcli loop <name>", detail["entrypoints"])
        self.assertEqual(detail["status"], "ok")

    def test_capability_detail_exposes_supabase_cli_first_notes(self) -> None:
        report = build_capabilities_report(inventory_snapshot=self._inventory())
        detail = capability_detail(report, "supabase-data")
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail["front_door"], "$supabase-capability")
        self.assertEqual(detail["status"], "ok")
        self.assertTrue(any("CLI-first" in note for note in detail["routing_notes"]))

    def test_capability_detail_exposes_github_advanced_security_routes(self) -> None:
        inventory = self._inventory()
        inventory["tool_map"]["ghas-cli"] = {
            "installed": True,
            "status": "degraded",
            "callable": False,
            "runtime_error": "ModuleNotFoundError: No module named 'cli'",
        }
        report = build_capabilities_report(inventory_snapshot=inventory)
        detail = capability_detail(report, "github-advanced-security")
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail["front_door"], "$github-security-capability")
        self.assertIn("gh codeql", detail["entrypoints"])
        self.assertIn("gh api", detail["entrypoints"])
        self.assertTrue(any("GHAS-specific" in note for note in detail["routing_notes"]))

    def test_capability_detail_exposes_plugin_backed_review_and_evaluation_routes(self) -> None:
        report = build_capabilities_report(inventory_snapshot=self._inventory())

        code_review = capability_detail(report, "code-review")
        self.assertIsNotNone(code_review)
        assert code_review is not None
        self.assertEqual(code_review["front_door"], "$coderabbit:coderabbit-review")
        self.assertIn("coderabbit review --agent", code_review["entrypoints"])
        self.assertEqual(code_review["status"], "ok")

        plugin_eval = capability_detail(report, "plugin-evaluation")
        self.assertIsNotNone(plugin_eval)
        assert plugin_eval is not None
        self.assertEqual(plugin_eval["front_door"], "$plugin-eval:plugin-eval")
        self.assertTrue(any("Fixture skills" in note for note in plugin_eval["routing_notes"]))
        self.assertEqual(plugin_eval["status"], "ok")

    def test_plugin_items_with_configured_flag_count_as_healthy(self) -> None:
        inventory = self._inventory()
        inventory["items"] = [
            item
            for item in inventory["items"]
            if not (item["kind"] == "plugin" and item["name"] == "agent-cli-os")
        ]
        inventory["items"].append({"kind": "plugin", "name": "agent-cli-os", "source_scope": "user", "status": "ok", "configured": True})
        report = build_capabilities_report(inventory_snapshot=inventory)
        detail = capability_detail(report, "agentcli-maintenance")
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail["status"], "ok")
        self.assertTrue(any(item["kind"] == "plugin" and item["enabled"] for item in detail["backing_interfaces"]))

    def test_playwright_browser_binaries_detects_standard_and_cached_windows_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            program_files = root / "Program Files"
            local_app_data = root / "AppData" / "Local"
            chrome_path = program_files / "Google" / "Chrome" / "Application" / "chrome.exe"
            chromium_path = local_app_data / "ms-playwright" / "chromium-1208" / "chrome-win64" / "chrome.exe"
            chrome_path.parent.mkdir(parents=True, exist_ok=True)
            chromium_path.parent.mkdir(parents=True, exist_ok=True)
            chrome_path.write_text("", encoding="utf-8")
            chromium_path.write_text("", encoding="utf-8")

            with mock.patch.dict(
                "os.environ",
                {
                    "ProgramFiles": str(program_files),
                    "ProgramFiles(x86)": str(root / "Program Files (x86)"),
                    "LOCALAPPDATA": str(local_app_data),
                },
                clear=False,
            ), mock.patch("lib.capabilities.command_path", return_value=None):
                browsers = _playwright_browser_binaries()

        self.assertEqual(browsers["chrome"], str(chrome_path))
        self.assertEqual(browsers["chromium"], str(chromium_path))

    def test_python_user_script_candidates_includes_windows_store_python_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            userbase = root / "local-packages"
            usersite = userbase / "Python312" / "site-packages"

            with mock.patch("os.name", "nt"), mock.patch("site.getuserbase", return_value=str(userbase)), mock.patch(
                "site.getusersitepackages", return_value=str(usersite)
            ):
                candidates = _python_user_script_candidates("ghas-cli")

        candidate_paths = set(candidates)
        self.assertTrue(any(path.endswith(r"Scripts\ghas-cli.exe") for path in candidate_paths))
        self.assertTrue(any(path.endswith(r"Python312\Scripts\ghas-cli.exe") for path in candidate_paths))

    @mock.patch("lib.capabilities.run_command")
    @mock.patch("lib.capabilities.command_path")
    def test_detect_ghas_cli_uses_help_long_flag(self, command_path: mock.Mock, run_command: mock.Mock) -> None:
        command_path.return_value = r"C:\Users\leona\AppData\Roaming\npm\ghas-cli.CMD"
        run_command.return_value = {
            "ok": True,
            "returncode": 0,
            "stdout": "Usage: cli.py [OPTIONS] COMMAND [ARGS]...",
            "stderr": "",
        }

        record = _detect_ghas_cli()

        run_command.assert_called_once_with([r"C:\Users\leona\AppData\Roaming\npm\ghas-cli.CMD", "--help"], timeout=20)
        self.assertEqual(record["status"], "ok")
        self.assertTrue(record["callable"])
        self.assertEqual(record["version"], "Usage: cli.py [OPTIONS] COMMAND [ARGS]...")

    def test_every_capability_has_a_skill_front_door(self) -> None:
        for spec in CAPABILITY_SPECS:
            self.assertTrue(spec.get("skills"), f"{spec['key']} should expose at least one skill")
            self.assertIn("$", spec["front_door"], f"{spec['key']} should route through a skill front door")


if __name__ == "__main__":
    unittest.main()
