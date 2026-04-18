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

    ci_path = repo / ".github" / "workflows" / "ci.yml"
    compose_path = repo / "automation-core" / "compose.yaml"
    dockerfile_path = repo / "automation-core" / "Dockerfile"

    results = [
        (
            "automation-core CI workflow exists and covers install, typecheck, build, and test",
            *file_contains(
                ci_path,
                "automation-core",
                "Install automation-core dependencies",
                "Typecheck automation-core",
                "Build automation-core",
                "Run automation-core tests",
            ),
        ),
        (
            "automation-core Docker runtime keeps the container restartable and health-checked",
            *file_contains(
                compose_path,
                "restart: unless-stopped",
                "healthcheck:",
            ),
        ),
        (
            "automation-core Docker image exposes a working runtime entrypoint",
            *file_contains(
                dockerfile_path,
                "CMD",
                "node",
            ),
        ),
        (
            "automation-core typecheck gate still passes",
            *run_command(repo, "npm --prefix automation-core run typecheck"),
        ),
        (
            "automation-core build gate still passes",
            *run_command(repo, "npm --prefix automation-core run build"),
        ),
        (
            "automation-core test gate still passes",
            *run_command(repo, "npm --prefix automation-core test"),
        ),
    ]

    checklist = [
        "# CI/CD Deep Audit Checklist",
        "",
        "## automation-core",
        "",
        *(checkbox(done, title, note) for title, done, note in results),
        "",
    ]
    checklist_path.parent.mkdir(parents=True, exist_ok=True)
    checklist_path.write_text("\n".join(checklist), encoding="utf-8")

    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["last_validation"] = {
        "worker": "cicd_deep_audit_worker",
        "items_checked": sum(1 for _, done, _ in results if done),
        "items_total": len(results),
    }
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
