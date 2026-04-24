from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.self_check import build_self_check


class SelfCheckTests(unittest.TestCase):
    def _capabilities(self) -> dict:
        return {
            "summary": {
                "status": "ok",
                "visible_group_count": 2,
                "max_group_size": 3,
            },
            "menu_budget": {
                "max_top_level_groups": 8,
                "max_group_items": 25,
            },
        }

    def _inventory(self) -> dict:
        return {
            "schema_version": 1,
            "generated_at": "2026-04-24T00:00:00+00:00",
            "summary": {"status": "ok"},
        }

    def _guidance(self) -> dict:
        return {
            "schema_version": 1,
            "summary": {"within_budget": True, "file_count": 0, "total_lines": 0},
        }

    @mock.patch("lib.self_check.public_launcher_health")
    @mock.patch("lib.self_check.read_install_metadata")
    def test_build_self_check_degrades_when_public_launcher_is_missing(
        self,
        install_metadata_mock: mock.Mock,
        launcher_mock: mock.Mock,
    ) -> None:
        install_metadata_mock.return_value = {"version": "v1.0.0"}
        launcher_mock.return_value = {
            "status": "missing",
            "detail": "`agentcli` is not available on PATH and no published launcher shim was found.",
        }

        payload = build_self_check(
            self._capabilities(),
            inventory=self._inventory(),
            guidance=self._guidance(),
        )

        self.assertEqual(payload["status"], "degraded")
        launcher_check = next(item for item in payload["checks"] if item["name"] == "public-launcher")
        self.assertEqual(launcher_check["status"], "degraded")
        self.assertIn("not available on PATH", launcher_check["detail"])

    @mock.patch("lib.self_check.public_launcher_health")
    @mock.patch("lib.self_check.read_install_metadata")
    def test_build_self_check_keeps_ok_when_public_launcher_is_healthy(
        self,
        install_metadata_mock: mock.Mock,
        launcher_mock: mock.Mock,
    ) -> None:
        install_metadata_mock.return_value = {"version": "v1.0.0"}
        launcher_mock.return_value = {
            "status": "ok",
            "detail": "`agentcli` resolves at C:\\shim\\agentcli.cmd.",
        }

        payload = build_self_check(
            self._capabilities(),
            inventory=self._inventory(),
            guidance=self._guidance(),
        )

        self.assertEqual(payload["status"], "ok")
        launcher_check = next(item for item in payload["checks"] if item["name"] == "public-launcher")
        self.assertEqual(launcher_check["status"], "ok")


if __name__ == "__main__":
    unittest.main()
