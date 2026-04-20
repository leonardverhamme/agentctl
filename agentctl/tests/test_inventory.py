from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.inventory import _apply_bucket_splitting, _merge_duplicate_items, _plugin_items, build_inventory_snapshot, filter_inventory_items, inventory_item


class InventoryTests(unittest.TestCase):
    def test_bucket_splitting_triggers_after_item_26(self) -> None:
        items = [
            {
                "id": f"skill:item-{index}@user",
                "kind": "skill",
                "name": f"item-{index:02d}",
                "source_scope": "user",
                "status": "ok",
                "menu_bucket": "skill:user",
            }
            for index in range(26)
        ]
        buckets = _apply_bucket_splitting(items, max_items=25)
        self.assertEqual(len(buckets), 2)
        self.assertEqual(max(bucket["count"] for bucket in buckets), 25)

    def test_inventory_item_handles_multiple_scopes(self) -> None:
        payload = {
            "items": [
                {"id": "tool:gh@system", "kind": "tool", "name": "gh", "source_scope": "system", "status": "ok"},
                {"id": "tool:gh@repo", "kind": "tool", "name": "gh", "source_scope": "repo", "status": "ok"},
            ]
        }
        result = inventory_item(payload, "tool:gh")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["kind"], "matches")
        self.assertEqual(len(result["matches"]), 2)

    def test_merge_duplicate_items_collapses_same_skill_scope(self) -> None:
        items = [
            {
                "id": "skill:ui-skill@user",
                "kind": "skill",
                "name": "ui-skill",
                "source_scope": "user",
                "status": "ok",
                "installed": True,
                "source_hint": "npx skills ls -g",
                "menu_bucket": "skill:user",
            },
            {
                "id": "skill:ui-skill@user",
                "kind": "skill",
                "name": "ui-skill",
                "source_scope": "user",
                "status": "ok",
                "installed": True,
                "source_path": r"C:\Users\leona\.codex\skills\ui-skill\SKILL.md",
                "menu_bucket": "skill:user",
            },
        ]
        merged = _merge_duplicate_items(items)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["name"], "ui-skill")
        self.assertIn("source_hint", merged[0])
        self.assertIn("source_path", merged[0])

    def test_plugin_items_skip_fixture_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plugins_root = Path(temp_dir)
            real_skill = plugins_root / "cache" / "openai-curated" / "plugin-eval" / "hash123" / "skills" / "plugin-eval" / "SKILL.md"
            fixture_skill = (
                plugins_root
                / "cache"
                / "openai-curated"
                / "plugin-eval"
                / "hash123"
                / "fixtures"
                / "minimal-plugin"
                / "skills"
                / "minimal-plugin-skill"
                / "SKILL.md"
            )
            real_skill.parent.mkdir(parents=True, exist_ok=True)
            fixture_skill.parent.mkdir(parents=True, exist_ok=True)
            real_skill.write_text("---\nname: plugin-eval\n---\n", encoding="utf-8")
            fixture_skill.write_text("---\nname: minimal-plugin-skill\n---\n", encoding="utf-8")

            with mock.patch("lib.inventory.PLUGINS_DIR", plugins_root):
                _, skill_items = _plugin_items({"plugins": {"plugin-eval@openai-curated": {"enabled": True}}})

        names = {item["name"] for item in skill_items}
        self.assertIn("plugin-eval:plugin-eval", names)
        self.assertNotIn("plugin-eval:minimal-plugin-skill", names)

    @mock.patch("lib.capabilities.run_command")
    @mock.patch("lib.capabilities._installed_skills")
    @mock.patch("lib.capabilities._detect_playwright")
    @mock.patch("lib.capabilities._detect_ghas_cli")
    @mock.patch("lib.capabilities._detect_gh_codeql")
    @mock.patch("lib.capabilities._gh_extensions")
    @mock.patch("lib.capabilities._detect_gh")
    @mock.patch("lib.capabilities._detect_skills_cli")
    @mock.patch("lib.capabilities.detect_codex_runtime")
    @mock.patch("lib.capabilities._tool_record")
    @mock.patch("lib.inventory.run_command")
    @mock.patch("lib.inventory.effective_config")
    @mock.patch("lib.inventory.PLUGINS_DIR", Path(r"C:\__agent_cli_os_test_plugins__"))
    @mock.patch("lib.inventory.SKILLS_DIR", Path(r"C:\__agent_cli_os_test_skills__"))
    def test_build_inventory_snapshot_records_expected_kinds(
        self,
        effective_config: mock.Mock,
        inventory_run_command: mock.Mock,
        tool_record: mock.Mock,
        detect_codex: mock.Mock,
        detect_skills_cli: mock.Mock,
        detect_gh: mock.Mock,
        gh_extensions: mock.Mock,
        detect_gh_codeql: mock.Mock,
        detect_ghas_cli: mock.Mock,
        detect_playwright: mock.Mock,
        installed_skills: mock.Mock,
        run_command: mock.Mock,
    ) -> None:
        effective_config.return_value = {
            "menus": {"max_items": 25},
            "plugins": {"agent-cli-os": {"enabled": True}},
            "mcp_servers": {"supabase": {"command": "supabase-mcp"}},
        }
        tool_record.side_effect = lambda name, **_: {"name": name, "installed": True, "status": "ok", "version": "1.0.0", "path": fr"C:\tools\{name}.exe", "command": name}
        detect_codex.return_value = {"installed": True, "status": "ok", "callable": True, "worker_runtime_ready": True, "path": r"C:\tools\codex.cmd", "command": "codex"}
        detect_skills_cli.return_value = {"installed": True, "status": "ok", "version": "1.5.1", "path": r"C:\tools\npx.cmd", "command": "npx skills"}
        detect_gh.return_value = {"installed": True, "status": "ok", "skill_supported": False, "path": r"C:\tools\gh.exe", "command": "gh"}
        gh_extensions.return_value = {}
        detect_gh_codeql.return_value = {"installed": True, "status": "ok", "path": r"C:\tools\gh.exe", "command": "gh codeql"}
        detect_ghas_cli.return_value = {"installed": True, "status": "ok", "path": r"C:\tools\ghas-cli.exe", "command": "ghas-cli"}
        detect_playwright.return_value = {"installed": True, "status": "ok", "path": r"C:\tools\playwright.cmd", "command": "python playwright_cli.py"}
        installed_skills.return_value = {"status": "ok", "items": [{"name": "loopsmith"}, {"name": "research-capability"}]}
        inventory_run_command.return_value = {"ok": True, "stdout": "[]", "stderr": "", "returncode": 0}
        run_command.return_value = {"ok": True, "stdout": "[]", "stderr": "", "returncode": 0}

        snapshot = build_inventory_snapshot(repo=Path.cwd())

        kinds = {item["kind"] for item in snapshot["items"]}
        tool_names = {item["name"] for item in snapshot["items"] if item["kind"] == "tool"}
        self.assertEqual(snapshot["schema_version"], 1)
        self.assertIn("tool", kinds)
        self.assertIn("skill", kinds)
        self.assertIn("plugin", kinds)
        self.assertIn("mcp", kinds)
        self.assertIn("gh", tool_names)
        self.assertIn("coderabbit", tool_names)
        self.assertIn("plugin-eval", tool_names)
        self.assertIn("supabase", tool_names)
        self.assertEqual(snapshot["summary"]["status"], "ok")

    def test_filter_inventory_items_respects_kind_and_scope(self) -> None:
        payload = {
            "schema_version": 1,
            "generated_at": "2026-04-19T00:00:00+00:00",
            "summary": {"status": "ok"},
            "menu_budget": {"max_items": 25},
            "items": [
                {"id": "tool:gh@system", "kind": "tool", "name": "gh", "source_scope": "system", "status": "ok", "menu_bucket": "tool:system"},
                {"id": "skill:repo-skill@repo", "kind": "skill", "name": "repo-skill", "source_scope": "repo", "status": "ok", "menu_bucket": "skill:repo"},
            ],
            "menu_buckets": [
                {"key": "tool:system", "item_ids": ["tool:gh@system"], "count": 1, "split": False},
                {"key": "skill:repo", "item_ids": ["skill:repo-skill@repo"], "count": 1, "split": False},
            ],
        }
        filtered = filter_inventory_items(payload, kind="skills", scope="repo")
        self.assertEqual(filtered["summary"]["total_items"], 1)
        self.assertEqual(filtered["items"][0]["name"], "repo-skill")


if __name__ == "__main__":
    unittest.main()
