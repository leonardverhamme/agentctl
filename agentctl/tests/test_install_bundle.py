from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "install_bundle.py"
SPEC = importlib.util.spec_from_file_location("install_bundle", MODULE_PATH)
assert SPEC and SPEC.loader
install_bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(install_bundle)


class InstallBundleTests(unittest.TestCase):
    def test_bundle_items_include_readme(self) -> None:
        self.assertIn("README.md", install_bundle.BUNDLE_ITEMS)

    def test_ensure_plugin_enabled_appends_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text("[plugins.other]\nenabled = true\n", encoding="utf-8")

            install_bundle.ensure_plugin_enabled(config_path)
            first = config_path.read_text(encoding="utf-8")
            install_bundle.ensure_plugin_enabled(config_path)
            second = config_path.read_text(encoding="utf-8")

        self.assertIn('[plugins."agentctl"]', first)
        self.assertEqual(first, second)

    def test_ensure_plugin_enabled_migrates_legacy_plugin_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text('[plugins."agentctl-platform"]\nenabled = true\n', encoding="utf-8")

            install_bundle.ensure_plugin_enabled(config_path)
            updated = config_path.read_text(encoding="utf-8")

        self.assertIn('[plugins."agentctl"]', updated)
        self.assertNotIn('agentctl-platform', updated)

    def test_cleanup_legacy_plugin_removes_old_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_root = Path(temp_dir)
            legacy = target_root / "plugins" / "agentctl-platform"
            legacy.mkdir(parents=True, exist_ok=True)
            (legacy / "placeholder.txt").write_text("x", encoding="utf-8")

            install_bundle.cleanup_legacy_plugin(target_root)

            self.assertFalse(legacy.exists())

    @mock.patch("agentctl.bundle_install.subprocess.run")
    def test_run_post_install_checks_writes_bootstrap_report(self, run_mock: mock.Mock) -> None:
        run_mock.return_value = mock.Mock(returncode=0, stdout='{"status":"ok"}', stderr="")
        with tempfile.TemporaryDirectory() as temp_dir:
            target_root = Path(temp_dir)
            (target_root / "agentctl").mkdir(parents=True, exist_ok=True)
            summary = install_bundle.run_post_install_checks(target_root)
            report_path = target_root / "agentctl" / "state" / "bootstrap-report.json"

            self.assertEqual(summary["status"], "ok")
            self.assertTrue(report_path.exists())
            self.assertEqual(run_mock.call_count, 3)
            called_env = run_mock.call_args.kwargs["env"]
            self.assertEqual(called_env["CODEX_HOME"], str(target_root))

    def test_evaluate_post_check_accepts_degraded_json(self) -> None:
        result = mock.Mock(returncode=1, stdout='{"summary":{"status":"degraded","blocked_findings":0}}', stderr="")
        ok, reported_status = install_bundle.evaluate_post_check("maintenance", result)
        self.assertTrue(ok)
        self.assertEqual(reported_status, "degraded")

    def test_evaluate_post_check_rejects_blocked_maintenance(self) -> None:
        result = mock.Mock(returncode=1, stdout='{"summary":{"status":"error","blocked_findings":1}}', stderr="")
        ok, reported_status = install_bundle.evaluate_post_check("maintenance", result)
        self.assertFalse(ok)
        self.assertIsNone(reported_status)


if __name__ == "__main__":
    unittest.main()
