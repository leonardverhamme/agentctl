from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.codex_runtime import detect_codex_runtime


class CodexRuntimeTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
