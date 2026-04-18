from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.workflows import run_workflow, workflow_status


CLI_ENTRY = Path(__file__).resolve().parents[1] / "agentctl.py"
REPO_ROOT = Path(__file__).resolve().parents[2]
FAKE_WORKER = REPO_ROOT / "workflow-tools" / "tests" / "fake_worker.py"
DEEP_WORKFLOWS = [
    "ui-deep-audit",
    "test-deep-audit",
    "docs-deep-audit",
    "cicd-deep-audit",
    "refactor-deep-audit",
]


def write_fake_codex_cli(root: Path) -> Path:
    script_path = root / "fake_codex.py"
    script_path.write_text(
        """
import json
import os
import sys
from pathlib import Path


def write_checklist(path: Path, iteration: int) -> None:
    if iteration <= 1:
        path.write_text(
            "# Checklist\\n\\n## Status\\n\\n- Unchecked: 1\\n- Checked: 1\\n\\n- [x] first item\\n- [ ] second item\\n",
            encoding="utf-8",
        )
    else:
        path.write_text(
            "# Checklist\\n\\n## Status\\n\\n- Unchecked: 0\\n- Checked: 2\\n\\n- [x] first item\\n- [x] second item\\n",
            encoding="utf-8",
        )


def main() -> int:
    args = sys.argv[1:]
    if "--help" in args:
        print("fake codex help")
        return 0
    if args[:2] != ["exec", "--full-auto"] or args[-1] != "-":
        print("unexpected args: " + " ".join(args), file=sys.stderr)
        return 2
    _ = sys.stdin.read()
    state_path = Path(os.environ["CODEX_WORKFLOW_STATE"])
    checklist_path = Path(os.environ["CODEX_WORKFLOW_CHECKLIST"])
    iteration = int(os.environ["CODEX_WORKFLOW_ITERATION"])
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["last_validation"] = {"worker_mode": "fake-codex", "iteration": iteration}
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    write_checklist(checklist_path, iteration)
    print("fake codex exec")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
""".strip()
        + "\n",
        encoding="utf-8",
    )
    wrapper_path = root / "fake_codex.cmd"
    wrapper_path.write_text(
        f'@echo off\r\n"{sys.executable}" "{script_path}" %*\r\n',
        encoding="utf-8",
    )
    return wrapper_path


