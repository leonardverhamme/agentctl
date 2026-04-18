from __future__ import annotations

import json
import os
import site
import sys
import tomllib
from pathlib import Path
from typing import Any

from .codex_runtime import detect_codex_runtime
from .common import command_path, print_json, run_command, utc_now
from .paths import AGENTCTL_CAPABILITIES_DOCS_DIR, CONFIG_PATH, PLAYWRIGHT_WRAPPER, PLAYWRIGHT_WRAPPER_CMD, SKILLS_DIR


CAPABILITY_SPECS: list[dict[str, Any]] = [
    {
        "key": "autonomous-deep-runs",
        "label": "Autonomous deep runs",
        "group": "control-plane",
        "required": True,
        "front_door": "agentctl run",
        "entrypoints": ["agentctl run <workflow>", "CODEX_WORKFLOW_WORKER_COMMAND", "AGENTCTL_CODEX_WORKER_TEMPLATE"],
        "skills": [],
        "interfaces": ["tool:codex"],
        "availability_mode": "all",
        "overlap_policy": "The outer execute-until-done loop must use a real worker command, not chat memory. Prefer Codex runtime when it is callable or explicitly templated.",
    },
    {
        "key": "skills-management",
        "label": "Skills management",
        "group": "control-plane",
        "required": True,
        "front_door": "agentctl skills",
        "entrypoints": ["agentctl skills list", "agentctl skills add", "agentctl skills check", "agentctl skills update"],
        "skills": [],
        "interfaces": ["tool:skills", "tool:npx"],
        "availability_mode": "all",
        "overlap_policy": "Wrap official skills tooling rather than reimplementing it.",
    },
    {
        "key": "agentctl-maintenance",
        "label": "Agentctl maintenance",
        "group": "control-plane",
        "required": True,
        "front_door": "$agentctl-maintenance-engineer",
        "entrypoints": ["agentctl maintenance check", "agentctl maintenance audit", "agentctl maintenance fix-docs"],
        "skills": ["agentctl-maintenance-engineer"],
        "interfaces": ["plugin:agentctl"],
        "availability_mode": "all",
        "overlap_policy": "Keep maintenance as one capability surface for docs, packaging, registry health, and platform drift.",
    },
    {
        "key": "context-workflows",
        "label": "Repo context workflows",
        "group": "workflow-skills",
        "required": True,
        "front_door": "$context-skill",
        "entrypoints": ["$context-skill"],
        "skills": ["context-skill"],
        "interfaces": [],
        "availability_mode": "all",
        "overlap_policy": "Prefer the lightweight context skill and durable repo docs over deeper automation.",
    },
    {
        "key": "ui-workflows",
        "label": "UI workflows",
        "group": "workflow-skills",
        "required": True,
        "front_door": "$ui-skill / $ui-deep-audit",
        "entrypoints": ["$ui-skill", "$ui-deep-audit", "agentctl run ui-deep-audit"],
        "skills": ["ui-skill", "ui-deep-audit"],
        "interfaces": [],
        "availability_mode": "all",
        "overlap_policy": "Surface the UI skills first; plugin support stays a backing capability, not a separate menu.",
    },
    {
        "key": "test-workflows",
        "label": "Testing workflows",
        "group": "workflow-skills",
        "required": True,
        "front_door": "$test-skill / $test-deep-audit",
        "entrypoints": ["$test-skill", "$test-deep-audit", "agentctl run test-deep-audit"],
        "skills": ["test-skill", "test-deep-audit"],
        "interfaces": [],
        "availability_mode": "any",
        "overlap_policy": "Collapse testing transports behind one testing surface; use repo-native CLIs and Playwright first.",
    },
    {
        "key": "docs-workflows",
        "label": "Documentation workflows",
        "group": "workflow-skills",
        "required": True,
        "front_door": "$docs-skill / $docs-deep-audit",
        "entrypoints": ["$docs-skill", "$docs-deep-audit", "agentctl run docs-deep-audit"],
        "skills": ["docs-skill", "docs-deep-audit"],
        "interfaces": [],
        "availability_mode": "all",
        "overlap_policy": "Keep docs work in the docs skills and hide transport details entirely.",
    },
    {
        "key": "refactor-workflows",
        "label": "Refactor workflows",
        "group": "workflow-skills",
        "required": True,
        "front_door": "$refactor-skill / $refactor-deep-audit",
        "entrypoints": ["$refactor-skill", "$refactor-deep-audit", "$refactor-orchestrator", "agentctl run refactor-deep-audit"],
        "skills": ["refactor-skill", "refactor-deep-audit", "refactor-orchestrator"],
        "interfaces": [],
        "availability_mode": "all",
        "overlap_policy": "Use the local refactor skills as the capability surface; do not split by underlying tooling.",
    },
    {
        "key": "cicd-workflows",
        "label": "CI/CD workflows",
        "group": "workflow-skills",
        "required": True,
        "front_door": "$cicd-skill / $cicd-deep-audit",
        "entrypoints": ["$cicd-skill", "$cicd-deep-audit", "agentctl run cicd-deep-audit"],
        "skills": ["cicd-skill", "cicd-deep-audit"],
        "interfaces": [],
        "availability_mode": "all",
        "overlap_policy": "Surface CI/CD by workflow, not by whether GitHub or Vercel provides the underlying route.",
    },
    {
        "key": "research",
        "label": "Research",
        "group": "research-and-verification",
        "required": True,
        "front_door": "agentctl research",
        "entrypoints": ["agentctl research web", "agentctl research github", "agentctl research scout"],
        "skills": ["internet-researcher", "github-researcher", "web-github-scout"],
        "interfaces": [],
        "availability_mode": "any",
        "overlap_policy": "Hide web, GitHub, and browser transport choices behind one research surface and one evidence contract.",
    },
    {
        "key": "github-workflows",
        "label": "GitHub workflows",
        "group": "integrations",
        "required": False,
        "front_door": "$github-capability",
        "entrypoints": ["$github-capability", "agentctl capability github-workflows", "$github:github", "$github:gh-fix-ci", "$github:gh-address-comments", "gh"],
        "skills": ["github-capability"],
        "interfaces": ["plugin:github@openai-curated", "tool:gh"],
        "availability_mode": "any",
        "overlap_policy": "Collapse GitHub plugin skills and gh into one capability entry instead of separate transport menus.",
        "summary": "Use for repositories, pull requests, issues, release history, and Actions triage.",
        "routing_notes": [
            "Prefer the GitHub capability skill when you need a quick route decision before acting.",
            "Use the GitHub plugin skills when they cover the task directly; use `gh` for direct CLI workflows and gaps in plugin coverage.",
        ],
    },
    {
        "key": "github-advanced-security",
        "label": "GitHub Advanced Security",
        "group": "integrations",
        "required": False,
        "front_door": "$github-security-capability",
        "entrypoints": [
            "$github-security-capability",
            "agentctl capability github-advanced-security",
            "ghas-cli",
            "gh codeql",
            "gh api",
        ],
        "skills": ["github-security-capability"],
        "interfaces": ["tool:gh", "tool:gh-codeql", "tool:ghas-cli", "plugin:github@openai-curated"],
        "availability_mode": "any",
        "overlap_policy": "Use `gh api` and `gh codeql` as the authoritative GitHub security routes, with `ghas-cli` as the rollout-at-scale helper when it is healthy. Do not assume generic GitHub plugin skills cover GHAS-specific work.",
        "summary": "Use for GHAS rollout, CodeQL, code scanning alerts, secret scanning alerts, Dependabot alerts, dependency review, security overview, and organization-scale security automation.",
        "routing_notes": [
            "Prefer `ghas-cli` for GHAS enablement and rollout work across many repositories when it is callable.",
            "Prefer `gh codeql` for local CodeQL CLI management, version pinning, and query workflows.",
            "Prefer `gh api` for alert inspection and targeted automation against code scanning, secret scanning, Dependabot, and dependency review endpoints.",
            "No installed GitHub plugin skill currently provides GHAS-specific workflow coverage, so route security work through this capability instead of generic GitHub skills.",
            "Useful community extensions exist, such as `advanced-security/gh-codeql-scan`, `GitHubSecurityLab/gh-mrva`, `CallMeGreg/gh-secret-scanning`, and `securesauce/gh-alerts`, but they are optional extras rather than agentctl defaults.",
        ],
    },
    {
        "key": "browser-automation",
        "label": "Browser automation",
        "group": "research-and-verification",
        "required": False,
        "front_door": "$browser-capability",
        "entrypoints": ["$browser-capability", "agentctl capability browser-automation", "$playwright", "playwright.cmd", "Playwright MCP"],
        "skills": ["browser-capability", "playwright"],
        "interfaces": ["tool:playwright", "mcp:playwright", "plugin:vercel@openai-curated"],
        "availability_mode": "any",
        "overlap_policy": "Treat Playwright CLI and MCP as peer browser backends behind one browser capability.",
        "summary": "Use for real browser automation, screenshots, runtime UI verification, and dynamic-site inspection.",
        "routing_notes": [
            "Prefer Playwright CLI when a terminal-driven browser route is enough.",
            "Use Playwright MCP when the structured MCP browser path gives a better interface for the task.",
        ],
    },
    {
        "key": "vercel-platform",
        "label": "Vercel platform",
        "group": "integrations",
        "required": False,
        "front_door": "$vercel-capability",
        "entrypoints": ["$vercel-capability", "agentctl capability vercel-platform", "$vercel:vercel-cli", "$vercel:deployments-cicd", "vercel"],
        "skills": ["vercel-capability"],
        "interfaces": ["plugin:vercel@openai-curated", "tool:vercel", "mcp:com-vercel-vercel-mcp", "mcp:vercel-remote"],
        "availability_mode": "any",
        "overlap_policy": "Keep one Vercel capability entry; plugin and CLI are primary, MCP stays background metadata.",
        "summary": "Use for deployments, project linking, env vars, logs, domains, and Vercel platform operations.",
        "routing_notes": [
            "Prefer Vercel plugin skills for guided workflows already packaged in Codex.",
            "Use the Vercel CLI for direct project operations and deployment commands.",
        ],
    },
    {
        "key": "supabase-data",
        "label": "Supabase data",
        "group": "integrations",
        "required": False,
        "front_door": "$supabase-capability",
        "entrypoints": ["$supabase-capability", "agentctl capability supabase-data", "supabase", "Supabase MCP"],
        "skills": ["supabase-capability"],
        "interfaces": ["tool:supabase", "mcp:supabase", "mcp:supabase-remote"],
        "availability_mode": "any",
        "overlap_policy": "Prefer the Supabase CLI for local stack, schema, migrations, and CI/CD. Use MCP when structured project access adds value beyond the CLI.",
        "summary": "Use for local Supabase stacks, migrations, database workflows, platform deploy steps, and Supabase project operations.",
        "routing_notes": [
            "CLI-first: `supabase init` and `supabase start` are the default local-development path.",
            "Do not rely on `npm install -g supabase`; prefer Scoop, Homebrew, standalone binaries, or `npx supabase`.",
            "If running via `npx`, require Node.js 20 or later.",
            "Local Supabase development expects a Docker-compatible container runtime.",
        ],
    },
    {
        "key": "stripe-payments",
        "label": "Stripe payments",
        "group": "integrations",
        "required": False,
        "front_door": "$stripe-capability",
        "entrypoints": ["$stripe-capability", "agentctl capability stripe-payments", "$stripe:stripe-best-practices", "$stripe:upgrade-stripe"],
        "skills": ["stripe-capability"],
        "interfaces": ["plugin:stripe@openai-curated", "mcp:stripe"],
        "availability_mode": "any",
        "overlap_policy": "Prefer the Stripe plugin capability surface; keep MCP as backing metadata, not a separate menu.",
        "summary": "Use for payment flows, subscriptions, Connect/platform work, and Stripe integration reviews.",
        "routing_notes": [
            "Prefer the Stripe plugin skills for guided Stripe decisions and upgrade work.",
            "Use the capability page to see whether plugin coverage is enough before dropping into lower-level tooling.",
        ],
    },
    {
        "key": "sentry-observability",
        "label": "Sentry observability",
        "group": "integrations",
        "required": False,
        "front_door": "$sentry-capability",
        "entrypoints": ["$sentry-capability", "agentctl capability sentry-observability", "$sentry:sentry"],
        "skills": ["sentry-capability"],
        "interfaces": ["plugin:sentry@openai-curated"],
        "availability_mode": "all",
        "overlap_policy": "Expose Sentry as one observability capability instead of a transport-specific tool entry.",
        "summary": "Use for production error inspection, event review, and Sentry-backed observability checks.",
        "routing_notes": [
            "Use the Sentry capability when the task starts from a production issue or error event.",
        ],
    },
    {
        "key": "ios-development",
        "label": "iOS development",
        "group": "integrations",
        "required": False,
        "front_door": "Build iOS Apps plugin",
        "entrypoints": ["$build-ios-apps:ios-debugger-agent", "$build-ios-apps:swiftui-ui-patterns"],
        "skills": [],
        "interfaces": ["plugin:build-ios-apps@openai-curated"],
        "availability_mode": "all",
        "overlap_policy": "Expose iOS build, UI, and debugging workflows as one capability backed by the iOS plugin.",
    },
    {
        "key": "macos-development",
        "label": "macOS development",
        "group": "integrations",
        "required": False,
        "front_door": "Build macOS Apps plugin",
        "entrypoints": ["$build-macos-apps:build-run-debug", "$build-macos-apps:swiftui-patterns"],
        "skills": [],
        "interfaces": ["plugin:build-macos-apps@openai-curated"],
        "availability_mode": "all",
        "overlap_policy": "Expose macOS build, packaging, and desktop debugging as one capability backed by the macOS plugin.",
    },
    {
        "key": "android-testing",
        "label": "Android testing",
        "group": "integrations",
        "required": False,
        "front_door": "Test Android Apps plugin",
        "entrypoints": ["$test-android-apps:android-emulator-qa"],
        "skills": [],
        "interfaces": ["plugin:test-android-apps@openai-curated"],
        "availability_mode": "all",
        "overlap_policy": "Expose Android emulator QA as one capability backed by the Android testing plugin.",
    },
    {
        "key": "figma-design",
        "label": "Figma design",
        "group": "integrations",
        "required": False,
        "front_door": "$figma-capability",
        "entrypoints": ["$figma-capability", "agentctl capability figma-design", "Figma MCP"],
        "skills": ["figma-capability"],
        "interfaces": ["mcp:figma"],
        "availability_mode": "all",
        "overlap_policy": "No plugin overlap here, so MCP remains the single capability entry.",
        "summary": "Use for Figma design context, code-connect, design system search, and direct Figma edits via MCP.",
        "routing_notes": [
            "Figma is MCP-backed here; use the capability page to see the supported operations before editing design files.",
        ],
    },
    {
        "key": "nextjs-runtime",
        "label": "Next.js runtime",
        "group": "integrations",
        "required": False,
        "front_door": "$nextjs-runtime-capability",
        "entrypoints": ["$nextjs-runtime-capability", "agentctl capability nextjs-runtime", "Next DevTools MCP"],
        "skills": ["nextjs-runtime-capability"],
        "interfaces": ["mcp:next-devtools"],
        "availability_mode": "all",
        "overlap_policy": "Keep Next.js runtime tooling as one capability entry backed by Next DevTools MCP.",
        "summary": "Use for live Next.js dev-server diagnostics, route introspection, and runtime/build error inspection.",
        "routing_notes": [
            "Prefer Next DevTools MCP over generic browser logs when the task is specifically about a running Next.js app.",
        ],
    },
]

