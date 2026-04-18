from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.codex_runtime import (
    CODEX_ENV_TEMPLATE,
    CODEX_PATH_ENV,
    builtin_codex_worker_command,
    detect_codex_runtime,
    render_worker_command_template,
    resolve_codex_worker_command,
)


class CodexRuntimeTests(unittest.TestCase):
    @mock.patch("lib.codex_runtime._windows_global_cli_candidates")
    def test_candidate_paths_prefer_windows_global_cli_shim(self, windows_candidates: mock.Mock) -> None:
        windows_candidates.return_value = [r"C:\Users\tester\AppData\Roaming\npm\codex.cmd"]
        from lib.codex_runtime import _candidate_paths

        with mock.patch("lib.codex_runtime.command_path", side_effect=lambda value: value if value in {"codex", "codex.cmd"} else None):
            candidates = _candidate_paths()

        self.assertEqual(candidates[0], r"C:\Users\tester\AppData\Roaming\npm\codex.cmd")

    @mock.patch("lib.codex_runtime.run_command")
    @mock.patch("lib.codex_runtime._candidate_paths")
    def test_detect_codex_runtime_reports_degraded_when_not_callable(self, candidate_paths: mock.Mock, run_command: mock.Mock) -> None:
        candidate_paths.return_value = [r"C:\Program Files\WindowsApps\OpenAI.Codex\codex.exe"]
        run_command.return_value = {"ok": False, "stderr": "[WinError 5] Access is denied", "stdout": "", "returncode": 126}

        payload = detect_codex_runtime()

        self.assertTrue(payload["installed"])
        self.assertFalse(payload["callable"])
        self.assertEqual(payload["status"], "degraded")
        self.assertFalse(payload["worker_runtime_ready"])

    @mock.patch("lib.codex_runtime.run_command")
    def test_detect_codex_runtime_prefers_explicit_path_env(self, run_command: mock.Mock) -> None:
        run_command.return_value = {"ok": True, "stderr": "", "stdout": "help", "returncode": 0}

        with mock.patch.dict(os.environ, {CODEX_PATH_ENV: r"C:\tools\codex.cmd"}, clear=False):
            payload = detect_codex_runtime()

        self.assertEqual(payload["path"], r"C:\tools\codex.cmd")
        self.assertTrue(payload["callable"])
        self.assertTrue(payload["worker_runtime_ready"])

    @mock.patch("lib.codex_runtime.run_command")
    @mock.patch("lib.codex_runtime._candidate_paths")
    def test_detect_codex_runtime_template_keeps_worker_ready_when_binary_is_degraded(self, candidate_paths: mock.Mock, run_command: mock.Mock) -> None:
        candidate_paths.return_value = [r"C:\Program Files\WindowsApps\OpenAI.Codex\codex.exe"]
        run_command.return_value = {"ok": False, "stderr": "[WinError 5] Access is denied", "stdout": "", "returncode": 126}

        with mock.patch.dict(os.environ, {CODEX_ENV_TEMPLATE: "custom worker"}, clear=False):
            payload = detect_codex_runtime()

        self.assertEqual(payload["status"], "degraded")
        self.assertFalse(payload["callable"])
        self.assertTrue(payload["template_configured"])
        self.assertTrue(payload["worker_runtime_ready"])

    @mock.patch("lib.codex_runtime.detect_codex_runtime")
    def test_render_worker_command_template_formats_runtime_context(self, detect_runtime: mock.Mock) -> None:
        detect_runtime.return_value = {"path": r"C:\tools\codex.cmd"}

        rendered = render_worker_command_template(
            '{python_q} {codex_worker_q} --repo {repo_root} --state {state_path} --codex {codex_path_q}',
            workflow="ui-deep-audit",
            repo_root=Path(r"C:\repo"),
            checklist_path=Path(r"C:\repo\docs\ui-deep-audit-checklist.md"),
            progress_path=Path(r"C:\repo\docs\ui-deep-audit-progress.md"),
            state_path=Path(r"C:\repo\.codex-workflows\ui-deep-audit\state.json"),
        )

        self.assertIn("codex_worker.py", rendered)
        self.assertIn(r"C:\repo", rendered)
        self.assertIn(r"C:\tools\codex.cmd", rendered)

    @mock.patch("lib.codex_runtime.detect_codex_runtime")
    def test_resolve_codex_worker_command_returns_builtin_wrapper_when_runtime_is_callable(self, detect_runtime: mock.Mock) -> None:
        detect_runtime.return_value = {"callable": True, "path": "codex"}

        resolved = resolve_codex_worker_command(
            workflow="docs-deep-audit",
            repo_root=Path(r"C:\repo"),
            checklist_path=Path(r"C:\repo\docs\docs-deep-audit-checklist.md"),
            progress_path=Path(r"C:\repo\docs\docs-deep-audit-progress.md"),
            state_path=Path(r"C:\repo\.codex-workflows\docs-deep-audit\state.json"),
        )

        self.assertEqual(resolved, builtin_codex_worker_command())

    @mock.patch("lib.codex_runtime.detect_codex_runtime")
    def test_resolve_codex_worker_command_uses_template_when_present(self, detect_runtime: mock.Mock) -> None:
        detect_runtime.return_value = {"callable": False, "path": r"C:\tools\codex.cmd"}
        template = '{python_q} "{repo_root}" "{checklist_path}" "{state_path}"'

        with mock.patch.dict(os.environ, {CODEX_ENV_TEMPLATE: template}, clear=False):
            resolved = resolve_codex_worker_command(
                workflow="test-deep-audit",
                repo_root=Path(r"C:\repo"),
                checklist_path=Path(r"C:\repo\docs\test-deep-audit-checklist.md"),
                progress_path=Path(r"C:\repo\docs\test-deep-audit-progress.md"),
                state_path=Path(r"C:\repo\.codex-workflows\test-deep-audit\state.json"),
            )

        self.assertIn(str(Path(r"C:\repo")), resolved)
        self.assertIn("test-deep-audit-checklist.md", resolved)


if __name__ == "__main__":
    unittest.main()
