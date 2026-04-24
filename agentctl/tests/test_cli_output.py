from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.capabilities import (
    print_doctor_human,
    print_capabilities_human,
    print_capability_human,
    print_research_human,
    print_skills_human,
    print_status_human,
)
from lib.computer_intel import print_computer_intel_human
from lib.overview import print_overview_human
from lib.inventory import print_inventory_human

CLI_ENTRY = Path(__file__).resolve().parents[1] / "agentctl.py"
REPO_ROOT = Path(__file__).resolve().parents[2]


class CliOutputTests(unittest.TestCase):
    def _write_inventory_snapshot(self) -> None:
        inventory_path = REPO_ROOT / "agentctl" / "state" / "inventory.json"
        inventory_path.parent.mkdir(parents=True, exist_ok=True)
        inventory_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "generated_at": "2026-04-19T00:00:00+00:00",
                    "summary": {"status": "ok", "max_bucket_size": 1},
                    "menu_budget": {"max_items": 25},
                    "tool_map": {
                        "python": {"installed": True, "status": "ok", "version": "3.12.0"},
                        "npx": {"installed": True, "status": "ok", "version": "10.0.0"},
                        "skills": {"installed": True, "status": "ok", "version": "1.5.1"},
                        "codex": {"installed": True, "status": "ok", "callable": True, "worker_runtime_ready": True},
                        "gh": {"installed": True, "status": "ok", "skill_supported": False},
                        "gh-codeql": {"installed": True, "status": "ok"},
                        "ghas-cli": {"installed": True, "status": "ok", "callable": True},
                        "vercel": {"installed": True, "status": "ok"},
                        "supabase": {"installed": True, "status": "ok"},
                        "graphify": {"installed": True, "status": "ok", "version": "graphify v4"},
                        "obsidian": {"installed": True, "status": "ok", "version": "Obsidian"},
                        "firebase": {"installed": False, "status": "missing", "detect_only": True},
                        "gcloud": {"installed": False, "status": "missing", "detect_only": True},
                        "playwright": {"installed": True, "status": "ok", "wrapper_ready": True},
                    },
                    "items": [
                        {"kind": "skill", "name": "loopsmith", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                        {"kind": "skill", "name": "autonomous-deep-runs-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                        {"kind": "skill", "name": "skills-management-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                        {"kind": "skill", "name": "agentcli-maintenance-engineer", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
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
                        {"kind": "skill", "name": "supabase-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                        {"kind": "skill", "name": "github-security-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                        {"kind": "skill", "name": "research-capability", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                        {"kind": "skill", "name": "internet-researcher", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                        {"kind": "skill", "name": "github-researcher", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                        {"kind": "skill", "name": "web-github-scout", "source_scope": "user", "status": "ok", "source_hint": "npx skills ls -g"},
                        {"kind": "plugin", "name": "agent-cli-os", "source_scope": "user", "status": "ok", "enabled": True},
                        {"kind": "app", "name": "build-web-apps", "source_scope": "plugin", "status": "ok", "configured": True, "connector_id": "build-web-apps"},
                        {"kind": "app", "name": "figma", "source_scope": "plugin", "status": "degraded", "configured": True, "connector_id": "figma"},
                        {"kind": "mcp", "name": "supabase", "source_scope": "user", "status": "configured", "configured": True},
                        {"kind": "mcp", "name": "playwright", "source_scope": "user", "status": "degraded", "configured": True},
                    ],
                    "menu_buckets": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def test_doctor_human_is_compact_and_health_focused(self) -> None:
        payload = {
            "summary": {"status": "ok", "installed_skill_count": 17},
            "public_launcher": {"status": "missing", "detail": "`agentcli` is not available on PATH."},
            "tools": {
                "gh": {"installed": True, "skill_supported": False},
            },
            "detect_only_tools": ["firebase", "gcloud"],
            "capabilities": [
                {"label": "Research", "status": "ok", "front_door": "agentcli research", "required": True},
                {"label": "Supabase data", "status": "degraded", "front_door": "supabase + Supabase MCP", "required": False},
            ],
        }
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            print_doctor_human(payload)
        output = buffer.getvalue()
        self.assertIn("Healthy baseline capabilities: 1 / 1", output)
        self.assertIn("Needs attention", output)
        self.assertIn("not available on PATH", output)
        self.assertNotIn("Capability menu", output)

    def test_status_human_hides_history_and_surfaces_active_workflows(self) -> None:
        payload = {
            "summary": {"status": "ok", "count": 1, "historical_count": 4},
            "workflows": [
                {
                    "workflow_name": "agentcli-maintenance",
                    "status": "complete",
                    "tasks_done": 19,
                    "tasks_total": 19,
                    "tasks_open": 0,
                    "tasks_blocked": 0,
                    "iteration": 1,
                    "repo_root": r"C:\repo\agentctl",
                    "checklist_path": r"docs/agent-cli-os/maintenance.md",
                }
            ],
        }
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            print_status_human(payload)
        output = buffer.getvalue()
        self.assertIn("Active workflows: 1", output)
        self.assertIn("Historical workflows hidden: 4", output)
        self.assertIn("agentcli-maintenance: complete", output)

    def test_skills_human_distinguishes_local_and_external_management(self) -> None:
        payload = {
            "summary": {"status": "ok", "scope": "global"},
            "tracked_missing": [],
            "tracked_local": ["ui-skill", "test-skill"],
            "tracked_external": ["external-skill"],
            "unmanaged_installed": [],
        }
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            print_skills_human(payload)
        output = buffer.getvalue()
        self.assertIn("Managed local skills", output)
        self.assertIn("ui-skill", output)
        self.assertIn("Managed external skills", output)
        self.assertIn("external-skill", output)

    def test_research_human_shows_caveats_when_degraded(self) -> None:
        payload = {
            "status": "degraded",
            "mode": "github",
            "query": "agent skills cli",
            "evidence": {
                "shortlist": [{"title": "skills-cli", "url": "https://example.com"}],
                "caveats": ["GitHub CLI auth is unavailable."],
            },
            "paths": {"json": r"C:\tmp\evidence.json", "brief": r"C:\tmp\brief.md"},
        }
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            print_research_human(payload)
        output = buffer.getvalue()
        self.assertIn("Status: degraded", output)
        self.assertIn("Caveats", output)
        self.assertIn("GitHub CLI auth is unavailable.", output)

    def test_capabilities_human_points_to_drill_down_pages(self) -> None:
        payload = {
            "summary": {"status": "ok"},
            "tools": {"gh": {"installed": True, "skill_supported": False}, "codex": {"installed": True, "callable": False}},
            "detect_only_tools": ["firebase"],
            "capability_groups": [
                {"key": "platforms", "label": "Platforms", "count": 1},
                {"key": "research", "label": "Research", "count": 1},
            ],
            "capabilities": [
                {"key": "github-workflows", "label": "GitHub workflows", "status": "ok", "front_door": "$github-capability", "required": False, "group": "platforms"},
                {"key": "research", "label": "Research", "status": "ok", "front_door": "agentcli research", "required": True, "group": "research"},
            ],
        }
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            print_capabilities_human(payload)
        output = buffer.getvalue()
        self.assertIn("Platforms [ok] 1 items", output)
        self.assertIn("Use `agentcli capability <key>`", output)

    def test_overview_human_is_compact_and_names_first(self) -> None:
        payload = {
            "summary": {"status": "healthy", "front_door_group_count": 2, "cli_count": 3, "app_count": 2, "mcp_count": 1, "plugin_count": 2},
            "repo_intel": {
                "repo_root": r"C:\repo",
                "repo_name": "repo",
                "status": "fresh",
                "detail": "Repo graph exists and matches the current repo state.",
                "trusted": True,
                "recommended_action": "No action needed.",
                "default_mode": "repo-first",
                "computer_intel_role": "exception-only",
            },
            "front_doors": [
                {"key": "core", "label": "Core", "status": "healthy", "count": 2, "items": ["Autonomous deep runs", "Long task loops"]},
                {"key": "workflows", "label": "Workflows", "status": "degraded", "count": 1, "items": ["UI workflows"]},
            ],
            "clis": {"status": "healthy", "items": {"healthy": ["codex", "gh"], "missing": ["aws"]}},
            "apps": {
                "status": "degraded",
                "items": {
                    "healthy": [
                        "a [connector: a]",
                        "b [connector: b]",
                        "c [connector: c]",
                        "d [connector: d]",
                        "e [connector: e]",
                        "f [connector: f]",
                        "g [connector: g]",
                        "h [connector: h]",
                        "i [connector: i]",
                    ],
                    "degraded": ["figma [connector: figma]"],
                },
            },
            "mcps": {"status": "healthy", "items": {"healthy": ["supabase"], "degraded": ["playwright"]}},
            "plugins": {"status": "healthy", "items": {"healthy": ["agent-cli-os", "plugin-eval:plugin-eval"]}},
        }
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            print_overview_human(payload)
        output = buffer.getvalue()
        self.assertIn("Current repo intelligence", output)
        self.assertIn("repo [fresh] repo-first", output)
        self.assertIn("Front-door capabilities", output)
        self.assertIn("Core [healthy] 2: Autonomous deep runs, Long task loops", output)
        self.assertIn("Apps / connectors", output)
        self.assertIn("a [connector: a]", output)
        self.assertIn("+1 more", output)
        self.assertIn("Use `agentcli capabilities`", output)

    def test_inventory_human_renders_bucketed_raw_inventory(self) -> None:
        payload = {
            "summary": {"status": "ok", "total_items": 2, "bucket_count": 1},
            "menu_buckets": [{"key": "tool:system", "count": 2, "split": False, "item_ids": ["tool:gh@system", "tool:vercel@system"]}],
            "items": [
                {"id": "tool:gh@system", "kind": "tool", "name": "gh", "source_scope": "system", "status": "ok", "menu_bucket": "tool:system"},
                {"id": "tool:vercel@system", "kind": "tool", "name": "vercel", "source_scope": "system", "status": "missing", "menu_bucket": "tool:system"},
            ],
        }
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            print_inventory_human(payload)
        output = buffer.getvalue()
        self.assertIn("tool:system [2]", output)
        self.assertIn("gh [ok]", output)
        self.assertIn("vercel [missing]", output)

    def test_capability_human_surfaces_doc_page_and_routing_notes(self) -> None:
        payload = {
            "key": "supabase-data",
            "label": "Supabase data",
            "status": "ok",
            "front_door": "$supabase-capability",
            "doc_path": r"C:\repo\docs\agent-cli-os\capabilities\supabase-data.md",
            "summary": "Use for local Supabase stacks and database workflows.",
            "skills": ["supabase-capability"],
            "entrypoints": ["$supabase-capability", "supabase", "Supabase MCP"],
            "routing_notes": ["CLI-first: `supabase init` and `supabase start` are the default path."],
            "backing_interfaces": [{"kind": "tool", "name": "supabase", "status": "ok"}],
            "cloud_readiness": [{"name": "supabase", "classification": "cloud-ready-with-setup", "requirements": ["Supabase CLI"], "notes": "project/auth context"}],
            "overlap_policy": "Prefer the Supabase CLI first.",
        }
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            print_capability_human(payload)
        output = buffer.getvalue()
        self.assertIn("Doc page:", output)
        self.assertIn("CLI-first", output)
        self.assertIn("supabase-capability", output)

    def test_computer_intel_human_surfaces_machine_counts(self) -> None:
        payload = {
            "kind": "computer-intel-status",
            "status": "ok",
            "detail": "Machine-wide computer-intel registry refreshed.",
            "generated_at": "2026-04-21T00:00:00+00:00",
            "state_path": r"C:\repo\agentctl\state\computer-graph.json",
            "summary": {
                "root_count": 3,
                "repo_count": 10,
                "trusted_repo_count": 4,
                "managed_repo_count": 5,
                "vault_count": 2,
                "graph_count": 7,
                "service_count": 3,
                "truncated": False,
            },
        }
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            print_computer_intel_human(payload)
        output = buffer.getvalue()
        self.assertIn("Counts", output)
        self.assertIn("- repos: 10", output)
        self.assertIn("agentcli computer-intel search <query>", output)

    def test_capability_command_emits_json_for_known_key(self) -> None:
        self._write_inventory_snapshot()
        env = os.environ.copy()
        env["CODEX_HOME"] = str(REPO_ROOT)
        result = subprocess.run(
            [sys.executable, str(CLI_ENTRY), "capability", "supabase-data", "--json"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["key"], "supabase-data")
        self.assertEqual(payload["front_door"], "$supabase-capability")

    def test_capability_command_emits_json_for_github_advanced_security(self) -> None:
        self._write_inventory_snapshot()
        env = os.environ.copy()
        env["CODEX_HOME"] = str(REPO_ROOT)
        result = subprocess.run(
            [sys.executable, str(CLI_ENTRY), "capability", "github-advanced-security", "--json"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["key"], "github-advanced-security")
        self.assertEqual(payload["front_door"], "$github-security-capability")
        self.assertIn("gh codeql", payload["entrypoints"])

    def test_overview_command_emits_json(self) -> None:
        self._write_inventory_snapshot()
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            repo_root.mkdir(parents=True, exist_ok=True)
            (repo_root / ".git").mkdir()
            (repo_root / "app.py").write_text("print('ok')\n", encoding="utf-8")
            env = os.environ.copy()
            env["CODEX_HOME"] = str(REPO_ROOT)
            result = subprocess.run(
                [sys.executable, str(CLI_ENTRY), "overview", "--repo", str(repo_root), "--json"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["kind"], "overview")
        self.assertIn("front_doors", payload)
        self.assertIn("apps", payload)
        self.assertIn("mcps", payload)
        self.assertEqual(payload["repo_intel"]["repo_name"], "repo")

    def test_inventory_show_supports_apps_kind(self) -> None:
        self._write_inventory_snapshot()
        env = os.environ.copy()
        env["CODEX_HOME"] = str(REPO_ROOT)
        result = subprocess.run(
            [sys.executable, str(CLI_ENTRY), "inventory", "show", "--kind", "apps", "--json"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["total_items"], 2)
        self.assertEqual({item["kind"] for item in payload["items"]}, {"app"})

    def test_repo_intel_status_command_emits_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            repo_root.mkdir(parents=True, exist_ok=True)
            (repo_root / "app.py").write_text("print('ok')\n", encoding="utf-8")
            env = os.environ.copy()
            env["CODEX_HOME"] = str(REPO_ROOT)
            result = subprocess.run(
                [sys.executable, str(CLI_ENTRY), "repo-intel", "status", "--repo", str(repo_root), "--json"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["kind"], "repo-intel-status")
        self.assertEqual(payload["status"], "missing")

    def test_computer_intel_status_command_emits_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            codex_home = Path(temp_dir) / ".codex"
            agentctl_state = codex_home / "agentctl" / "state"
            agentctl_state.mkdir(parents=True, exist_ok=True)
            (agentctl_state / "computer-graph.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "generated_at": "2026-04-21T00:00:00+00:00",
                        "status": "ok",
                        "detail": "Machine-wide computer-intel registry refreshed.",
                        "summary": {
                            "root_count": 1,
                            "repo_count": 2,
                            "trusted_repo_count": 1,
                            "managed_repo_count": 1,
                            "vault_count": 1,
                            "graph_count": 1,
                            "service_count": 0,
                            "truncated": False,
                        },
                        "roots": [{"kind": "root", "name": "Documents", "path": r"C:\Users\leona\Documents"}],
                        "repos": [],
                        "vaults": [],
                        "graphs": [],
                        "services": [],
                        "scan_stats": {"scanned_directories": 1, "skipped_directories": 0, "inaccessible_directories": 0, "truncated": False, "directory_budget": 50000},
                        "config": {"enabled": True, "scan_scope": "laptop"},
                    }
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["CODEX_HOME"] = str(codex_home)
            result = subprocess.run(
                [sys.executable, str(CLI_ENTRY), "computer-intel", "status", "--json"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["kind"], "computer-intel-status")
        self.assertEqual(payload["status"], "ok")


if __name__ == "__main__":
    unittest.main()