GROUP_LABELS = {
    "control-plane": "Control plane",
    "workflow-skills": "Workflow skills",
    "research-and-verification": "Research and verification",
    "integrations": "Integrations",
}

CAPABILITY_CLOUD_READINESS = {
    "autonomous-deep-runs": [],
    "skills-management": ["skills wrapper layer"],
    "agentctl-maintenance": ["agentctl core"],
    "research": ["research web", "research github", "research scout"],
    "browser-automation": ["Playwright CLI", "Playwright MCP"],
    "github-workflows": ["gh"],
    "github-advanced-security": ["gh", "gh-codeql", "ghas-cli"],
    "vercel-platform": ["vercel"],
    "supabase-data": ["supabase"],
    "stripe-payments": [],
    "sentry-observability": [],
    "figma-design": [],
    "nextjs-runtime": [],
}

REQUIRED_TOOL_NAMES = {"python", "npx", "skills"}


def _tool_record(name: str, *, command: str, version_args: list[str], auth_args: list[str] | None = None, detect_only: bool = False) -> dict[str, Any]:
    path = command_path(command)
    record: dict[str, Any] = {
        "name": name,
        "command": command,
        "path": path,
        "installed": bool(path),
        "detect_only": detect_only,
        "version": None,
        "auth": "unknown",
        "status": "missing",
    }
    if not path:
        return record

    version_result = run_command([command, *version_args], timeout=20)
    if version_result["ok"]:
        version_text = version_result["stdout"] or version_result["stderr"]
        record["version"] = version_text.splitlines()[0] if version_text else None
        record["status"] = "ok"
    else:
        record["status"] = "degraded"
        record["version_error"] = version_result["stderr"]

    if auth_args:
        auth_result = run_command([command, *auth_args], timeout=20)
        record["auth"] = "ok" if auth_result["ok"] else "unknown"
        if auth_result["stdout"]:
            record["auth_detail"] = auth_result["stdout"].splitlines()[0]
        elif auth_result["stderr"]:
            record["auth_detail"] = auth_result["stderr"].splitlines()[0]
    return record