class WorkflowStatusTests(unittest.TestCase):
    def test_status_reads_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            state_path = repo_root / ".codex-workflows" / "ui-deep-audit" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "workflow_name": "ui-deep-audit",
                        "skill_name": "ui-deep-audit",
                        "repo_root": str(repo_root),
                        "checklist_path": str(repo_root / "docs" / "ui-deep-audit-checklist.md"),
                        "progress_path": str(repo_root / "docs" / "ui-deep-audit-progress.md"),
                        "status": "running",
                        "iteration": 1,
                        "max_iterations": 30,
                        "stagnant_iterations": 0,
                        "max_stagnant_iterations": 3,
                        "tasks_total": 2,
                        "tasks_done": 1,
                        "tasks_open": 1,
                        "tasks_blocked": 0,
                        "last_batch": [],
                        "last_validation": {},
                        "last_error": {},
                        "ready_allowed": False,
                        "remaining_items": [],
                        "blocked_items": [],
                        "evidence": [],
                    }
                ),
                encoding="utf-8",
            )
            result = workflow_status(repo=str(repo_root), use_registry=False)
            self.assertEqual(result["summary"]["status"], "ok")
            self.assertEqual(result["workflows"][0]["schema_version"], 1)

    def test_status_flags_complete_without_ready_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            state_path = repo_root / ".codex-workflows" / "ui-deep-audit" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "workflow_name": "ui-deep-audit",
                        "skill_name": "ui-deep-audit",
                        "repo_root": str(repo_root),
                        "checklist_path": str(repo_root / "docs" / "ui-deep-audit-checklist.md"),
                        "progress_path": str(repo_root / "docs" / "ui-deep-audit-progress.md"),
                        "status": "complete",
                        "iteration": 1,
                        "max_iterations": 30,
                        "stagnant_iterations": 0,
                        "max_stagnant_iterations": 3,
                        "tasks_total": 1,
                        "tasks_done": 1,
                        "tasks_open": 0,
                        "tasks_blocked": 0,
                        "last_batch": [],
                        "last_validation": {},
                        "last_error": {},
                        "ready_allowed": False,
                        "remaining_items": [],
                        "blocked_items": [],
                        "evidence": [],
                    }
                ),
                encoding="utf-8",
            )
            result = workflow_status(repo=str(repo_root), use_registry=False)
            self.assertEqual(result["summary"]["status"], "error")
            self.assertIn("ready_allowed=true", result["workflows"][0]["errors"][0])

    def test_registry_hides_ephemeral_history_from_active_workflows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry.json"
            durable_repo = Path(temp_dir) / "repo"
            durable_state = durable_repo / ".codex-workflows" / "agentctl-maintenance" / "state.json"
            durable_state.parent.mkdir(parents=True, exist_ok=True)
            durable_state.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "workflow_name": "agentctl-maintenance",
                        "skill_name": "agentctl-maintenance-engineer",
                        "repo_root": str(durable_repo),
                        "checklist_path": str(durable_repo / "docs" / "maintenance.md"),
                        "progress_path": str(durable_repo / "docs" / "maintenance-report.json"),
                        "status": "complete",
                        "iteration": 1,
                        "max_iterations": 1,
                        "stagnant_iterations": 0,
                        "max_stagnant_iterations": 1,
                        "tasks_total": 1,
                        "tasks_done": 1,
                        "tasks_open": 0,
                        "tasks_blocked": 0,
                        "last_batch": [],
                        "last_validation": {},
                        "last_error": {},
                        "ready_allowed": True,
                        "remaining_items": [],
                        "blocked_items": [],
                        "evidence": [],
                    }
                ),
                encoding="utf-8",
            )
            registry_path.write_text(
                json.dumps(
                    {
                        f"{durable_repo}::agentctl-maintenance": {
                            "workflow_name": "agentctl-maintenance",
                            "skill_name": "agentctl-maintenance-engineer",
                            "repo_root": str(durable_repo),
                            "status": "complete",
                        },
                        "C:\\Users\\leona\\AppData\\Local\\Temp\\tmp123::ui-deep-audit": {
                            "workflow_name": "ui-deep-audit",
                            "skill_name": "ui-deep-audit",
                            "repo_root": "C:\\Users\\leona\\AppData\\Local\\Temp\\tmp123",
                            "status": "error",
                        },
                    }
                ),
                encoding="utf-8",
            )

            ephemeral_repo = "C:\\Users\\leona\\AppData\\Local\\Temp\\tmp123"
            with mock.patch("lib.workflows.WORKFLOW_REGISTRY_PATH", registry_path), mock.patch(
                "lib.workflows._is_ephemeral_repo",
                side_effect=lambda repo_root: str(repo_root) == ephemeral_repo,
            ):
                result = workflow_status(repo=None, use_registry=True)

        self.assertEqual(result["summary"]["status"], "ok")
        self.assertEqual(result["summary"]["count"], 1)
        self.assertEqual(result["summary"]["historical_count"], 1)
        self.assertEqual(result["workflows"][0]["workflow_name"], "agentctl-maintenance")

    @mock.patch("lib.workflows.subprocess.run")
    @mock.patch("lib.workflows.resolve_codex_worker_command")
    def test_run_workflow_uses_codex_template_in_auto_mode(self, resolve_codex_worker_command: mock.Mock, run_mock: mock.Mock) -> None:
        resolve_codex_worker_command.return_value = "codex-template-worker"
        run_mock.return_value = mock.Mock(returncode=0)
        with tempfile.TemporaryDirectory() as temp_dir:
            rc = run_workflow(
                workflow="ui-deep-audit",
                repo=temp_dir,
                checklist=None,
                progress=None,
                worker_command=None,
                worker_mode="auto",
                max_iterations=30,
                max_stagnant=3,
            )

        self.assertEqual(rc, 0)
        resolve_codex_worker_command.assert_called_once()
        resolver_kwargs = resolve_codex_worker_command.call_args.kwargs
        self.assertEqual(resolver_kwargs["workflow"], "ui-deep-audit")
        self.assertEqual(Path(resolver_kwargs["repo_root"]).resolve(), Path(temp_dir).resolve())
        self.assertTrue(str(resolver_kwargs["state_path"]).endswith(".codex-workflows\\ui-deep-audit\\state.json") or str(resolver_kwargs["state_path"]).endswith(".codex-workflows/ui-deep-audit/state.json"))
        command = run_mock.call_args.args[0]
        self.assertIn("--worker-command", command)
        self.assertIn("codex-template-worker", command)
        self.assertIn("--worker-mode", command)
        self.assertIn("auto", command)

    @mock.patch("lib.workflows.subprocess.run")
    @mock.patch("lib.workflows.resolve_codex_worker_command")
    def test_run_workflow_keeps_explicit_worker_command(self, resolve_codex_worker_command: mock.Mock, run_mock: mock.Mock) -> None:
        resolve_codex_worker_command.return_value = "ignored-template"
        run_mock.return_value = mock.Mock(returncode=0)
        with tempfile.TemporaryDirectory() as temp_dir:
            rc = run_workflow(
                workflow="test-deep-audit",
                repo=temp_dir,
                checklist=None,
                progress=None,
                worker_command="explicit-worker",
                worker_mode="codex",
                max_iterations=30,
                max_stagnant=3,
            )

        self.assertEqual(rc, 0)
        command = run_mock.call_args.args[0]
        self.assertIn("explicit-worker", command)
        self.assertNotIn("ignored-template", command)

    def test_cli_run_completes_end_to_end_with_fake_worker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            env = os.environ.copy()
            env["CODEX_HOME"] = str(REPO_ROOT)
            worker_command = f'"{sys.executable}" "{FAKE_WORKER}" complete_after_two'

            run_result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_ENTRY),
                    "run",
                    "ui-deep-audit",
                    "--repo",
                    str(repo_root),
                    "--worker-command",
                    worker_command,
                    "--worker-mode",
                    "explicit",
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(run_result.returncode, 0, run_result.stderr or run_result.stdout)

            status_result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_ENTRY),
                    "status",
                    "--repo",
                    str(repo_root),
                    "--json",
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(status_result.returncode, 0, status_result.stderr or status_result.stdout)
            payload = json.loads(status_result.stdout)
            self.assertEqual(payload["workflows"][0]["status"], "complete")
            self.assertTrue(payload["workflows"][0]["ready_allowed"])

    def test_cli_run_stalls_end_to_end_with_fake_worker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            env = os.environ.copy()
            env["CODEX_HOME"] = str(REPO_ROOT)
            worker_command = f'"{sys.executable}" "{FAKE_WORKER}" stall'

            run_result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_ENTRY),
                    "run",
                    "docs-deep-audit",
                    "--repo",
                    str(repo_root),
                    "--worker-command",
                    worker_command,
                    "--worker-mode",
                    "explicit",
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(run_result.returncode, 2, run_result.stderr or run_result.stdout)

            status_result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_ENTRY),
                    "status",
                    "--repo",
                    str(repo_root),
                    "--json",
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(status_result.returncode, 0, status_result.stderr or status_result.stdout)
            payload = json.loads(status_result.stdout)
            self.assertEqual(payload["workflows"][0]["status"], "stalled")
            self.assertFalse(payload["workflows"][0]["ready_allowed"])

    def test_cli_run_blocks_end_to_end_with_fake_worker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            env = os.environ.copy()
            env["CODEX_HOME"] = str(REPO_ROOT)
            worker_command = f'"{sys.executable}" "{FAKE_WORKER}" blocked'

            run_result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_ENTRY),
                    "run",
                    "cicd-deep-audit",
                    "--repo",
                    str(repo_root),
                    "--worker-command",
                    worker_command,
                    "--worker-mode",
                    "explicit",
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(run_result.returncode, 2, run_result.stderr or run_result.stdout)

            status_result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_ENTRY),
                    "status",
                    "--repo",
                    str(repo_root),
                    "--json",
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(status_result.returncode, 0, status_result.stderr or status_result.stdout)
            payload = json.loads(status_result.stdout)
            self.assertEqual(payload["workflows"][0]["status"], "blocked")
            self.assertFalse(payload["workflows"][0]["ready_allowed"])

    def test_cli_run_completes_all_supported_deep_workflows_with_fake_worker(self) -> None:
        env = os.environ.copy()
        env["CODEX_HOME"] = str(REPO_ROOT)
        worker_command = f'"{sys.executable}" "{FAKE_WORKER}" complete_after_two'

        for workflow in DEEP_WORKFLOWS:
            with self.subTest(workflow=workflow), tempfile.TemporaryDirectory() as temp_dir:
                repo_root = Path(temp_dir)
                run_result = subprocess.run(
                    [
                        sys.executable,
                        str(CLI_ENTRY),
                        "run",
                        workflow,
                        "--repo",
                        str(repo_root),
                        "--worker-command",
                        worker_command,
                        "--worker-mode",
                        "explicit",
                    ],
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                    check=False,
                    env=env,
                )
                self.assertEqual(run_result.returncode, 0, run_result.stderr or run_result.stdout)

                status_result = subprocess.run(
                    [
                        sys.executable,
                        str(CLI_ENTRY),
                        "status",
                        "--repo",
                        str(repo_root),
                        "--json",
                    ],
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                    check=False,
                    env=env,
                )
                self.assertEqual(status_result.returncode, 0, status_result.stderr or status_result.stdout)
                payload = json.loads(status_result.stdout)
                workflow_record = payload["workflows"][0]
                self.assertEqual(workflow_record["workflow_name"], workflow)
                self.assertEqual(workflow_record["status"], "complete")
                self.assertTrue(workflow_record["ready_allowed"])
                self.assertTrue(Path(workflow_record["state_path"]).exists())
                self.assertTrue(Path(workflow_record["checklist_path"]).exists())
                self.assertTrue(
                    str(workflow_record["checklist_path"]).endswith(f"docs\\{workflow}-checklist.md")
                    or str(workflow_record["checklist_path"]).endswith(f"docs/{workflow}-checklist.md")
                )

    def test_cli_run_uses_template_worker_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            env = os.environ.copy()
            env["CODEX_HOME"] = str(REPO_ROOT)
            env["AGENTCTL_CODEX_WORKER_TEMPLATE"] = f'"{sys.executable}" "{FAKE_WORKER}" complete_after_two'

            run_result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_ENTRY),
                    "run",
                    "ui-deep-audit",
                    "--repo",
                    str(repo_root),
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(run_result.returncode, 0, run_result.stderr or run_result.stdout)

            state = json.loads(
                (repo_root / ".codex-workflows" / "ui-deep-audit" / "state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["status"], "complete")
            self.assertTrue(state["ready_allowed"])
            self.assertEqual(state["worker_mode"], "auto")
            self.assertIn("complete_after_two", state["worker_command"])

    def test_cli_run_uses_formatted_template_worker_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            env = os.environ.copy()
            env["CODEX_HOME"] = str(REPO_ROOT)
            env["AGENTCTL_CODEX_WORKER_TEMPLATE"] = '{python_q} "' + str(FAKE_WORKER) + '" complete_after_two'

            run_result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_ENTRY),
                    "run",
                    "docs-deep-audit",
                    "--repo",
                    str(repo_root),
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(run_result.returncode, 0, run_result.stderr or run_result.stdout)

            state = json.loads(
                (repo_root / ".codex-workflows" / "docs-deep-audit" / "state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["status"], "complete")
            self.assertTrue(state["ready_allowed"])
            self.assertIn(str(Path(sys.executable)), state["worker_command"])

    def test_cli_run_uses_builtin_codex_worker_wrapper_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as tool_dir:
            repo_root = Path(temp_dir)
            fake_codex = write_fake_codex_cli(Path(tool_dir))
            env = os.environ.copy()
            env["CODEX_HOME"] = str(REPO_ROOT)
            env["AGENTCTL_CODEX_PATH"] = str(fake_codex)
            env.pop("AGENTCTL_CODEX_WORKER_TEMPLATE", None)
            env.pop("CODEX_WORKFLOW_WORKER_COMMAND", None)

            run_result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_ENTRY),
                    "run",
                    "ui-deep-audit",
                    "--repo",
                    str(repo_root),
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(run_result.returncode, 0, run_result.stderr or run_result.stdout)
            state = json.loads(
                (repo_root / ".codex-workflows" / "ui-deep-audit" / "state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["status"], "complete")
            self.assertTrue(state["ready_allowed"])
            self.assertEqual(state["worker_mode"], "auto")
            self.assertIn("codex_worker.py", state["worker_command"])

    def test_cli_run_without_worker_command_fails_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            docs_dir = repo_root / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)
            (docs_dir / "ui-deep-audit-checklist.md").write_text("- [ ] Smoke item\n", encoding="utf-8")
            env = os.environ.copy()
            env["CODEX_HOME"] = str(REPO_ROOT)
            env.pop("CODEX_WORKFLOW_WORKER_COMMAND", None)
            env.pop("AGENTCTL_CODEX_WORKER_TEMPLATE", None)
            env.pop("AGENTCTL_CODEX_PATH", None)
            env["APPDATA"] = str(repo_root / "missing-appdata")
            env["PATH"] = ""

            run_result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_ENTRY),
                    "run",
                    "ui-deep-audit",
                    "--repo",
                    str(repo_root),
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(run_result.returncode, 2, run_result.stderr or run_result.stdout)
            self.assertIn("no worker command configured", run_result.stdout + run_result.stderr)

            state = json.loads(
                (repo_root / ".codex-workflows" / "ui-deep-audit" / "state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["status"], "blocked")
            self.assertFalse(state["ready_allowed"])
            self.assertEqual(state["worker_mode"], "auto")


if __name__ == "__main__":
    unittest.main()
