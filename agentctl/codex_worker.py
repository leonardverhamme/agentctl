from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
WORKFLOW_TOOLS_DIR = CURRENT_DIR.parent / "workflow-tools"
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(WORKFLOW_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(WORKFLOW_TOOLS_DIR))

from lib.codex_runtime import detect_codex_runtime  # noqa: E402
from workflow_common import parse_checklist  # type: ignore  # noqa: E402


def _read_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"missing required environment variable: {name}")
    return value


def _text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _trim_block(text: str, *, limit: int = 6000) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n...[truncated]..."


def build_prompt() -> str:
    workflow = _read_env("CODEX_WORKFLOW_SKILL")
    repo_root = Path(_read_env("CODEX_WORKFLOW_REPO"))
    checklist_path = Path(_read_env("CODEX_WORKFLOW_CHECKLIST"))
    state_path = Path(_read_env("CODEX_WORKFLOW_STATE"))
    progress_path = Path(_read_env("CODEX_WORKFLOW_PROGRESS"))
    iteration = _read_env("CODEX_WORKFLOW_ITERATION")
    retry_hint = os.environ.get("CODEX_WORKFLOW_RETRY_HINT", "").strip()
    checklist = parse_checklist(checklist_path)
    checklist_text = _trim_block(_text_if_exists(checklist_path), limit=12000)
    state_text = _trim_block(_text_if_exists(state_path), limit=6000)
    progress_text = _trim_block(_text_if_exists(progress_path), limit=6000)

    remaining_titles = [item["title"] for item in checklist.get("remaining_items", [])[:12]]
    blocked_titles = [item["title"] for item in checklist.get("blocked_items", [])[:12]]
    remaining_lines = "\n".join(f"- {title}" for title in remaining_titles) or "- none listed"
    blocked_lines = "\n".join(f"- {title}" for title in blocked_titles) or "- none listed"

    return f"""Use ${workflow}.

You are running exactly one pass inside the shared deep-workflow loop for `{workflow}`.

Hard rules:
- Work from disk, not from chat memory.
- Trust `{checklist_path}` as the human queue and `{state_path}` as the machine queue.
- Re-open and use both files before making changes.
- If checklist and state disagree, repair the state by syncing it to the checklist before continuing.
- Do not stop at audit-only output or a progress summary.
- Complete one coherent, validated batch of work in this pass.
- Prefer 3 to 8 related checklist items when that is realistic.
- If the remaining work cleanly partitions, you may use subagents for independent batches inside this pass, then merge and validate.
- Update the checklist, state, and progress artifacts before exiting.
- Never mark the workflow ready unless the checklist is actually at zero unchecked items and the guard would pass.
- If items are genuinely blocked, leave them unchecked and record a concise blocker note instead of pretending they are done.

Context:
- Repo root: `{repo_root}`
- Workflow: `{workflow}`
- Iteration: `{iteration}`
- Checklist path: `{checklist_path}`
- State path: `{state_path}`
- Progress path: `{progress_path}`
- Current checklist counts: total={checklist.get("total", 0)}, done={checklist.get("done", 0)}, open={checklist.get("open", 0)}, blocked={checklist.get("blocked", 0)}

Top remaining items:
{remaining_lines}

Blocked items:
{blocked_lines}

Retry hint:
{retry_hint or "- none"}

Execution contract for this pass:
1. Read the checklist and state from disk.
2. Choose the next coherent batch from the remaining unchecked items.
3. Implement the fixes in the repo.
4. Run the smallest correct validations for that batch.
5. Update the checklist, progress notes, and machine state so the outer runner can continue.
6. Exit after one real batch, not after a plan-only note.

Checklist snapshot:
```markdown
{checklist_text or "# checklist file missing"}
```

State snapshot:
```json
{state_text or '{{}}'}
```

Progress snapshot:
```markdown
{progress_text or "# no progress file yet"}
```
"""


def main() -> int:
    runtime = detect_codex_runtime()
    if not runtime.get("callable"):
        detail = runtime.get("call_detail") or "Codex runtime is not callable"
        print(detail, file=sys.stderr)
        return 126

    repo_root = Path(_read_env("CODEX_WORKFLOW_REPO"))
    command = [str(runtime["path"]), "exec", "--full-auto"]
    if not (repo_root / ".git").exists():
        command.append("--skip-git-repo-check")
    command.append("-")

    prompt = build_prompt()
    result = subprocess.run(
        command,
        cwd=str(repo_root),
        input=prompt,
        text=True,
        capture_output=True,
        check=False,
        env=os.environ.copy(),
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