def _python_user_script_candidates(name: str) -> list[Path]:
    userbase = Path(site.getuserbase())
    script_dirs: list[Path]
    if os.name == "nt":
        script_dirs = [userbase / "Scripts"]
        usersite = site.getusersitepackages()
        if usersite:
            script_dirs.append(Path(usersite).resolve().parent / "Scripts")
        script_dirs.extend(candidate / "Scripts" for candidate in userbase.glob("Python*") if candidate.is_dir())
        candidates: list[Path] = []
        seen: set[Path] = set()
        for scripts_dir in script_dirs:
            for candidate in (
                scripts_dir / f"{name}.exe",
                scripts_dir / f"{name}.cmd",
                scripts_dir / f"{name}.bat",
                scripts_dir / name,
            ):
                if candidate not in seen:
                    seen.add(candidate)
                    candidates.append(candidate)
        return candidates

    scripts_dir = userbase / "bin"
    return [scripts_dir / name]


def _detect_skills_cli() -> dict[str, Any]:
    record = _tool_record("skills", command="npx", version_args=["skills", "--version"])
    if record["installed"] and record["status"] == "ok":
        record["invocation"] = "npx skills"
    return record


def _detect_gh() -> dict[str, Any]:
    record = _tool_record("gh", command="gh", version_args=["--version"], auth_args=["auth", "status"])
    if not record["installed"]:
        record["skill_supported"] = False
        return record
    skill_help = run_command(["gh", "help", "skill"], timeout=20)
    combined = f"{skill_help['stdout']}\n{skill_help['stderr']}".strip().lower()
    record["skill_supported"] = skill_help["ok"] and "unknown help topic" not in combined and 'unknown command "skill"' not in combined
    if not record["skill_supported"]:
        record["skill_detail"] = skill_help["stderr"] or skill_help["stdout"] or "gh skill unavailable"
    return record


