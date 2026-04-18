from __future__ import annotations

import io
import json
import os
import subprocess
import sys
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

CLI_ENTRY = Path(__file__).resolve().parents[1] / "agentctl.py"
REPO_ROOT = Path(__file__).resolve().parents[2]


class CliOutputTests(unittest.TestCase):
    def test_doctor_human_is_compact_and_health_focused(self) -> None:
        payload = {
            "summary": {"status": "ok", "installed_skill_count": 17},
            "tools": {
                "gh": {"installed": True, "skill_supported": False},
            },
            "detect_only_tools": ["firebase", "gcloud"],
            "capabilities": [
                {"label": "Research", "status": "ok", "front_door": "agentctl research", "required": True},
                {"label": "Supabase data", "status": "degraded", "front_door": "supabase + Supabase MCP", "required": False},
            ],
        }
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            print_doctor_human(payload)
        output = buffer.getvalue()
        self.assertIn("Healthy baseline capabilities: 1 / 1", output)
        self.assertIn("Needs attention", output)
        self.assertNotIn("Capability menu", output)

    def test_status_human_hides_history_and_surfaces_active_workflows(self) -> None:
        payload = {
            "summary": {"status": "ok", "count": 1, "historical_count": 4},
            "workflows": [
                {
                    "workflow_name": "agentctl-maintenance",
                    "status": "complete",
                    "tasks_done": 19,
                    "tasks_total": 19,
                    "tasks_open": 0,
                    "tasks_blocked": 0,
                    "iteration": 1,
                    "repo_root": r"C:\repo\agentctl",
                    "checklist_path": r"docs/agentctl/maintenance.md",
                }
            ],
        }
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            print_status_human(payload)
        output = buffer.getvalue()
        self.assertIn("Active workflows: 1", output)
        self.assertIn("Historical workflows hidden: 4", output)
        self.assertIn("agentctl-maintenance: complete", output)

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
            "capabilities": [
                {"key": "github-workflows", "label": "GitHub workflows", "status": "ok", "front_door": "$github-capability", "required": False, "group": "integrations"},
                {"key": "research", "label": "Research", "status": "ok", "front_door": "agentctl research", "required": True, "group": "research-and-verification"},
            ],
        }
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            print_capabilities_human(payload)
        output = buffer.getvalue()
        self.assertIn("github-workflows", output)
        self.assertIn("Use `agentctl capability <key>`", output)

    def test_capability_human_surfaces_doc_page_and_routing_notes(self) -> None:
        payload = {
            "key": "supabase-data",
            "label": "Supabase data",
            "status": "ok",
            "front_door": "$supabase-capability",
            "doc_path": r"C:\repo\docs\agentctl\capabilities\supabase-data.md",
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

    def test_capability_command_emits_json_for_known_key(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
