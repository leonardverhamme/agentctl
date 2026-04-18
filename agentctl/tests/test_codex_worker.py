from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import codex_worker


class CodexWorkerTests(unittest.TestCase):
    def _env(self, repo_root: Path) -> dict[str, str]:
        checklist_path = repo_root / "docs" / "ui-deep-audit-checklist.md"
        checklist_path.parent.mkdir(parents=True, exist_ok=True)
        checklist_path.write_text(
            "# Checklist\n\n- [ ] first item\n- [ ] second item\n",
            encoding="utf-8",
        )
        state_path = repo_root / ".codex-workflows" / "ui-deep-audit" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps({"status": "running", "tasks_open": 2}, indent=2) + "\n",
            encoding="utf-8",
        )
        progress_path = repo_root / "docs" / "ui-deep-audit-progress.md"
        progress_path.write_text("# Progress\n", encoding="utf-8")
        return {
            "CODEX_WORKFLOW_SKILL": "ui-deep-audit",
            "CODEX_WORKFLOW_REPO": str(repo_root),
            "CODEX_WORKFLOW_CHECKLIST": str(checklist_path),
            "CODEX_WORKFLOW_STATE": str(state_path),
            "CODEX_WORKFLOW_PROGRESS": str(progress_path),
            "CODEX_WORKFLOW_ITERATION": "3",
            "CODEX_WORKFLOW_RETRY_HINT": "Try another route.",
        }

    @mock.patch("codex_worker.subprocess.run")
    @mock.patch("codex_worker.detect_codex_runtime")
    def test_main_invokes_codex_exec_with_builtin_prompt(self, detect_runtime: mock.Mock, run_mock: mock.Mock) -> None:
        detect_runtime.return_value = {"callable": True, "path": "codex"}
        run_mock.return_value = mock.Mock(returncode=0, stdout="ok\n", stderr="")

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            with mock.patch.dict(os.environ, self._env(repo_root), clear=False):
                rc = codex_worker.main()

        self.assertEqual(rc, 0)
        command = run_mock.call_args.kwargs["args"] if "args" in run_mock.call_args.kwargs else run_mock.call_args.args[0]
        self.assertEqual(command[:3], ["codex", "exec", "--full-auto"])
        self.assertIn("--skip-git-repo-check", command)
        self.assertEqual(command[-1], "-")
        prompt = run_mock.call_args.kwargs["input"]
        self.assertIn("Use $ui-deep-audit.", prompt)
        self.assertIn("Try another route.", prompt)
        self.assertIn("Top remaining items:", prompt)
        self.assertIn("State snapshot:", prompt)

    @mock.patch("codex_worker.subprocess.run")
    @mock.patch("codex_worker.detect_codex_runtime")
    def test_main_omits_skip_git_repo_check_for_git_repos(self, detect_runtime: mock.Mock, run_mock: mock.Mock) -> None:
        detect_runtime.return_value = {"callable": True, "path": "codex"}
        run_mock.return_value = mock.Mock(returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / ".git").mkdir()
            with mock.patch.dict(os.environ, self._env(repo_root), clear=False):
                rc = codex_worker.main()

        self.assertEqual(rc, 0)
        command = run_mock.call_args.kwargs["args"] if "args" in run_mock.call_args.kwargs else run_mock.call_args.args[0]
        self.assertNotIn("--skip-git-repo-check", command)

    @mock.patch("codex_worker.detect_codex_runtime")
    def test_main_returns_126_when_runtime_is_not_callable(self, detect_runtime: mock.Mock) -> None:
        detect_runtime.return_value = {"callable": False, "call_detail": "Access is denied."}

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            with mock.patch.dict(os.environ, self._env(repo_root), clear=False):
                rc = codex_worker.main()

        self.assertEqual(rc, 126)


if __name__ == "__main__":
    unittest.main()