def _gh_extensions() -> dict[str, dict[str, Any]]:
    gh_path = command_path("gh")
    if not gh_path:
        return {}
    result = run_command(["gh", "extension", "list"], timeout=20)
    if not result["ok"]:
        return {}

    extensions: dict[str, dict[str, Any]] = {}
    for raw_line in result["stdout"].splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("\t") if part.strip()]
        if not parts:
            continue
        command_name = parts[0]
        repo = parts[1] if len(parts) > 1 else command_name
        revision = parts[2] if len(parts) > 2 else None
        item = {"command": command_name, "repo": repo, "revision": revision}
        extensions[repo.lower()] = item
        extensions[repo.split("/")[-1].lower()] = item
        extensions[command_name.replace("gh ", "", 1).lower()] = item
    return extensions


def _detect_gh_codeql(extensions: dict[str, dict[str, Any]], gh_record: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "name": "gh-codeql",
        "command": "gh codeql",
        "path": gh_record.get("path"),
        "installed": False,
        "status": "missing",
    }
    if not gh_record.get("installed"):
        return record

    item = extensions.get("github/gh-codeql") or extensions.get("gh-codeql") or extensions.get("codeql")
    if item:
        record["installed"] = True
        record["status"] = "ok"
        record["repo"] = item.get("repo")
        if item.get("revision"):
            record["revision"] = item["revision"]
    return record


def _detect_ghas_cli() -> dict[str, Any]:
    path = command_path("ghas-cli")
    if not path:
        for candidate in _python_user_script_candidates("ghas-cli"):
            if candidate.exists():
                path = str(candidate)
                break

    record: dict[str, Any] = {
        "name": "ghas-cli",
        "command": "ghas-cli",
        "path": path,
        "installed": bool(path),
        "status": "missing",
        "auth": "unknown",
    }
    if not path:
        return record

    help_result = run_command([path, "-h"], timeout=20)
    if help_result["ok"]:
        record["status"] = "ok"
        record["callable"] = True
        first_line = (help_result["stdout"] or help_result["stderr"]).splitlines()
        if first_line:
            record["version"] = first_line[0]
        return record

    record["status"] = "degraded"
    record["callable"] = False
    combined = (help_result["stderr"] or help_result["stdout"] or "").strip().splitlines()
    if combined:
        record["runtime_error"] = combined[0]
    return record


def _playwright_browser_binaries() -> dict[str, str]:
    candidates: list[tuple[str, Path]] = []
    env_local = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    standard_roots = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
        env_local,
    ]
    standard_layouts = {
        "chrome": [
            ("Google", "Chrome", "Application", "chrome.exe"),
        ],
        "msedge": [
            ("Microsoft", "Edge", "Application", "msedge.exe"),
        ],
    }
    for label, layouts in standard_layouts.items():
        for root in standard_roots:
            for suffix in layouts:
                candidates.append((label, root.joinpath(*suffix)))

    playwright_root = env_local / "ms-playwright"
    if playwright_root.exists():
        for folder in sorted(playwright_root.glob("chromium-*")):
            candidates.append(("chromium", folder / "chrome-win64" / "chrome.exe"))
            candidates.append(("chromium", folder / "chrome-win" / "chrome.exe"))
        for folder in sorted(playwright_root.glob("mcp-chrome*")):
            candidates.append(("chromium", folder / "chrome-win64" / "chrome.exe"))
            candidates.append(("chromium", folder / "chrome-win" / "chrome.exe"))

    browser_present: dict[str, str] = {}
    for label, path in candidates:
        if label in browser_present:
            continue
        if path.exists():
            browser_present[label] = str(path)

    for label, command in {"chrome": "chrome", "msedge": "msedge", "chromium": "chromium"}.items():
        if label not in browser_present:
            found = command_path(command)
            if found:
                browser_present[label] = found
    return browser_present


