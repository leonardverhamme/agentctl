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
    @staticmethod
    def _default_tool_record(*args, **kwargs) -> dict:
        name = kwargs.get("name")
        if name is None and args:
            name = args[0]
        base = {"installed": True, "status": "ok", "version": "1.0.0"}
        if name == "gh-codeql":
            return {**base, "name": "gh-codeql", "extension": "github/gh-codeql"}
        if name == "ghas-cli":
            return {**base, "name": "ghas-cli", "callable": True, "path": r"C:\tools\ghas-cli.exe"}
        return base

    @mock.patch("lib.capabilities._local_skill_names")
    @mock.patch("lib.capabilities._mcp_servers_map")
    @mock.patch("lib.capabilities._enabled_plugins_map")
    @mock.patch("lib.capabilities._config_payload")
    @mock.patch("lib.capabilities._installed_skills")
    @mock.patch("lib.capabilities.detect_codex_runtime")
    @mock.patch("lib.capabilities._detect_playwright")
    @mock.patch("lib.capabilities._detect_ghas_cli")
    @mock.patch("lib.capabilities._detect_gh_codeql")
    @mock.patch("lib.capabilities._detect_gh")
    @mock.patch("lib.capabilities._detect_skills_cli")
    @mock.patch("lib.capabilities._tool_record")
    def test_report_contains_expected_capabilities(
        self,
        tool_record: mock.Mock,
        detect_skills: mock.Mock,
        detect_gh: mock.Mock,
        detect_gh_codeql: mock.Mock,
        detect_ghas_cli: mock.Mock,
        detect_playwright: mock.Mock,
        detect_codex: mock.Mock,
        installed_skills: mock.Mock,
        config_payload: mock.Mock,
        enabled_plugins: mock.Mock,
        mcp_servers: mock.Mock,
        local_skill_names: mock.Mock,
    ) -> None:
        tool_record.side_effect = self._default_tool_record
        detect_skills.return_value = {"installed": True, "status": "ok", "version": "1.5.1"}
        detect_gh.return_value = {"installed": True, "status": "ok", "version": "gh 1.0", "skill_supported": False}
        detect_gh_codeql.return_value = self._default_tool_record("gh-codeql")
        detect_ghas_cli.return_value = self._default_tool_record("ghas-cli")
        detect_playwright.return_value = {"installed": True, "status": "degraded", "wrapper_ready": False}
        detect_codex.return_value = {"installed": True, "status": "ok", "callable": True, "worker_runtime_ready": True}
        installed_skills.return_value = {"status": "ok", "items": [{"name": "ui-skill"}]}
        config_payload.return_value = {}
        enabled_plugins.return_value = {
            "github@openai-curated": {"name": "github@openai-curated", "enabled": True, "status": "ok"},
            "loopsmith": {"name": "loopsmith", "enabled": True, "status": "ok"},
        }
        mcp_servers.return_value = {
            "playwright": {"name": "playwright", "status": "configured", "configured": True, "transport": "mcp"},
            "supabase": {"name": "supabase", "status": "configured", "configured": True, "transport": "mcp"},
        }
        local_skill_names.return_value = {
            "ui-skill",
            "ui-deep-audit",
            "test-skill",
            "test-deep-audit",
            "internet-researcher",
            "github-researcher",
            "web-github-scout",
            "research-capability",
            "skills-management-capability",
            "autonomous-deep-runs-capability",
            "agentctl-maintenance-engineer",
            "ios-development-capability",
            "macos-development-capability",
            "android-testing-capability",
        }

        report = build_capabilities_report()
        capability_keys = {item["key"] for item in report["capabilities"]}
        self.assertEqual(report["schema_version"], 2)
        self.assertIn("research", capability_keys)
        self.assertIn("browser-automation", capability_keys)
        self.assertIn("supabase-data", capability_keys)
        self.assertIn("github-advanced-security", capability_keys)
        self.assertIn("autonomous-deep-runs", capability_keys)
        self.assertEqual(report["summary"]["installed_skill_count"], 1)

    @mock.patch("lib.capabilities._local_skill_names")
    @mock.patch("lib.capabilities._mcp_servers_map")
    @mock.patch("lib.capabilities._enabled_plugins_map")
    @mock.patch("lib.capabilities._config_payload")
    @mock.patch("lib.capabilities._installed_skills")
    @mock.patch("lib.capabilities.detect_codex_runtime")
    @mock.patch("lib.capabilities._detect_playwright")
    @mock.patch("lib.capabilities._detect_ghas_cli")
    @mock.patch("lib.capabilities._detect_gh_codeql")
    @mock.patch("lib.capabilities._detect_gh")
    @mock.patch("lib.capabilities._detect_skills_cli")
    @mock.patch("lib.capabilities._tool_record")
    def test_optional_integrations_do_not_degrade_baseline_summary(
        self,
        tool_record: mock.Mock,
        detect_skills: mock.Mock,
        detect_gh: mock.Mock,
        detect_gh_codeql: mock.Mock,
        detect_ghas_cli: mock.Mock,
        detect_playwright: mock.Mock,
        detect_codex: mock.Mock,
        installed_skills: mock.Mock,
        config_payload: mock.Mock,
        enabled_plugins: mock.Mock,
        mcp_servers: mock.Mock,
        local_skill_names: mock.Mock,
    ) -> None:
        tool_record.side_effect = self._default_tool_record
        detect_skills.return_value = {"installed": True, "status": "ok", "version": "1.5.1"}
        detect_gh.return_value = {"installed": False, "status": "missing", "skill_supported": False}
        detect_gh_codeql.return_value = {"installed": False, "status": "missing", "name": "gh-codeql"}
        detect_ghas_cli.return_value = {"installed": False, "status": "missing", "name": "ghas-cli"}
        detect_playwright.return_value = {"installed": False, "status": "missing", "wrapper_ready": False}
        detect_codex.return_value = {"installed": True, "status": "ok", "callable": True, "worker_runtime_ready": True}
        installed_skills.return_value = {"status": "ok", "items": []}
        config_payload.return_value = {}
        enabled_plugins.return_value = {"loopsmith": {"name": "loopsmith", "enabled": True, "status": "ok"}}
        mcp_servers.return_value = {}
        local_skill_names.return_value = {
            "context-skill",
            "ui-skill",
            "ui-deep-audit",
            "test-skill",
            "test-deep-audit",
            "docs-skill",
            "docs-deep-audit",
            "refactor-skill",
            "refactor-deep-audit",
            "refactor-orchestrator",
            "cicd-skill",
            "cicd-deep-audit",
            "internet-researcher",
            "github-researcher",
            "web-github-scout",
            "research-capability",
            "skills-management-capability",
            "autonomous-deep-runs-capability",
            "agentctl-maintenance-engineer",
            "ios-development-capability",
            "macos-development-capability",
            "android-testing-capability",
        }

        report = build_capabilities_report()
        self.assertEqual(report["summary"]["status"], "ok")
        self.assertGreater(report["summary"]["optional_attention_count"], 0)

    @mock.patch("lib.capabilities._local_skill_names")
    @mock.patch("lib.capabilities._mcp_servers_map")
    @mock.patch("lib.capabilities._enabled_plugins_map")
    @mock.patch("lib.capabilities._config_payload")
    @mock.patch("lib.capabilities._installed_skills")
    @mock.patch("lib.capabilities.detect_codex_runtime")
    @mock.patch("lib.capabilities._detect_playwright")
    @mock.patch("lib.capabilities._detect_ghas_cli")
    @mock.patch("lib.capabilities._detect_gh_codeql")
    @mock.patch("lib.capabilities._detect_gh")
    @mock.patch("lib.capabilities._detect_skills_cli")
    @mock.patch("lib.capabilities._tool_record")
    def test_autonomous_deep_runs_stays_ok_when_default_codex_runtime_is_unavailable(
        self,
        tool_record: mock.Mock,
        detect_skills: mock.Mock,
        detect_gh: mock.Mock,
        detect_gh_codeql: mock.Mock,
        detect_ghas_cli: mock.Mock,
        detect_playwright: mock.Mock,
        detect_codex: mock.Mock,
        installed_skills: mock.Mock,
        config_payload: mock.Mock,
        enabled_plugins: mock.Mock,
        mcp_servers: mock.Mock,
        local_skill_names: mock.Mock,
    ) -> None:
        tool_record.side_effect = self._default_tool_record
        detect_skills.return_value = {"installed": True, "status": "ok", "version": "1.5.1"}
        detect_gh.return_value = {"installed": True, "status": "ok", "version": "gh 1.0", "skill_supported": False}
        detect_gh_codeql.return_value = self._default_tool_record("gh-codeql")
        detect_ghas_cli.return_value = self._default_tool_record("ghas-cli")
        detect_playwright.return_value = {"installed": True, "status": "ok", "wrapper_ready": True}
        detect_codex.return_value = {
            "installed": True,
            "status": "degraded",
            "callable": False,
            "worker_runtime_ready": False,
        }
        installed_skills.return_value = {"status": "ok", "items": []}
        config_payload.return_value = {}
        enabled_plugins.return_value = {"loopsmith": {"name": "loopsmith", "enabled": True, "status": "ok"}}
        mcp_servers.return_value = {}
        local_skill_names.return_value = {
            "context-skill",
            "ui-skill",
            "ui-deep-audit",
            "test-skill",
            "test-deep-audit",
            "docs-skill",
            "docs-deep-audit",
            "refactor-skill",
            "refactor-deep-audit",
            "refactor-orchestrator",
            "cicd-skill",
            "cicd-deep-audit",
            "internet-researcher",
            "github-researcher",
            "web-github-scout",
            "research-capability",
            "skills-management-capability",
            "autonomous-deep-runs-capability",
            "agentctl-maintenance-engineer",
            "ios-development-capability",
            "macos-development-capability",
            "android-testing-capability",
        }

        report = build_capabilities_report()
        capability = next(item for item in report["capabilities"] if item["key"] == "autonomous-deep-runs")

        self.assertEqual(report["summary"]["status"], "ok")
        self.assertEqual(capability["status"], "ok")
        self.assertIn("AGENTCTL_CODEX_WORKER_TEMPLATE", capability["advisory"])

    @mock.patch("lib.capabilities._local_skill_names")
    @mock.patch("lib.capabilities._mcp_servers_map")
    @mock.patch("lib.capabilities._enabled_plugins_map")
    @mock.patch("lib.capabilities._config_payload")
    @mock.patch("lib.capabilities._installed_skills")
    @mock.patch("lib.capabilities.detect_codex_runtime")
    @mock.patch("lib.capabilities._detect_playwright")
    @mock.patch("lib.capabilities._detect_ghas_cli")
    @mock.patch("lib.capabilities._detect_gh_codeql")
    @mock.patch("lib.capabilities._detect_gh")
    @mock.patch("lib.capabilities._detect_skills_cli")
    @mock.patch("lib.capabilities._tool_record")
    def test_capability_detail_exposes_supabase_cli_first_notes(
        self,
        tool_record: mock.Mock,
        detect_skills: mock.Mock,
        detect_gh: mock.Mock,
        detect_gh_codeql: mock.Mock,
        detect_ghas_cli: mock.Mock,
        detect_playwright: mock.Mock,
        detect_codex: mock.Mock,
        installed_skills: mock.Mock,
        config_payload: mock.Mock,
        enabled_plugins: mock.Mock,
        mcp_servers: mock.Mock,
        local_skill_names: mock.Mock,
    ) -> None:
        tool_record.side_effect = self._default_tool_record
        detect_skills.return_value = {"installed": True, "status": "ok", "version": "1.5.1"}
        detect_gh.return_value = {"installed": True, "status": "ok", "version": "gh 1.0", "skill_supported": False}
        detect_gh_codeql.return_value = self._default_tool_record("gh-codeql")
        detect_ghas_cli.return_value = self._default_tool_record("ghas-cli")
        detect_playwright.return_value = {"installed": True, "status": "ok", "wrapper_ready": True}
        detect_codex.return_value = {"installed": True, "status": "ok", "callable": True, "worker_runtime_ready": True}
        installed_skills.return_value = {"status": "ok", "items": []}
        config_payload.return_value = {}
        enabled_plugins.return_value = {"loopsmith": {"name": "loopsmith", "enabled": True, "status": "ok"}}
        mcp_servers.return_value = {}
        local_skill_names.return_value = {
            "supabase-capability",
        }

        report = build_capabilities_report()
        detail = capability_detail(report, "supabase-data")

        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail["front_door"], "$supabase-capability")
        self.assertEqual(detail["status"], "ok")
        self.assertTrue(any("CLI-first" in note for note in detail["routing_notes"]))

    @mock.patch("lib.capabilities._local_skill_names")
    @mock.patch("lib.capabilities._mcp_servers_map")
    @mock.patch("lib.capabilities._enabled_plugins_map")
    @mock.patch("lib.capabilities._config_payload")
    @mock.patch("lib.capabilities._installed_skills")
    @mock.patch("lib.capabilities.detect_codex_runtime")
    @mock.patch("lib.capabilities._detect_playwright")
    @mock.patch("lib.capabilities._detect_ghas_cli")
    @mock.patch("lib.capabilities._detect_gh_codeql")
    @mock.patch("lib.capabilities._detect_gh")
    @mock.patch("lib.capabilities._detect_skills_cli")
    @mock.patch("lib.capabilities._tool_record")
    def test_capability_detail_exposes_github_advanced_security_routes(
        self,
        tool_record: mock.Mock,
        detect_skills: mock.Mock,
        detect_gh: mock.Mock,
        detect_gh_codeql: mock.Mock,
        detect_ghas_cli: mock.Mock,
        detect_playwright: mock.Mock,
        detect_codex: mock.Mock,
        installed_skills: mock.Mock,
        config_payload: mock.Mock,
        enabled_plugins: mock.Mock,
        mcp_servers: mock.Mock,
        local_skill_names: mock.Mock,
    ) -> None:
        tool_record.side_effect = self._default_tool_record
        detect_skills.return_value = {"installed": True, "status": "ok", "version": "1.5.1"}
        detect_gh.return_value = {"installed": True, "status": "ok", "version": "gh 1.0", "skill_supported": False}
        detect_gh_codeql.return_value = self._default_tool_record("gh-codeql")
        detect_ghas_cli.return_value = {
            "installed": True,
            "status": "degraded",
            "name": "ghas-cli",
            "callable": False,
            "runtime_error": "ModuleNotFoundError: No module named 'cli'",
        }
        detect_playwright.return_value = {"installed": True, "status": "ok", "wrapper_ready": True}
        detect_codex.return_value = {"installed": True, "status": "ok", "callable": True, "worker_runtime_ready": True}
        installed_skills.return_value = {"status": "ok", "items": []}
        config_payload.return_value = {}
        enabled_plugins.return_value = {
            "github@openai-curated": {"name": "github@openai-curated", "enabled": True, "status": "ok"},
            "loopsmith": {"name": "loopsmith", "enabled": True, "status": "ok"},
        }
        mcp_servers.return_value = {}
        local_skill_names.return_value = {"github-capability", "github-security-capability"}

        report = build_capabilities_report()
        detail = capability_detail(report, "github-advanced-security")

        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail["front_door"], "$github-security-capability")
        self.assertIn("gh codeql", detail["entrypoints"])
        self.assertIn("gh api", detail["entrypoints"])
        self.assertTrue(any("GHAS-specific" in note for note in detail["routing_notes"]))

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

    def test_every_capability_has_a_local_skill_front_door(self) -> None:
        for spec in CAPABILITY_SPECS:
            self.assertTrue(spec.get("skills"), f"{spec['key']} should expose at least one local skill")
            self.assertIn("$", spec["front_door"], f"{spec['key']} should route through a skill front door")


if __name__ == "__main__":
    unittest.main()
