from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def run_command(repo: Path, command: str) -> tuple[bool, str]:
    result = subprocess.run(
        command,
        cwd=str(repo),
        shell=True,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True, command
    tail = (result.stderr or result.stdout)[-500:]
    return False, f"{command} failed: {tail}"


def file_contains(path: Path, *needles: str) -> tuple[bool, str]:
    if not path.exists():
        return False, f"Missing file: {path}"
    content = path.read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in content]
    if missing:
        return False, f"Missing expected content in {path.name}: {', '.join(missing)}"
    return True, f"Validated {path.name}"


def checkbox(done: bool, title: str, note: str) -> str:
    marker = "x" if done else " "
    if done:
        return f"- [{marker}] {title}\n  Verified: {note}"
    return f"- [{marker}] {title}\n  Blocked: {note}"


def main() -> int:
    repo = Path(os.environ["CODEX_WORKFLOW_REPO"]).resolve()
    checklist_path = Path(os.environ["CODEX_WORKFLOW_CHECKLIST"]).resolve()
    state_path = Path(os.environ["CODEX_WORKFLOW_STATE"]).resolve()

    render_path = repo / "automation-core" / "src" / "web" / "render.ts"
    app_test_path = repo / "automation-core" / "tests" / "app.test.ts"

    results = [
        (
            "Dashboard shell uses a dense operator-console structure with semantic landmarks",
            *file_contains(
                render_path,
                '<header class="panel topbar">',
                '<main class="workspace">',
                'aria-label="Queue overview"',
                'aria-label="Decision queues"',
            ),
        ),
        (
            "Queue lanes show proposal metadata and structured field-level diffs",
            *file_contains(
                render_path,
                'renderDiffTable',
                'Proposed changes',
                'detail-grid',
                'Read gate',
            ),
        ),
        (
            "UI tokens favor compact controls, restrained surfaces, and explicit focus states",
            *file_contains(
                render_path,
                ":focus-visible",
                "border-radius: 8px",
                "surface-subtle",
                "status-pill",
            ),
        ),
        (
            "Root route regression coverage verifies the operator console HTML",
            *file_contains(
                app_test_path,
                'url: "/"',
                "Operator console",
                "Proposed changes",
                "Open Gmail",
            ),
        ),
        (
            "automation-core typechecks",
            *run_command(repo, "npm --prefix automation-core run typecheck"),
        ),
        (
            "automation-core builds cleanly",
            *run_command(repo, "npm --prefix automation-core run build"),
        ),
        (
            "automation-core tests pass after the UI audit",
            *run_command(repo, "npm --prefix automation-core test"),
        ),
    ]

    checklist = [
        "# UI Deep Audit Checklist",
        "",
        "## automation-core operator console",
        "",
        *(checkbox(done, title, note) for title, done, note in results),
        "",
    ]
    checklist_path.parent.mkdir(parents=True, exist_ok=True)
    checklist_path.write_text("\n".join(checklist), encoding="utf-8")

    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["last_validation"] = {
        "worker": "ui_deep_audit_worker",
        "items_checked": sum(1 for _, done, _ in results if done),
        "items_total": len(results),
    }
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