def _detect_playwright() -> dict[str, Any]:
    wrapper_result = run_command([sys.executable, str(PLAYWRIGHT_WRAPPER), "--help"], timeout=40)
    browser_present = _playwright_browser_binaries()
    status = "ok" if wrapper_result["ok"] and browser_present else "degraded"
    if not command_path("npx"):
        status = "missing"
    return {
        "name": "playwright",
        "command": "python playwright_cli.py",
        "path": str(PLAYWRIGHT_WRAPPER),
        "cmd_wrapper": str(PLAYWRIGHT_WRAPPER_CMD),
        "installed": PLAYWRIGHT_WRAPPER.exists(),
        "status": status,
        "browser_binaries": browser_present,
        "wrapper_ready": wrapper_result["ok"],
        "wrapper_detail": wrapper_result["stderr"] or wrapper_result["stdout"],
        "mcp_status": "unknown",
    }


def _installed_skills() -> dict[str, Any]:
    result = run_command(["npx", "skills", "ls", "-g", "--json"], timeout=60)
    if not result["ok"]:
        return {"status": "degraded", "items": [], "error": result["stderr"] or result["stdout"]}
    try:
        items = json.loads(result["stdout"] or "[]")
    except json.JSONDecodeError as exc:
        return {"status": "error", "items": [], "error": f"failed to parse skills output: {exc}"}
    return {"status": "ok", "items": items}


