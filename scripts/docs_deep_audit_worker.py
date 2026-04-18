from __future__ import annotations

import json
import os
from pathlib import Path


def check_contains(path: Path, *needles: str) -> tuple[bool, str]:
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

    root_readme = repo / "README.md"
    automation_readme = repo / "automation-core" / "README.md"
    operator_doc = repo / "docs" / "automation-core.md"

    results = [
        (
            "Root README documents the automation-core surface and operator flow",
            *check_contains(
                root_readme,
                "automation-core",
                "docs/automation-core.md",
                "npm run cli -- job gmail-sync",
            ),
        ),
        (
            "automation-core README documents architecture, API endpoints, and automation mapping",
            *check_contains(
                automation_readme,
                "## Architecture",
                "## HTTP API",
                "## Codex automation mapping",
            ),
        ),
        (
            "Operator guide captures data sources, approval flow, and troubleshooting",
            *check_contains(
                operator_doc,
                "## Notion data sources",
                "## Approval model",
                "## Troubleshooting",
            ),
        ),
    ]

    checklist = [
        "# Docs Deep Audit Checklist",
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
        "worker": "docs_deep_audit_worker",
        "items_checked": sum(1 for _, done, _ in results if done),
        "items_total": len(results),
    }
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
