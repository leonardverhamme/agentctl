from __future__ import annotations

import json
import ntpath
import os
import site
import sys
import tomllib
from pathlib import Path
from typing import Any

from .branding import LEGACY_PLUGIN_NAMES, PUBLIC_COMMAND, PUBLIC_DOCS_DIRNAME, PUBLIC_PRODUCT_NAME
from .codex_runtime import detect_codex_runtime
from .common import command_path, print_json, run_command, utc_now
from .config_layers import effective_config
from .inventory import load_inventory_snapshot
from .paths import AGENTCTL_CAPABILITIES_DOCS_DIR, CONFIG_PATH, PLAYWRIGHT_WRAPPER, PLAYWRIGHT_WRAPPER_CMD, PLUGINS_DIR, SKILLS_DIR


CAPABILITY_SPECS: list[dict[str, Any]] = [
    {
        "key": "autonomous-deep-runs",
        "label": "Autonomous deep runs",
        "group": "core",
        "required": True,
        "front_door": "$autonomous-deep-runs-capability",
        "entrypoints": [
            "$autonomous-deep-runs-capability",
            f"{PUBLIC_COMMAND} capability autonomous-deep-runs",
            f"{PUBLIC_COMMAND} run <workflow>",
            "CODEX_WORKFLOW_WORKER_COMMAND",
            "AGENTCTL_CODEX_WORKER_TEMPLATE",
        ],
        "skills": ["autonomous-deep-runs-capability"],
        "interfaces": ["tool:codex"],
        "availability_mode": "all",
        "overlap_policy": "The outer execute-until-done loop must use a real worker command, not chat memory. Prefer Codex runtime when it is callable or explicitly templated.",
        "summary": "Use for launching, resuming, and diagnosing unattended deep workflows through the shared runner.",
        "routing_notes": [
            f"Start with the capability skill, then route into `{PUBLIC_COMMAND} run <workflow>`.",
            "A real worker command or `AGENTCTL_CODEX_WORKER_TEMPLATE` is still required for unattended execution.",
        ],
    },
    {
        "key": "long-task-loops",
        "label": "Long task loops",
        "group": "core",
        "required": True,
        "front_door": "$loopsmith",
        "entrypoints": [
            "$loopsmith",
            f"{PUBLIC_COMMAND} capability long-task-loops",
            f"{PUBLIC_COMMAND} loop <name>",
            f"{PUBLIC_COMMAND} status --repo <path>",
            f"{PUBLIC_COMMAND} self-check",
        ],
        "skills": ["loopsmith"],
        "interfaces": [],
        "availability_mode": "all",
        "overlap_policy": "Use named deep workflows first. Use the generic durable loop only when the task is large, multi-step, and does not already fit a dedicated workflow skill.",
        "summary": "Use for oversized or novel tasks that need a durable checklist, state file, and one-batch-at-a-time loop until the queue is truly empty.",
        "routing_notes": [
            f"Start with `$loopsmith`, then launch the durable loop with `{PUBLIC_COMMAND} loop <name>`.",
            f"Prefer `{PUBLIC_COMMAND} run <workflow>` when a dedicated deep workflow already exists, such as UI, docs, test, refactor, or CI/CD audits.",
            f"If `{PUBLIC_COMMAND}` or `loopsmith` is not on PATH, repair the launcher with the bundle-local `agentctl.py doctor --fix` path before continuing; do not replace the loop with docs-only tracking.",
            "Store the task brief on disk and let the outer runner own `.codex-workflows/<name>/state.json`, the checklist, and the progress notes.",
        ],
    },
    {
        "key": "skills-management",
        "label": "Skills management",
        "group": "core",
        "required": True,
        "front_door": "$skills-management-capability",
        "entrypoints": [
            "$skills-management-capability",
            f"{PUBLIC_COMMAND} capability skills-management",
            f"{PUBLIC_COMMAND} skills list",
            f"{PUBLIC_COMMAND} skills add",
            f"{PUBLIC_COMMAND} skills check",
            f"{PUBLIC_COMMAND} skills update",
        ],
        "skills": ["skills-management-capability"],
        "interfaces": ["tool:skills", "tool:npx"],
        "availability_mode": "all",
        "overlap_policy": "Wrap official skills tooling rather than reimplementing it.",
        "summary": "Use for listing, adding, checking, and safely updating installed skills and their provenance.",
        "routing_notes": [
            "Use the capability skill first so the agent stays on the thin wrapper path instead of bypassing the official skills tooling.",
            "Keep installs pinned and provenance-aware rather than treating `skills update` as an uncontrolled bulk sync.",
        ],
    },
    {
        "key": "agentcli-maintenance",
        "label": "Agent CLI OS maintenance",
        "group": "core",
        "required": True,
        "front_door": "$agentcli-maintenance-engineer",
        "entrypoints": [f"{PUBLIC_COMMAND} maintenance check", f"{PUBLIC_COMMAND} maintenance audit", f"{PUBLIC_COMMAND} maintenance fix-docs"],
        "skills": ["agentcli-maintenance-engineer"],
        "interfaces": [f"plugin:{PUBLIC_PRODUCT_NAME}"],
        "availability_mode": "all",
        "overlap_policy": "Keep maintenance as one capability surface for docs, packaging, registry health, and platform drift.",
        "summary": "Use for control-plane maintenance, generated docs refreshes, machine-state audits, packaging drift, and maintenance-report regeneration.",
        "routing_notes": [
            f"Start with `$agentcli-maintenance-engineer` when the Agent CLI OS control plane itself changed or looks suspect.",
            f"Use `{PUBLIC_COMMAND} maintenance audit` to refresh the generated docs, state, and maintenance report together instead of hand-editing generated files.",
        ],
    },
    {
        "key": "plugin-evaluation",
        "label": "Plugin evaluation",
        "group": "core",
        "required": False,
        "front_door": "$plugin-eval:plugin-eval",
        "entrypoints": [
            "$plugin-eval:plugin-eval",
            "$plugin-eval:evaluate-plugin",
            "$plugin-eval:evaluate-skill",
            f"{PUBLIC_COMMAND} capability plugin-evaluation",
            'plugin-eval start <path> --request "<natural request>"',
        ],
        "skills": ["plugin-eval:plugin-eval"],
        "interfaces": ["plugin:plugin-eval@openai-curated", "tool:plugin-eval"],
        "availability_mode": "paired",
        "overlap_policy": "Keep plugin and skill evaluation behind one chat-first route instead of scattering analysis, budget, and benchmark commands through the default menu.",
        "summary": "Use for evaluating skills and plugins, explaining token budgets, and planning or running local benchmark workflows.",
        "routing_notes": [
            "Start with `$plugin-eval:plugin-eval` for chat-first evaluation requests such as score explanations, fix-first prioritization, and benchmark planning.",
            "Use the local `plugin-eval` command when you want the exact analyze, explain-budget, measurement-plan, or benchmark workflow on disk.",
            "Fixture skills bundled with the Plugin Eval repo are test data and stay hidden from the curated capability surface.",
        ],
    },
    {
        "key": "repo-intelligence",
        "label": "Repo intelligence",
        "group": "core",
        "required": False,
        "front_door": f"{PUBLIC_COMMAND} repo-intel",
        "entrypoints": [
            f"{PUBLIC_COMMAND} repo-intel status",
            f"{PUBLIC_COMMAND} repo-intel ensure",
            f"{PUBLIC_COMMAND} repo-intel update",
            f"{PUBLIC_COMMAND} repo-intel query",
            f"{PUBLIC_COMMAND} repo-intel audit",
            f"{PUBLIC_COMMAND} repo-intel serve",
        ],
        "skills": [],
        "interfaces": ["tool:graphify"],
        "availability_mode": "any",
        "overlap_policy": "Keep repo intelligence as a CLI-first subsystem. Graphify is the indexing engine, Obsidian is a secondary export/view layer, and AGENTS guidance should stay a tiny routing hint only.",
        "summary": "Use for per-repo graph health, repo-first graph routing, managed `.gitignore` hygiene, ensure/update flows, graph-backed repo queries, and workspace-wide trusted-repo audits.",
        "routing_notes": [
            f"When the agent is already inside a repo, keep that repo as the working universe and start with `{PUBLIC_COMMAND} repo-intel status` or `{PUBLIC_COMMAND} repo-intel ensure` before broad raw-file search.",
            f"Trusted repos should default to `{PUBLIC_COMMAND} repo-intel ensure` when repo-intel, repo hygiene, or graph freshness drift appears so graph-first retrieval stays the normal path.",
            f"Use `{PUBLIC_COMMAND} repo-intel query` for focused graph traversal and `{PUBLIC_COMMAND} repo-intel serve` when an MCP client should talk to the local graph directly.",
            f"Use `{PUBLIC_COMMAND} computer-intel ...` only when the target repo is unknown or the task is explicitly cross-repo.",
            "Do not treat the workspace registry as the repo graph itself; it is an index-of-indexes over trusted repos.",
        ],
    },
    {
        "key": "computer-intelligence",
        "label": "Computer intelligence",
        "group": "core",
        "required": False,
        "front_door": f"{PUBLIC_COMMAND} computer-intel",
        "entrypoints": [
            f"{PUBLIC_COMMAND} computer-intel status",
            f"{PUBLIC_COMMAND} computer-intel refresh",
            f"{PUBLIC_COMMAND} computer-intel search",
        ],
        "skills": [],
        "interfaces": [],
        "availability_mode": "all",
        "overlap_policy": "Keep the machine-wide laptop discovery layer separate from per-repo Graphify graphs. Use the global index for whole-computer discovery and repo selection, then drop into repo-intel for repo-specific graph work.",
        "summary": "Use for machine-wide discovery of repos, vaults, Graphify outputs, services, and laptop-wide path search without replacing repo-local graph traversal.",
        "routing_notes": [
            f"Treat `{PUBLIC_COMMAND} computer-intel ...` as the exception path, not the default repo workflow.",
            f"Start with `{PUBLIC_COMMAND} computer-intel status` or `{PUBLIC_COMMAND} computer-intel refresh` only when the task is about the whole laptop rather than one repo.",
            f"Use `{PUBLIC_COMMAND} computer-intel search` for laptop-wide discovery, then switch to `{PUBLIC_COMMAND} repo-intel ...` once the target repo is known.",
            "The machine-wide index is metadata-first and should not replace per-repo Graphify graphs for architecture questions.",
        ],
    },
    {
        "key": "context-workflows",
        "label": "Repo context workflows",
        "group": "workflows",
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
        "group": "workflows",
        "required": True,
        "front_door": "$ui-skill / $ui-deep-audit",
        "entrypoints": ["$ui-skill", "$ui-deep-audit", f"{PUBLIC_COMMAND} run ui-deep-audit"],
        "skills": ["ui-skill", "ui-deep-audit"],
        "interfaces": [],
        "availability_mode": "all",
        "overlap_policy": "Surface the UI skills first; plugin support stays a backing capability, not a separate menu.",
    },
    {
        "key": "test-workflows",
        "label": "Testing workflows",
        "group": "workflows",
        "required": True,
        "front_door": "$test-skill / $test-deep-audit",
        "entrypoints": ["$test-skill", "$test-deep-audit", f"{PUBLIC_COMMAND} run test-deep-audit"],
        "skills": ["test-skill", "test-deep-audit"],
        "interfaces": [],
        "availability_mode": "any",
        "overlap_policy": "Collapse testing transports behind one testing surface; use repo-native CLIs and Playwright first.",
    },
    {
        "key": "docs-workflows",
        "label": "Documentation workflows",
        "group": "workflows",
        "required": True,
        "front_door": "$docs-skill / $docs-deep-audit",
        "entrypoints": ["$docs-skill", "$docs-deep-audit", f"{PUBLIC_COMMAND} run docs-deep-audit"],
        "skills": ["docs-skill", "docs-deep-audit"],
        "interfaces": [],
        "availability_mode": "all",
        "overlap_policy": "Keep docs work in the docs skills and hide transport details entirely.",
    },
    {
        "key": "refactor-workflows",
        "label": "Refactor workflows",
        "group": "workflows",
        "required": True,
        "front_door": "$refactor-skill / $refactor-deep-audit",
        "entrypoints": ["$refactor-skill", "$refactor-deep-audit", "$refactor-orchestrator", f"{PUBLIC_COMMAND} run refactor-deep-audit"],
        "skills": ["refactor-skill", "refactor-deep-audit", "refactor-orchestrator"],
        "interfaces": [],
        "availability_mode": "all",
        "overlap_policy": "Use the local refactor skills as the capability surface; do not split by underlying tooling.",
    },
    {
        "key": "cicd-workflows",
        "label": "CI/CD workflows",
        "group": "workflows",
        "required": True,
        "front_door": "$cicd-skill / $cicd-deep-audit",
        "entrypoints": ["$cicd-skill", "$cicd-deep-audit", f"{PUBLIC_COMMAND} run cicd-deep-audit"],
        "skills": ["cicd-skill", "cicd-deep-audit"],
        "interfaces": [],
        "availability_mode": "all",
        "overlap_policy": "Surface CI/CD by workflow, not by whether GitHub or Vercel provides the underlying route.",
    },
    {
        "key": "code-review",
        "label": "Code review",
        "group": "workflows",
        "required": False,
        "front_door": "$coderabbit:coderabbit-review",
        "entrypoints": [
            "$coderabbit:coderabbit-review",
            f"{PUBLIC_COMMAND} capability code-review",
            "coderabbit review --agent",
        ],
        "skills": ["coderabbit:coderabbit-review"],
        "interfaces": ["plugin:coderabbit@openai-curated", "tool:coderabbit"],
        "availability_mode": "paired",
        "overlap_policy": "Keep AI-powered code review under one explicit route: the CodeRabbit plugin skill plus a callable CodeRabbit runtime.",
        "summary": "Use for AI-powered review of the current diff, structured findings, and follow-up fix guidance.",
        "routing_notes": [
            "Start with `$coderabbit:coderabbit-review` when you want a real AI review of the current changes rather than an ad hoc chat review.",
            "Keep CodeRabbit findings separate from human findings and do not claim manual review output came from CodeRabbit.",
            "If the CodeRabbit CLI is not callable, keep the capability visible but marked degraded until the runtime is installed or linked.",
        ],
    },
    {
        "key": "research",
        "label": "Research",
        "group": "research",
        "required": True,
        "front_door": "$research-capability",
        "entrypoints": [
            "$research-capability",
            f"{PUBLIC_COMMAND} capability research",
            f"{PUBLIC_COMMAND} research web",
            f"{PUBLIC_COMMAND} research github",
            f"{PUBLIC_COMMAND} research scout",
        ],
        "skills": ["research-capability", "internet-researcher", "github-researcher", "web-github-scout"],
        "interfaces": [],
        "availability_mode": "any",
        "overlap_policy": "Hide web, GitHub, and browser transport choices behind one research surface and one evidence contract.",
        "summary": "Use for routing current web research, GitHub scouting, and mixed evidence briefs through one front door.",
        "routing_notes": [
            "Use the capability skill first, then pick `$internet-researcher`, `$github-researcher`, or `$web-github-scout` based on the evidence mix you need.",
            "Keep the shared evidence contract intact instead of inventing ad hoc research output formats.",
        ],
    },
    {
        "key": "github-workflows",
        "label": "GitHub workflows",
        "group": "platforms",
        "required": False,
        "front_door": "$github-capability",
        "entrypoints": ["$github-capability", f"{PUBLIC_COMMAND} capability github-workflows", "$github:github", "$github:gh-fix-ci", "$github:gh-address-comments", "gh"],
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
        "group": "platforms",
        "required": False,
        "front_door": "$github-security-capability",
        "entrypoints": [
            "$github-security-capability",
            f"{PUBLIC_COMMAND} capability github-advanced-security",
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
        "group": "browser-design",
        "required": False,
        "front_door": "$browser-capability",
        "entrypoints": ["$browser-capability", f"{PUBLIC_COMMAND} capability browser-automation", "$playwright", "playwright.cmd", "Playwright MCP"],
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
        "group": "platforms",
        "required": False,
        "front_door": "$vercel-capability",
        "entrypoints": ["$vercel-capability", f"{PUBLIC_COMMAND} capability vercel-platform", "$vercel:vercel-cli", "$vercel:deployments-cicd", "vercel"],
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
        "group": "platforms",
        "required": False,
        "front_door": "$supabase-capability",
        "entrypoints": ["$supabase-capability", f"{PUBLIC_COMMAND} capability supabase-data", "supabase", "Supabase MCP"],
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
        "group": "platforms",
        "required": False,
        "front_door": "$stripe-capability",
        "entrypoints": ["$stripe-capability", f"{PUBLIC_COMMAND} capability stripe-payments", "$stripe:stripe-best-practices", "$stripe:upgrade-stripe"],
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
        "group": "platforms",
        "required": False,
        "front_door": "$sentry-capability",
        "entrypoints": ["$sentry-capability", f"{PUBLIC_COMMAND} capability sentry-observability", "$sentry:sentry"],
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
        "group": "native",
        "required": False,
        "front_door": "$ios-development-capability",
        "entrypoints": [
            "$ios-development-capability",
            f"{PUBLIC_COMMAND} capability ios-development",
            "$build-ios-apps:ios-debugger-agent",
            "$build-ios-apps:swiftui-ui-patterns",
        ],
        "skills": ["ios-development-capability"],
        "interfaces": ["plugin:build-ios-apps@openai-curated"],
        "availability_mode": "all",
        "overlap_policy": "Expose iOS build, UI, and debugging workflows as one capability backed by the iOS plugin.",
        "summary": "Use for local iOS builds, simulator debugging, SwiftUI UI work, and iOS-specific review paths.",
        "routing_notes": [
            "Start with the capability skill, then route into the specific Build iOS Apps plugin skill that best matches the task.",
        ],
    },
    {
        "key": "macos-development",
        "label": "macOS development",
        "group": "native",
        "required": False,
        "front_door": "$macos-development-capability",
        "entrypoints": [
            "$macos-development-capability",
            f"{PUBLIC_COMMAND} capability macos-development",
            "$build-macos-apps:build-run-debug",
            "$build-macos-apps:swiftui-patterns",
        ],
        "skills": ["macos-development-capability"],
        "interfaces": ["plugin:build-macos-apps@openai-curated"],
        "availability_mode": "all",
        "overlap_policy": "Expose macOS build, packaging, and desktop debugging as one capability backed by the macOS plugin.",
        "summary": "Use for local macOS build, run, packaging, signing, and desktop-specific SwiftUI/AppKit work.",
        "routing_notes": [
            "Start with the capability skill, then route into the specific Build macOS Apps plugin skill that fits the current task.",
        ],
    },
    {
        "key": "android-testing",
        "label": "Android testing",
        "group": "native",
        "required": False,
        "front_door": "$android-testing-capability",
        "entrypoints": [
            "$android-testing-capability",
            f"{PUBLIC_COMMAND} capability android-testing",
            "$test-android-apps:android-emulator-qa",
        ],
        "skills": ["android-testing-capability"],
        "interfaces": ["plugin:test-android-apps@openai-curated"],
        "availability_mode": "all",
        "overlap_policy": "Expose Android emulator QA as one capability backed by the Android testing plugin.",
        "summary": "Use for Android emulator QA, reproduction, screenshots, and log-driven debugging.",
        "routing_notes": [
            "Start with the capability skill, then route into the Android emulator QA plugin skill for the actual run.",
        ],
    },
    {
        "key": "figma-design",
        "label": "Figma design",
        "group": "browser-design",
        "required": False,
        "front_door": "$figma-capability",
        "entrypoints": ["$figma-capability", f"{PUBLIC_COMMAND} capability figma-design", "Figma MCP"],
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
        "group": "browser-design",
        "required": False,
        "front_door": "$nextjs-runtime-capability",
        "entrypoints": ["$nextjs-runtime-capability", f"{PUBLIC_COMMAND} capability nextjs-runtime", "Next DevTools MCP"],
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

CAPABILITY_GROUPS = [
    {
        "key": "core",
        "label": "Core",
        "summary": "Control-plane entrypoints for install health, maintenance, and unattended worker routing.",
    },
    {
        "key": "workflows",
        "label": "Workflows",
        "summary": "Reusable repo-level workflows for UI, tests, docs, refactors, CI/CD, and context upkeep.",
    },
    {
        "key": "research",
        "label": "Research",
        "summary": "Research routing and evidence creation before implementation.",
    },
    {
        "key": "platforms",
        "label": "Platforms",
        "summary": "Vendor and platform integrations such as GitHub, Vercel, Supabase, Stripe, and Sentry.",
    },
    {
        "key": "browser-design",
        "label": "Browser & design",
        "summary": "Browser automation, Figma, and frontend runtime drill-down pages.",
    },
    {
        "key": "native",
        "label": "Native",
        "summary": "iOS, macOS, and Android development/testing capability front doors.",
    },
]

GROUP_LABELS = {item["key"]: item["label"] for item in CAPABILITY_GROUPS}
MAX_TOP_LEVEL_GROUPS = 8
MAX_GROUP_ITEMS = 25

CAPABILITY_CLOUD_READINESS = {
    "autonomous-deep-runs": [],
    "skills-management": ["skills wrapper layer"],
    "agentcli-maintenance": ["agent-cli-os core"],
    "plugin-evaluation": ["plugin-eval"],
    "repo-intelligence": ["agent-cli-os core"],
    "computer-intelligence": ["agent-cli-os core"],
    "research": ["research web", "research github", "research scout"],
    "code-review": ["coderabbit"],
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


def _group_specs_map() -> dict[str, dict[str, Any]]:
    return {item["key"]: item for item in CAPABILITY_GROUPS}


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


def _python_user_script_candidates(name: str) -> list[str]:
    userbase = site.getuserbase()
    if os.name == "nt":
        script_dirs: list[str] = [ntpath.join(userbase, "Scripts")]
        usersite = site.getusersitepackages()
        if usersite:
            script_dirs.append(ntpath.join(ntpath.dirname(usersite), "Scripts"))
        try:
            for candidate in Path(userbase).glob("Python*"):
                if candidate.is_dir():
                    script_dirs.append(ntpath.join(str(candidate), "Scripts"))
        except (OSError, NotImplementedError):
            pass

        candidates: list[str] = []
        seen: set[str] = set()
        for scripts_dir in script_dirs:
            for candidate in (
                ntpath.join(scripts_dir, f"{name}.exe"),
                ntpath.join(scripts_dir, f"{name}.cmd"),
                ntpath.join(scripts_dir, f"{name}.bat"),
                ntpath.join(scripts_dir, name),
            ):
                if candidate not in seen:
                    seen.add(candidate)
                    candidates.append(candidate)
        return candidates

    scripts_dir = Path(userbase) / "bin"
    return [str(scripts_dir / name)]


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
            if Path(candidate).exists():
                path = candidate
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

    help_result = run_command([path, "--help"], timeout=20)
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


def _plugin_payload(plugins: dict[str, Any], name: str) -> dict[str, Any] | None:
    candidates = [name]
    if name == PUBLIC_PRODUCT_NAME:
        candidates.extend(LEGACY_PLUGIN_NAMES)
    if name.endswith("@openai-curated"):
        candidates.append(name.split("@", 1)[0])
    else:
        candidates.append(f"{name}@openai-curated")
    for candidate in candidates:
        item = plugins.get(candidate)
        if item:
            return item
    return None


def _plugin_status(plugins: dict[str, Any], name: str) -> str:
    item = _plugin_payload(plugins, name)
    if not item:
        return "missing"
    if item.get("status") in {"ok", "configured"}:
        return "ok"
    return "ok" if item.get("enabled") or item.get("configured") else "disabled"


def _mcp_status(mcp_servers: dict[str, Any], name: str) -> str:
    item = mcp_servers.get(name)
    if not item:
        return "missing"
    return item.get("status", "configured")


def _skill_status(local_skill_names: set[str], plugins: dict[str, Any], name: str) -> str:
    if name in local_skill_names:
        return "ok"
    if ":" in name:
        plugin_name = name.split(":", 1)[0]
        if _plugin_status(plugins, plugin_name) == "ok" or _plugin_status(plugins, f"{plugin_name}@openai-curated") == "ok":
            return "ok"
    return "missing"


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
        payload = _plugin_payload(plugins, name)
        return {
            "kind": kind,
            "name": name,
            "status": _plugin_status(plugins, name),
            "enabled": bool(payload and (payload.get("enabled") or payload.get("configured") or payload.get("status") in {"ok", "configured"})),
        }
    if kind == "mcp":
        payload = mcp_servers.get(name)
        return {"kind": kind, "name": name, "status": _mcp_status(mcp_servers, name), "configured": bool(payload)}
    if kind == "skill":
        return {"kind": kind, "name": name, "status": _skill_status(local_skill_names, plugins, name)}
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
        {"kind": "skill", "name": name, "status": _skill_status(local_skill_names, plugins, name)}
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


def _inventory_items(payload: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [item for item in payload.get("items", []) if item.get("kind") == kind]


def _inventory_skills(payload: dict[str, Any]) -> dict[str, Any]:
    global_items = [
        item
        for item in _inventory_items(payload, "skill")
        if item.get("source_scope") == "user" and item.get("source_hint") == "npx skills ls -g"
    ]
    return {"status": payload.get("summary", {}).get("status", "unknown"), "items": [{"name": item["name"]} for item in global_items]}


def _inventory_local_skill_names(payload: dict[str, Any]) -> set[str]:
    return {
        item["name"]
        for item in _inventory_items(payload, "skill")
        if item.get("source_scope") in {"user", "repo", "plugin"}
    }


def _cached_plugin_roots(plugin_name: str) -> list[Path]:
    cache_root = PLUGINS_DIR / "cache"
    if not cache_root.exists():
        return []
    roots: list[Path] = []
    for marketplace_dir in sorted(path for path in cache_root.iterdir() if path.is_dir()):
        plugin_dir = marketplace_dir / plugin_name
        if not plugin_dir.exists():
            continue
        roots.extend(sorted(path for path in plugin_dir.iterdir() if path.is_dir()))
    return roots


def _detect_plugin_eval() -> dict[str, Any]:
    record = _tool_record("plugin-eval", command="plugin-eval", version_args=["--help"])
    if record["installed"]:
        return record

    node_path = command_path("node")
    script_candidates = [root / "scripts" / "plugin-eval.js" for root in _cached_plugin_roots("plugin-eval")]
    script_path = next((path for path in script_candidates if path.exists()), None)

    fallback: dict[str, Any] = {
        "name": "plugin-eval",
        "command": "plugin-eval",
        "path": str(script_path) if script_path else None,
        "installed": bool(script_path),
        "detect_only": False,
        "version": None,
        "auth": "unknown",
        "status": "missing",
    }
    if not script_path:
        return fallback
    if not node_path:
        fallback["status"] = "degraded"
        fallback["runtime_error"] = "Node.js is required to run the bundled Plugin Eval CLI."
        return fallback

    help_result = run_command([node_path, str(script_path), "--help"], timeout=20)
    package_path = script_path.parent.parent / "package.json"
    package_version: str | None = None
    if package_path.exists():
        try:
            payload = json.loads(package_path.read_text(encoding="utf-8"))
            raw_version = payload.get("version")
            if isinstance(raw_version, str) and raw_version.strip():
                package_version = raw_version.strip()
        except json.JSONDecodeError:
            package_version = None
    if help_result["ok"]:
        output_lines = (help_result["stdout"] or help_result["stderr"] or "").splitlines()
        fallback["status"] = "ok"
        fallback["command"] = f'node "{script_path}"'
        fallback["version"] = f"bundled {package_version}" if package_version else (output_lines[0] if output_lines else "bundled plugin-eval script")
        fallback["wrapper_ready"] = True
        return fallback

    fallback["status"] = "degraded"
    fallback["command"] = f'node "{script_path}"'
    fallback["wrapper_ready"] = False
    fallback["runtime_error"] = help_result["stderr"] or help_result["stdout"] or "failed to execute bundled Plugin Eval CLI"
    return fallback


def _inventory_plugins_map(payload: dict[str, Any]) -> dict[str, Any]:
    return {item["name"]: item for item in _inventory_items(payload, "plugin")}


def _inventory_apps_map(payload: dict[str, Any]) -> dict[str, Any]:
    return {item["name"]: item for item in _inventory_items(payload, "app")}


def _inventory_mcp_map(payload: dict[str, Any]) -> dict[str, Any]:
    return {item["name"]: item for item in _inventory_items(payload, "mcp")}


def build_capabilities_report(*, inventory_snapshot: dict[str, Any] | None = None, refresh_inventory: bool = False) -> dict[str, Any]:
    inventory = inventory_snapshot or load_inventory_snapshot(refresh=refresh_inventory)
    tools = inventory.get("tool_map", {})
    installed_skills = _inventory_skills(inventory)
    plugins = _inventory_plugins_map(inventory)
    apps = _inventory_apps_map(inventory)
    mcp_servers = _inventory_mcp_map(inventory)
    local_skill_names = _inventory_local_skill_names(inventory)
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
    detect_only_tools = [name for name in ("aws", "az", "firebase", "gcloud") if name in tools and tools[name]["installed"]]
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
    combined_statuses = required_tool_statuses | required_capability_statuses | {inventory.get("summary", {}).get("status", "ok")}
    summary_status = "error" if "error" in combined_statuses else "degraded" if "degraded" in combined_statuses or "missing" in combined_statuses or "disabled" in combined_statuses else "ok"

    required_capability_count = sum(1 for entry in capabilities if entry.get("required", True))
    optional_capability_count = len(capabilities) - required_capability_count
    optional_attention_count = sum(1 for entry in capabilities if not entry.get("required", True) and entry.get("status") != "ok")
    grouped = _grouped_capabilities({"capabilities": capabilities})
    capability_groups = [
        {
            **group_spec,
            "count": len(grouped.get(group_spec["key"], [])),
            "items": [item["key"] for item in grouped.get(group_spec["key"], [])],
        }
        for group_spec in CAPABILITY_GROUPS
    ]
    visible_group_count = sum(1 for group in capability_groups if group["count"])
    max_group_size = max((group["count"] for group in capability_groups), default=0)

    return {
        "schema_version": 2,
        "generated_at": utc_now(),
        "codex_home": str(Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).resolve()),
        "inventory_path": str((Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).resolve() / "agentctl" / "state" / "inventory.json")),
        "inventory_summary": inventory.get("summary", {}),
        "summary": {
            "status": summary_status,
            "installed_skill_count": len(installed_skills["items"]),
            "local_skill_count": len(local_skill_names),
            "enabled_plugin_count": sum(1 for item in plugins.values() if item.get("enabled")),
            "configured_app_count": sum(
                1
                for item in apps.values()
                if item.get("configured") or item.get("status") in {"ok", "configured", "degraded"}
            ),
            "app_item_count": len(apps),
            "configured_mcp_count": len(mcp_servers),
            "global_skills_dir": str(SKILLS_DIR),
            "required_capability_count": required_capability_count,
            "optional_capability_count": optional_capability_count,
            "optional_attention_count": optional_attention_count,
            "visible_group_count": visible_group_count,
            "max_group_size": max_group_size,
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
        "apps": {
            "status": "ok",
            "items": sorted(apps.values(), key=lambda item: item["name"]),
        },
        "mcp_servers": {
            "status": "ok",
            "items": sorted(mcp_servers.values(), key=lambda item: item["name"]),
        },
        "tools": tools,
        "capabilities": capabilities,
        "capability_groups": capability_groups,
        "menu_budget": {
            "max_top_level_groups": MAX_TOP_LEVEL_GROUPS,
            "max_group_items": MAX_GROUP_ITEMS,
        },
        "overlap_analysis": overlap_analysis,
        "detect_only_tools": detect_only_tools,
    }


def capability_doc_path(key: str) -> Path:
    return AGENTCTL_CAPABILITIES_DOCS_DIR / f"{key}.md"


def capability_keys(payload: dict[str, Any]) -> list[str]:
    return [item["key"] for item in payload.get("capabilities", [])]


def capability_detail(payload: dict[str, Any], key: str) -> dict[str, Any] | None:
    group_spec = _group_specs_map().get(key)
    if group_spec:
        grouped = _grouped_capabilities(payload)
        items = grouped.get(key, [])
        return {
            "kind": "group",
            "key": key,
            "label": group_spec["label"],
            "status": "ok",
            "summary": group_spec["summary"],
            "doc_path": str(capability_doc_path(key)),
            "items": items,
            "menu_budget": payload.get("menu_budget", {}),
        }

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
        "kind": "capability",
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
    grouped: dict[str, list[dict[str, Any]]] = {group["key"]: [] for group in CAPABILITY_GROUPS}
    spec_order = {spec["key"]: index for index, spec in enumerate(CAPABILITY_SPECS)}
    for item in payload.get("capabilities", []):
        group_key = item.get("group", "other")
        grouped.setdefault(group_key, []).append(item)
    for items in grouped.values():
        items.sort(key=lambda item: (_status_rank(item.get("status", "unknown")), spec_order.get(item.get("key"), 9999), item.get("label", item.get("key", "unknown"))))
    return grouped


def _group_status(items: list[dict[str, Any]]) -> str:
    statuses = {item.get("status", "unknown") for item in items}
    if "error" in statuses:
        return "error"
    if "degraded" in statuses or "missing" in statuses or "disabled" in statuses:
        return "degraded"
    return "ok"


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
    launcher = payload.get("public_launcher", {})
    if launcher and launcher.get("status") != "ok":
        notes.append(launcher.get("detail", f"`{PUBLIC_COMMAND}` is not resolving from PATH cleanly."))
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
    guidance = payload.get("guidance_snapshot", {})
    if guidance and not guidance.get("summary", {}).get("within_budget", True):
        notes.append("Personal guidance snippets exceed the configured budget; trim files or line count so the control plane stays compact.")
    inventory = payload.get("inventory_snapshot", {})
    if inventory and inventory.get("summary", {}).get("status") == "degraded":
        notes.append(f"The autodetected inventory is degraded; inspect `{PUBLIC_COMMAND} inventory show` before trusting route coverage.")
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
    visible_groups = payload.get("capability_groups") or [
        {
            "key": group["key"],
            "label": group["label"],
            "count": len(grouped.get(group["key"], [])),
        }
        for group in CAPABILITY_GROUPS
    ]
    known_group_keys = {group["key"] for group in visible_groups}
    for group_key, items in grouped.items():
        if group_key in known_group_keys or not items:
            continue
        visible_groups.append(
            {
                "key": group_key,
                "label": GROUP_LABELS.get(group_key, group_key.replace("-", " ").title()),
                "count": len(items),
            }
        )
    for group in visible_groups:
        group_key = group["key"]
        items = grouped.get(group_key, [])
        if not items:
            continue
        print(
            f"- {group.get('label', GROUP_LABELS.get(group_key, group_key.replace('-', ' ').title()))} "
            f"[{_group_status(items)}] {len(items)} items"
        )
    print("")
    print(f"Use `{PUBLIC_COMMAND} capability <key>` for a group page or a single capability drill-down page.")
    print(f"Use `{PUBLIC_COMMAND} skill-map` for the human-facing map of local front-door skills versus the much larger plugin catalog.")
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

    if payload.get("kind") == "group":
        print(f"Group: {payload['label']} (`{payload['key']}`)")
        print(f"Doc page: `{payload['doc_path']}`")
        print("")
        print(payload["summary"])
        print("")
        print("Items")
        for item in payload.get("items", []):
            optional_tag = " optional" if not item.get("required", True) else ""
            print(f"- {item['key']}: `{item['front_door']}` [{item['status']}{optional_tag}]")
        print("")
        print("Menu budget")
        budget = payload.get("menu_budget", {})
        print(f"- top-level groups: <= {budget.get('max_top_level_groups', MAX_TOP_LEVEL_GROUPS)}")
        print(f"- items per group page: <= {budget.get('max_group_items', MAX_GROUP_ITEMS)}")
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