def _config_payload() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    return tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _configured_plugins(config: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    plugins = config.get("plugins", {})
    if not isinstance(plugins, dict):
        return {"status": "ok", "items": items}
    for name, payload in sorted(plugins.items()):
        enabled = isinstance(payload, dict) and bool(payload.get("enabled"))
        items.append(
            {
                "name": name,
                "enabled": enabled,
                "status": "ok" if enabled else "disabled",
            }
        )
    return {"status": "ok", "items": items}


def _configured_mcp_servers(config: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    servers = config.get("mcp_servers", {})
    if not isinstance(servers, dict):
        return {"status": "ok", "items": items}
    for name, payload in sorted(servers.items()):
        if not isinstance(payload, dict):
            continue
        kind = "url" if payload.get("url") else "command" if payload.get("command") else "unknown"
        items.append(
            {
                "name": name,
                "kind": kind,
                "status": "configured",
                "configured": True,
                "transport": "mcp",
            }
        )
    return {"status": "ok", "items": items}


def _local_skill_names() -> set[str]:
    names: set[str] = set()
    if not SKILLS_DIR.exists():
        return names
    for path in SKILLS_DIR.rglob("SKILL.md"):
        relative = path.parent.relative_to(SKILLS_DIR)
        if relative.parts and relative.parts[0] == ".system":
            continue
        if len(relative.parts) == 1:
            names.add(relative.parts[0])
    return names


def _status_rank(status: str) -> int:
    return {
        "ok": 0,
        "configured": 0,
        "degraded": 1,
        "disabled": 2,
        "missing": 3,
        "error": 4,
        "unknown": 5,
    }.get(status, 5)


def _aggregate_status(statuses: list[str], *, mode: str) -> str:
    if not statuses:
        return "missing"
    available = [status for status in statuses if status in {"ok", "configured"}]
    if mode == "all":
        if len(available) == len(statuses):
            return "ok"
        if any(status == "degraded" for status in statuses):
            return "degraded"
        if available:
            return "degraded"
        return "missing"
    if mode == "paired":
        if len(available) == len(statuses):
            return "ok"
        if available:
            return "degraded"
        return "missing"
    if available:
        return "ok"
    if any(status == "degraded" for status in statuses):
        return "degraded"
    return "missing"


def _tool_status(tools: dict[str, Any], name: str) -> str:
    return tools.get(name, {}).get("status", "missing")


def _plugin_status(plugins: dict[str, Any], name: str) -> str:
    item = plugins.get(name)
    if not item:
        return "missing"
    return "ok" if item.get("enabled") else "disabled"


def _mcp_status(mcp_servers: dict[str, Any], name: str) -> str:
    item = mcp_servers.get(name)
    if not item:
        return "missing"
    return item.get("status", "configured")


def _skill_status(local_skill_names: set[str], name: str) -> str:
    return "ok" if name in local_skill_names else "missing"


def _interface_record(
    identifier: str,
    *,
    tools: dict[str, Any],
    plugins: dict[str, Any],
    mcp_servers: dict[str, Any],
    local_skill_names: set[str],
) -> dict[str, Any]:
    kind, name = identifier.split(":", 1)
    if kind == "tool":
        payload = tools.get(name, {})
        return {"kind": kind, "name": name, "status": payload.get("status", "missing")}
    if kind == "plugin":
        payload = plugins.get(name)
        return {"kind": kind, "name": name, "status": _plugin_status(plugins, name), "enabled": bool(payload and payload.get("enabled"))}
    if kind == "mcp":
        payload = mcp_servers.get(name)
        return {"kind": kind, "name": name, "status": _mcp_status(mcp_servers, name), "configured": bool(payload)}
    if kind == "skill":
        return {"kind": kind, "name": name, "status": _skill_status(local_skill_names, name)}
    return {"kind": kind, "name": name, "status": "unknown"}


def _capability_record(
    spec: dict[str, Any],
    *,
    tools: dict[str, Any],
    plugins: dict[str, Any],
    mcp_servers: dict[str, Any],
    local_skill_names: set[str],
) -> dict[str, Any]:
    skill_records = [
        {"kind": "skill", "name": name, "status": _skill_status(local_skill_names, name)}
        for name in spec.get("skills", [])
    ]
    interface_records = [
        _interface_record(
            identifier,
            tools=tools,
            plugins=plugins,
            mcp_servers=mcp_servers,
            local_skill_names=local_skill_names,
        )
        for identifier in spec.get("interfaces", [])
    ]

    required_statuses = [record["status"] for record in skill_records]
    interface_statuses = [record["status"] for record in interface_records]
    availability_mode = spec.get("availability_mode", "any")

    if availability_mode == "paired":
        paired_identifiers = spec.get("paired_primary", spec.get("interfaces", []))
        paired_records = [
            _interface_record(
                identifier,
                tools=tools,
                plugins=plugins,
                mcp_servers=mcp_servers,
                local_skill_names=local_skill_names,
            )
            for identifier in paired_identifiers
        ]
        interface_status = _aggregate_status([record["status"] for record in paired_records], mode="paired")
    else:
        interface_status = _aggregate_status(interface_statuses, mode=availability_mode) if interface_records else "ok"

    skill_status = _aggregate_status(required_statuses, mode="all") if required_statuses else "ok"
    status = "ok"
    if _status_rank(skill_status) > _status_rank(status):
        status = skill_status
    if _status_rank(interface_status) > _status_rank(status):
        status = interface_status

    advisory: str | None = None
    if spec["key"] == "autonomous-deep-runs":
        # The control-plane capability stays healthy as long as `agentctl run`
        # can drive the shared runner with an explicit worker command. The
        # default Codex runtime on a given machine may still be degraded.
        status = "ok"
        codex_runtime = tools.get("codex", {})
        if not codex_runtime.get("worker_runtime_ready"):
            advisory = (
                "Default Codex runtime is not callable in this environment. "
                "Use `--worker-command` or configure `AGENTCTL_CODEX_WORKER_TEMPLATE` "
                "for unattended deep runs."
            )

    backing = skill_records + interface_records
    backing_sorted = sorted(backing, key=lambda item: (_status_rank(item["status"]), item["kind"], item["name"]))
    record = {
        "key": spec["key"],
        "label": spec["label"],
        "group": spec["group"],
        "required": spec.get("required", True),
        "status": status,
        "front_door": spec["front_door"],
        "entrypoints": spec["entrypoints"],
        "skills": [record["name"] for record in skill_records],
        "backing_interfaces": backing_sorted,
        "overlap_policy": spec["overlap_policy"],
        "summary": spec.get("summary", spec["label"]),
        "routing_notes": spec.get("routing_notes", []),
    }
    if advisory:
        record["advisory"] = advisory
    return record


def _enabled_plugins_map(config: dict[str, Any]) -> dict[str, Any]:
    records = _configured_plugins(config)["items"]
    return {item["name"]: item for item in records}


def _mcp_servers_map(config: dict[str, Any]) -> dict[str, Any]:
    records = _configured_mcp_servers(config)["items"]
    return {item["name"]: item for item in records}


def build_capabilities_report() -> dict[str, Any]:
    gh = _detect_gh()
    gh_extensions = _gh_extensions() if gh.get("installed") else {}
    tools = {
        "python": {
            "name": "python",
            "command": sys.executable,
            "path": sys.executable,
            "installed": True,
            "status": "ok",
            "version": sys.version.splitlines()[0],
        },
        "npx": _tool_record("npx", command="npx", version_args=["--version"]),
        "skills": _detect_skills_cli(),
        "codex": detect_codex_runtime(),
        "gh": gh,
        "gh-codeql": _detect_gh_codeql(gh_extensions, gh),
        "ghas-cli": _detect_ghas_cli(),
        "vercel": _tool_record("vercel", command="vercel", version_args=["--version"]),
        "supabase": _tool_record("supabase", command="supabase", version_args=["--version"]),
        "firebase": _tool_record("firebase", command="firebase", version_args=["--version"], detect_only=True),
        "gcloud": _tool_record("gcloud", command="gcloud", version_args=["--version"], detect_only=True),
        "playwright": _detect_playwright(),
    }
    installed_skills = _installed_skills()
    config = _config_payload()
    plugins = _enabled_plugins_map(config)
    mcp_servers = _mcp_servers_map(config)
    local_skill_names = _local_skill_names()
    capabilities = [
        _capability_record(
            spec,
            tools=tools,
            plugins=plugins,
            mcp_servers=mcp_servers,
            local_skill_names=local_skill_names,
        )
        for spec in CAPABILITY_SPECS
    ]
    detect_only_tools = [name for name in ("firebase", "gcloud") if tools[name]["installed"]]
    overlap_analysis = [
        {
            "capability": capability["key"],
            "front_door": capability["front_door"],
            "backing_kinds": sorted({entry["kind"] for entry in capability["backing_interfaces"]}),
            "overlap_count": len(capability["backing_interfaces"]),
            "policy": capability["overlap_policy"],
        }
        for capability in capabilities
        if len(capability["backing_interfaces"]) > 1
    ]

    required_tool_statuses = {tools[name]["status"] for name in REQUIRED_TOOL_NAMES if name in tools}
    required_capability_statuses = {entry["status"] for entry in capabilities if entry.get("required", True)}
    combined_statuses = required_tool_statuses | required_capability_statuses
    summary_status = "error" if "error" in combined_statuses else "degraded" if "degraded" in combined_statuses or "missing" in combined_statuses or "disabled" in combined_statuses else "ok"

    required_capability_count = sum(1 for entry in capabilities if entry.get("required", True))
    optional_capability_count = len(capabilities) - required_capability_count
    optional_attention_count = sum(1 for entry in capabilities if not entry.get("required", True) and entry.get("status") != "ok")

    return {
        "schema_version": 2,
        "generated_at": utc_now(),
        "codex_home": str(Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).resolve()),
        "summary": {
            "status": summary_status,
            "installed_skill_count": len(installed_skills["items"]),
            "local_skill_count": len(local_skill_names),
            "enabled_plugin_count": sum(1 for item in plugins.values() if item.get("enabled")),
            "configured_mcp_count": len(mcp_servers),
            "global_skills_dir": str(SKILLS_DIR),
            "required_capability_count": required_capability_count,
            "optional_capability_count": optional_capability_count,
            "optional_attention_count": optional_attention_count,
        },
        "installed_skills": installed_skills,
        "local_skills": {
            "status": "ok",
            "items": sorted(local_skill_names),
        },
        "plugins": {
            "status": "ok",
            "items": sorted(plugins.values(), key=lambda item: item["name"]),
        },
        "mcp_servers": {
            "status": "ok",
            "items": sorted(mcp_servers.values(), key=lambda item: item["name"]),
        },
        "tools": tools,
        "capabilities": capabilities,
        "overlap_analysis": overlap_analysis,
        "detect_only_tools": detect_only_tools,
    }


def capability_doc_path(key: str) -> Path:
    return AGENTCTL_CAPABILITIES_DOCS_DIR / f"{key}.md"


def capability_keys(payload: dict[str, Any]) -> list[str]:
    return [item["key"] for item in payload.get("capabilities", [])]


def capability_detail(payload: dict[str, Any], key: str) -> dict[str, Any] | None:
    capability = next((item for item in payload.get("capabilities", []) if item.get("key") == key), None)
    if capability is None:
        return None

    tool_map = payload.get("tools", {})
    fallback_label = key.replace("-", " ").title()
    cloud_items = [
        item
        for item in payload.get("cloud_readiness", [])
        if item.get("name") in CAPABILITY_CLOUD_READINESS.get(key, [])
    ]

    return {
        "key": capability["key"],
        "label": capability.get("label", fallback_label),
        "group": capability.get("group", "unknown"),
        "required": capability.get("required", True),
        "status": capability["status"],
        "front_door": capability["front_door"],
        "entrypoints": capability.get("entrypoints", []),
        "skills": capability.get("skills", []),
        "backing_interfaces": capability.get("backing_interfaces", []),
        "overlap_policy": capability.get("overlap_policy"),
        "summary": capability.get("summary", capability.get("label", fallback_label)),
        "routing_notes": capability.get("routing_notes", []),
        "advisory": capability.get("advisory"),
        "doc_path": str(capability_doc_path(capability["key"])),
        "cloud_readiness": cloud_items,
        "tool_snapshot": {
            name: tool_map.get(name)
            for name in ("codex", "gh", "gh-codeql", "ghas-cli", "playwright", "supabase", "vercel")
            if name in tool_map
        },
    }


def _grouped_capabilities(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in payload.get("capabilities", []):
        grouped.setdefault(item["group"], []).append(item)
    for items in grouped.values():
        items.sort(key=lambda item: (item["status"] != "ok", item["label"]))
    return grouped


def _capability_counts(payload: dict[str, Any], *, required_only: bool = False) -> dict[str, int]:
    counts = {"ok": 0, "degraded": 0, "missing": 0, "disabled": 0, "error": 0, "other": 0}
    for item in payload.get("capabilities", []):
        if required_only and not item.get("required", True):
            continue
        status = item.get("status", "other")
        if status not in counts:
            counts["other"] += 1
        else:
            counts[status] += 1
    return counts


def _doctor_notes(payload: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    gh = payload.get("tools", {}).get("gh", {})
    if gh.get("installed") and not gh.get("skill_supported"):
        notes.append("`gh skill` is unavailable locally, so publish/preview wrappers stay disabled.")
    ghas_cli = payload.get("tools", {}).get("ghas-cli", {})
    if ghas_cli.get("installed") and ghas_cli.get("status") != "ok":
        notes.append("`ghas-cli` is installed but not callable cleanly here, so GitHub security work should prefer `gh api` and `gh codeql` unless the GHAS CLI route is repaired.")
    detect_only = payload.get("detect_only_tools", [])
    if detect_only:
        notes.append("Detect-only capabilities remain intentionally lightweight: " + ", ".join(f"`{name}`" for name in detect_only) + ".")
    optional_unavailable = [
        item["label"]
        for item in payload.get("capabilities", [])
        if not item.get("required", True) and item.get("status") != "ok"
    ]
    if optional_unavailable:
        notes.append(
            "Optional capabilities are not counted as baseline failures: "
            + ", ".join(f"`{label}`" for label in optional_unavailable[:6])
            + ("." if len(optional_unavailable) <= 6 else ", and more.")
        )
    codex = payload.get("tools", {}).get("codex", {})
    if codex.get("installed") and not codex.get("callable"):
        notes.append(
            "Codex CLI is installed but not callable in this environment; unattended deep runs need an explicit worker command or a configured `AGENTCTL_CODEX_WORKER_TEMPLATE`."
        )
    elif not codex.get("installed"):
        notes.append("Codex CLI is not detected locally; unattended deep runs need `--worker-command` or `CODEX_WORKFLOW_WORKER_COMMAND`.")
    return notes


def print_doctor_human(payload: dict[str, Any], *, as_json: bool = False) -> None:
    if as_json:
        print_json(payload)
        return

    summary = payload.get("summary", {})
    print(f"Status: {summary.get('status', 'unknown')}")
    counts = _capability_counts(payload, required_only=True)
    total = sum(counts.values())
    print(f"Healthy baseline capabilities: {counts['ok']} / {total}")
    needs_attention = counts["degraded"] + counts["missing"] + counts["disabled"] + counts["error"] + counts["other"]
    print(f"Needs attention: {needs_attention}")
    optional_attention = payload.get("summary", {}).get("optional_attention_count", 0)
    if optional_attention:
        print(f"Optional capabilities unavailable: {optional_attention}")
    if payload.get("installed_skills", {}).get("items") is not None:
        print(f"Installed skills: {summary.get('installed_skill_count', 0)}")

    issues = [
        item
        for item in payload.get("capabilities", [])
        if item.get("required", True) and item.get("status") != "ok"
    ]
    if issues:
        print("")
        print("Needs attention")
        for item in issues:
            print(f"- {item['label']}: {item['status']} | front door `{item['front_door']}`")

    notes = _doctor_notes(payload)
    if notes:
        print("")
        print("Notes")
        for note in notes:
            print(f"- {note}")


def print_capabilities_human(payload: dict[str, Any], *, as_json: bool = False) -> None:
    if as_json:
        print_json(payload)
        return

    summary = payload.get("summary", {})
    print(f"Status: {summary.get('status', 'unknown')}")
    print("")
    print("Capability menu")
    grouped = _grouped_capabilities(payload)
    for group_key in ("control-plane", "workflow-skills", "research-and-verification", "integrations"):
        items = grouped.get(group_key, [])
        if not items:
            continue
        print(f"- {GROUP_LABELS[group_key]}:")
        for item in items:
            optional_tag = " optional" if not item.get("required", True) else ""
            print(f"  - {item['key']}: `{item['front_door']}` [{item['status']}{optional_tag}]")
    print("")
    print("Use `agentctl capability <key>` for the drill-down page for any capability.")
    notes = _doctor_notes(payload)
    if notes:
        print("")
        print("Notes")
        for note in notes:
            print(f"- {note}")


def print_capability_human(payload: dict[str, Any], *, as_json: bool = False) -> None:
    if as_json:
        print_json(payload)
        return

    print(f"Capability: {payload['label']} (`{payload['key']}`)")
    print(f"Status: {payload['status']}")
    print(f"Front door: `{payload['front_door']}`")
    print(f"Doc page: `{payload['doc_path']}`")
    print("")
    print(payload["summary"])

    if payload.get("skills"):
        print("")
        print("Navigation skills")
        for name in payload["skills"]:
            print(f"- `{name}`")

    if payload.get("entrypoints"):
        print("")
        print("Entry points")
        for entry in payload["entrypoints"]:
            print(f"- `{entry}`")

    if payload.get("routing_notes"):
        print("")
        print("Routing notes")
        for note in payload["routing_notes"]:
            print(f"- {note}")

    if payload.get("advisory"):
        print("")
        print("Advisory")
        print(f"- {payload['advisory']}")

    if payload.get("backing_interfaces"):
        print("")
        print("Backing interfaces")
        for item in payload["backing_interfaces"]:
            extras: list[str] = []
            if "enabled" in item:
                extras.append(f"enabled={str(item['enabled']).lower()}")
            if "configured" in item:
                extras.append(f"configured={str(item['configured']).lower()}")
            suffix = f" ({', '.join(extras)})" if extras else ""
            print(f"- {item['kind']} `{item['name']}` [{item['status']}]"+suffix)

    if payload.get("cloud_readiness"):
        print("")
        print("Cloud readiness")
        for item in payload["cloud_readiness"]:
            print(f"- `{item['name']}`: `{item['classification']}`")

    print("")
    print("Overlap policy")
    print(f"- {payload['overlap_policy']}")


def print_status_human(payload: dict[str, Any], *, as_json: bool = False) -> None:
    if as_json:
        print_json(payload)
        return

    summary = payload.get("summary", {})
    print(f"Status: {summary.get('status', 'unknown')}")
    print(f"Active workflows: {summary.get('count', 0)}")
    historical_count = summary.get("historical_count", 0)
    if historical_count:
        print(f"Historical workflows hidden: {historical_count}")

    print("")
    print("Workflows")
    workflows = payload.get("workflows", [])
    if not workflows:
        print("- none")
        return
    for workflow in workflows:
        print(
            f"- {workflow['workflow_name']}: {workflow['status']} | "
            f"{workflow['tasks_done']}/{workflow['tasks_total']} done | "
            f"repo `{workflow['repo_root']}`"
        )
        if workflow.get("tasks_open") or workflow.get("tasks_blocked"):
            print(f"  - open {workflow['tasks_open']} | blocked {workflow['tasks_blocked']} | iteration {workflow.get('iteration', 0)}")
        if workflow.get("checklist_path"):
            print(f"  - checklist `{workflow['checklist_path']}`")


def print_skills_human(payload: dict[str, Any], *, as_json: bool = False) -> None:
    if as_json:
        print_json(payload)
        return

    summary = payload.get("summary", {})
    print(f"Status: {summary.get('status', 'unknown')}")
    if summary.get("scope"):
        print(f"Scope: {summary['scope']}")

    if payload.get("skills") is not None:
        print("")
        print("Skills")
        for item in payload["skills"]:
            print(f"- {item['name']}: {item.get('path', 'unknown path')}")
        return

    if payload.get("added_skills"):
        print("")
        print("Added skills")
        for name in payload["added_skills"]:
            print(f"- {name}")
        return

    if payload.get("tracked_missing") is not None:
        print("")
        print("Managed local skills")
        local_tracked = payload.get("tracked_local", [])
        if local_tracked:
            for name in local_tracked:
                print(f"- {name}")
        else:
            print("- none")

        print("")
        print("Managed external skills")
        external_tracked = payload.get("tracked_external", [])
        if external_tracked:
            for name in external_tracked:
                print(f"- {name}")
        else:
            print("- none")

        if payload.get("tracked_missing"):
            print("")
            print("Missing managed skills")
            for name in payload["tracked_missing"]:
                print(f"- {name}")

        unmanaged = payload.get("unmanaged_installed", [])
        if unmanaged:
            print("")
            print("Unmanaged installed skills")
            for name in unmanaged:
                print(f"- {name}")
        return

    if payload.get("updated") is not None:
        print("")
        print("Updated entries")
        if not payload["updated"]:
            print("- none")
        for item in payload["updated"]:
            names = ", ".join(item.get("added_skills", [])) or "no skills reported"
            print(f"- {item.get('source', 'unknown source')}: {names}")
        if payload.get("note"):
            print("")
            print(f"Note: {payload['note']}")


def print_research_human(payload: dict[str, Any], *, as_json: bool = False) -> None:
    if as_json:
        print_json(payload)
        return

    print(f"Status: {payload.get('status', 'unknown')}")
    print(f"Track: {payload.get('mode', 'unknown')}")
    print(f"Query: {payload.get('query', '')}")
    shortlist = payload.get("evidence", {}).get("shortlist", [])
    if shortlist:
        print("")
        print("Shortlist")
        for item in shortlist[:5]:
            print(f"- {item['title']}: {item['url']}")
    caveats = payload.get("evidence", {}).get("caveats", [])
    if caveats:
        print("")
        print("Caveats")
        for item in caveats:
            print(f"- {item}")
    print("")
    print(f"Evidence: {payload['paths']['json']}")
    print(f"Brief: {payload['paths']['brief']}")
