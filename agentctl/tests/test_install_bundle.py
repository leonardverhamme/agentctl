from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agentctl import bundle_install as bundle_install_module


MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "install_bundle.py"
SPEC = importlib.util.spec_from_file_location("install_bundle", MODULE_PATH)
assert SPEC and SPEC.loader
install_bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(install_bundle)


class InstallBundleTests(unittest.TestCase):
    def test_bundle_items_include_readme(self) -> None:
        self.assertIn("README.md", install_bundle.BUNDLE_ITEMS)

    def test_release_bundle_candidates_use_versioned_download_urls(self) -> None:
        candidates = bundle_install_module._release_bundle_candidates(
            "https://github.com/leonardverhamme/agent-cli-os",
            "v1.2.3",
        )

        self.assertEqual(candidates[0]["asset_name"], "agent-cli-os-bundle-v1.2.3.zip")
        self.assertEqual(
            candidates[0]["download_url"],
            "https://github.com/leonardverhamme/agent-cli-os/releases/download/v1.2.3/agent-cli-os-bundle-v1.2.3.zip",
        )

    def test_ensure_plugin_enabled_appends_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text("[plugins.other]\nenabled = true\n", encoding="utf-8")

            install_bundle.ensure_plugin_enabled(config_path)
            first = config_path.read_text(encoding="utf-8")
            install_bundle.ensure_plugin_enabled(config_path)
            second = config_path.read_text(encoding="utf-8")

        self.assertIn('[plugins."agent-cli-os"]', first)
        self.assertEqual(first, second)

    def test_ensure_plugin_enabled_migrates_legacy_plugin_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text('[plugins."agentctl-platform"]\nenabled = true\n', encoding="utf-8")

            install_bundle.ensure_plugin_enabled(config_path)
            updated = config_path.read_text(encoding="utf-8")

        self.assertIn('[plugins."agent-cli-os"]', updated)
        self.assertNotIn('agentctl-platform', updated)

    def test_cleanup_legacy_plugin_removes_old_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_root = Path(temp_dir)
            legacy = target_root / "plugins" / "agentctl-platform"
            legacy.mkdir(parents=True, exist_ok=True)
            (legacy / "placeholder.txt").write_text("x", encoding="utf-8")

            install_bundle.cleanup_legacy_plugin(target_root)

            self.assertFalse(legacy.exists())

    def test_extract_archive_accepts_flat_release_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "bundle.zip"
            extract_root = root / "extract"
            with zipfile.ZipFile(archive_path, "w") as bundle:
                bundle.writestr("agentctl/agentctl.py", "print('ok')\n")
                bundle.writestr("workflow-tools/workflow_runner.py", "# runner\n")
                bundle.writestr("skills/test-skill/SKILL.md", "# test skill\n")
                bundle.writestr("plugins/agent-cli-os/.codex-plugin/plugin.json", "{}\n")
                bundle.writestr("README.md", "# Agent CLI OS\n")
                bundle.writestr("AGENTS.md", "# agents\n")
                bundle.writestr("agentcli.cmd", "@echo off\n")
                bundle.writestr("agentcli.sh", "#!/bin/sh\n")
                bundle.writestr("loopsmith.cmd", "@echo off\n")
                bundle.writestr("loopsmith.sh", "#!/bin/sh\n")
                bundle.writestr("agentctl.cmd", "@echo off\n")
                bundle.writestr("agentctl.sh", "#!/bin/sh\n")
                bundle.writestr("docs/agent-cli-os/overview.md", "# overview\n")

            extracted = bundle_install_module.extract_archive(archive_path, extract_root)

            self.assertEqual(extracted, extract_root)
            self.assertTrue((extract_root / "agentctl" / "agentctl.py").exists())

    def test_copy_item_strips_utf8_bom_from_skill_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_root = root / "source"
            target_root = root / "target"
            skill_path = source_root / "skills" / "ui-skill" / "SKILL.md"
            skill_path.parent.mkdir(parents=True, exist_ok=True)
            skill_path.write_bytes(b"\xef\xbb\xbf---\nname: ui-skill\ndescription: test\n---\n")

            bundle_install_module.copy_item(source_root, target_root, "skills")

            copied = target_root / "skills" / "ui-skill" / "SKILL.md"
            self.assertTrue(copied.exists())
            self.assertEqual(copied.read_bytes(), b"---\nname: ui-skill\ndescription: test\n---\n")

    def test_preferred_launcher_dir_prefers_existing_path_visible_launcher_dir_on_windows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            local_app_data = root / "AppData" / "Local"
            app_data = root / "AppData" / "Roaming"
            codex_bin = local_app_data / "OpenAI" / "Codex" / "bin"
            python_scripts = app_data / "Python" / "Scripts"
            python_scripts.mkdir(parents=True, exist_ok=True)
            with mock.patch("agentctl.bundle_install.os.name", "nt"), mock.patch.dict(
                "os.environ",
                {
                    "LOCALAPPDATA": str(local_app_data),
                    "APPDATA": str(app_data),
                    "PATH": os.pathsep.join([str(codex_bin), str(python_scripts)]),
                },
                clear=False,
            ):
                selected = bundle_install_module.preferred_launcher_dir()

        self.assertEqual(selected, python_scripts)

    def test_publish_public_launchers_writes_windows_cmd_shims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target_root = root / ".codex"
            (target_root / "agentctl").mkdir(parents=True, exist_ok=True)
            local_app_data = root / "AppData" / "Local"
            app_data = root / "AppData" / "Roaming"
            codex_bin = local_app_data / "OpenAI" / "Codex" / "bin"
            with mock.patch("agentctl.bundle_install.os.name", "nt"), mock.patch.dict(
                "os.environ",
                {
                    "LOCALAPPDATA": str(local_app_data),
                    "APPDATA": str(app_data),
                    "PATH": str(codex_bin),
                },
                clear=False,
            ):
                summary = bundle_install_module.publish_public_launchers(target_root)
                self.assertEqual(summary["status"], "ok")
                agentcli_launcher = Path(summary["commands"]["agentcli"])
                self.assertTrue(agentcli_launcher.exists())
                content = agentcli_launcher.read_text(encoding="utf-8")
                self.assertIn(str(target_root).replace("/", "\\"), content)
                self.assertIn('%CODEX_HOME%\\agentctl\\agentctl.py', content)

    @mock.patch("agentctl.bundle_install.publish_public_launchers")
    @mock.patch("agentctl.bundle_install.write_install_metadata")
    @mock.patch("agentctl.bundle_install.ensure_plugin_enabled")
    @mock.patch("agentctl.bundle_install.cleanup_legacy_plugin")
    @mock.patch("agentctl.bundle_install.copy_item")
    def test_install_bundle_auto_publishes_launchers_for_default_codex_home(
        self,
        copy_item_mock: mock.Mock,
        cleanup_mock: mock.Mock,
        ensure_plugin_mock: mock.Mock,
        metadata_mock: mock.Mock,
        publish_mock: mock.Mock,
    ) -> None:
        copy_item_mock.return_value = None
        cleanup_mock.return_value = []
        ensure_plugin_mock.return_value = None
        publish_mock.return_value = {"status": "ok", "launcher_dir": r"C:\shim"}
        with tempfile.TemporaryDirectory() as temp_dir:
            target_root = Path(temp_dir) / ".codex"
            metadata_mock.return_value = target_root / "agentctl" / "state" / "install-metadata.json"
            with mock.patch("agentctl.bundle_install.default_codex_home", return_value=target_root):
                summary = bundle_install_module.install_bundle(
                    source_root=Path(temp_dir) / "source",
                    target_root=target_root,
                    skip_post_checks=True,
                )

        publish_mock.assert_called_once_with(target_root)
        self.assertEqual(summary["launchers"]["status"], "ok")

    def test_public_launcher_health_ignores_repo_local_wrapper_and_finds_path_shim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo_root = root / "repo"
            repo_root.mkdir(parents=True, exist_ok=True)
            (repo_root / "agentcli.cmd").write_text("@echo off\r\n", encoding="utf-8")
            target_root = root / ".codex"
            expected_launcher = root / "Scripts" / "agentcli.cmd"
            expected_launcher.parent.mkdir(parents=True, exist_ok=True)
            expected_launcher.write_text("@echo off\r\n", encoding="utf-8")

            with mock.patch("agentctl.bundle_install.preferred_launcher_dir", return_value=expected_launcher.parent), mock.patch.dict(
                "os.environ",
                {"PATH": str(expected_launcher.parent)},
                clear=False,
            ):
                cwd_before = Path.cwd()
                try:
                    os.chdir(repo_root)
                    health = bundle_install_module.public_launcher_health(target_root)
                finally:
                    os.chdir(cwd_before)

        self.assertEqual(health["status"], "ok")
        self.assertEqual(Path(health["commands"]["agentcli"]["resolved_path"]), expected_launcher.resolve())

    @mock.patch("agentctl.bundle_install.install_bundle")
    @mock.patch("agentctl.bundle_install.extract_archive")
    @mock.patch("agentctl.bundle_install.download_archive")
    @mock.patch("agentctl.bundle_install._release_metadata")
    def test_bootstrap_bundle_prefers_direct_release_asset_for_version(
        self,
        release_metadata_mock: mock.Mock,
        download_mock: mock.Mock,
        extract_mock: mock.Mock,
        install_mock: mock.Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_root = Path(temp_dir) / ".codex"
            extract_mock.return_value = Path(temp_dir) / "src"
            install_mock.return_value = {"status": "ok"}

            bundle_install_module.bootstrap_bundle(
                target_root=target_root,
                repo_url="https://github.com/leonardverhamme/agent-cli-os",
                version="v1.2.3",
                skip_post_checks=True,
            )

        self.assertIn(
            "/releases/download/v1.2.3/agent-cli-os-bundle-v1.2.3.zip",
            download_mock.call_args_list[0].args[0],
        )
        release_metadata_mock.assert_not_called()

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
            self.assertEqual(run_mock.call_count, 4)
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
