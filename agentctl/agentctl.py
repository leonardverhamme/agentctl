#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from .bundle_install import default_codex_home, public_launcher_health, repair_install, upgrade_bundle
    from .lib.branding import COMPATIBILITY_COMMAND, PUBLIC_COMMAND, PUBLIC_DISPLAY_NAME
    from .lib.capabilities import (
        build_capabilities_report,
        capability_detail,
        print_capabilities_human,
        print_capability_human,
        print_doctor_human,
        print_research_human,
        print_skills_human,
        print_status_human,
    )
    from .lib.common import print_json, save_json
    from .lib.computer_intel import (
        computer_intel_refresh,
        computer_intel_search,
        computer_intel_status,
        print_computer_intel_human,
    )
    from .lib.config_layers import (
        config_path_payload,
        config_snapshot,
        parse_value,
        print_config_human,
        repair_user_config,
        set_config_value,
        unset_config_value,
    )
    from .lib.guidance import load_guidance_snapshot
    from .lib.overview import build_overview_report, print_overview_human
    from .lib.inventory import (
        filter_inventory_items,
        inventory_item,
        load_inventory_snapshot,
        print_inventory_human,
        refresh_inventory_snapshot,
    )
    from .lib.maintenance import (
        maintenance_audit,
        maintenance_check,
        maintenance_fix_docs,
        maintenance_render_report,
        print_maintenance_human,
    )
    from .lib.paths import CAPABILITIES_PATH, DOCTOR_REPORT_PATH
    from .lib.repo_intel import (
        print_repo_intel_human,
        repo_intel_audit,
        repo_intel_ensure,
        repo_intel_query,
        repo_intel_serve,
        repo_intel_status,
        repo_intel_update,
    )
    from .lib.research import run_research
    from .lib.self_check import build_self_check, print_self_check, wrapper_version
    from .lib.skill_map import print_skill_map_human, write_skill_map_docs
    from .lib.skills_ops import add_skill, check_skills, list_skills, update_skills
    from .lib.workflows import run_workflow, workflow_status
except ImportError:
    from bundle_install import default_codex_home, public_launcher_health, repair_install, upgrade_bundle
    from lib.branding import COMPATIBILITY_COMMAND, PUBLIC_COMMAND, PUBLIC_DISPLAY_NAME
    from lib.capabilities import (
        build_capabilities_report,
        capability_detail,
        print_capabilities_human,
        print_capability_human,
        print_doctor_human,
        print_research_human,
        print_skills_human,
        print_status_human,
    )
    from lib.common import print_json, save_json
    from lib.computer_intel import (
        computer_intel_refresh,
        computer_intel_search,
        computer_intel_status,
        print_computer_intel_human,
    )
    from lib.config_layers import (
        config_path_payload,
        config_snapshot,
        parse_value,
        print_config_human,
        repair_user_config,
        set_config_value,
        unset_config_value,
    )
    from lib.guidance import load_guidance_snapshot
    from lib.overview import build_overview_report, print_overview_human
    from lib.inventory import (
        filter_inventory_items,
        inventory_item,
        load_inventory_snapshot,
        print_inventory_human,
        refresh_inventory_snapshot,
    )
    from lib.maintenance import (
        maintenance_audit,
        maintenance_check,
        maintenance_fix_docs,
        maintenance_render_report,
        print_maintenance_human,
    )
    from lib.paths import CAPABILITIES_PATH, DOCTOR_REPORT_PATH
    from lib.repo_intel import (
        print_repo_intel_human,
        repo_intel_audit,
        repo_intel_ensure,
        repo_intel_query,
        repo_intel_serve,
        repo_intel_status,
        repo_intel_update,
    )
    from lib.research import run_research
    from lib.self_check import build_self_check, print_self_check, wrapper_version
    from lib.skill_map import print_skill_map_human, write_skill_map_docs
    from lib.skills_ops import add_skill, check_skills, list_skills, update_skills
    from lib.workflows import run_workflow, workflow_status


def add_skills_subcommands(skills_parser: argparse.ArgumentParser) -> None:
    skills_subparsers = skills_parser.add_subparsers(dest="skills_command", required=True)

    list_parser = skills_subparsers.add_parser("list", help="List installed skills")
    list_parser.add_argument("--project", action="store_true", help="List project skills instead of global skills")
    list_parser.add_argument("--json", action="store_true", help="Emit JSON")

    add_parser = skills_subparsers.add_parser("add", help="Install skills through the official skills CLI")
    add_parser.add_argument("source", help="Skill source, e.g. owner/repo or local path")
    add_parser.add_argument("--skill", dest="skill_names", action="append", help="Specific skill to install")
    add_parser.add_argument("--ref", help="Optional tag, branch, or commit SHA to pin")
    add_parser.add_argument("--project", action="store_true", help="Install to project scope instead of global")
    add_parser.add_argument("--json", action="store_true", help="Emit JSON")

    check_parser = skills_subparsers.add_parser("check", help="Compare installed skills with the local lock file")
    check_parser.add_argument("--project", action="store_true", help="Check project skills instead of global skills")
    check_parser.add_argument("--json", action="store_true", help="Emit JSON")

    update_parser = skills_subparsers.add_parser("update", help="Safely refresh tracked skills from the lock file")
    update_parser.add_argument("--project", action="store_true", help="Update project-scoped tracked skills")
    update_parser.add_argument("--json", action="store_true", help="Emit JSON")


def add_maintenance_subcommands(maintenance_parser: argparse.ArgumentParser) -> None:
    maintenance_subparsers = maintenance_parser.add_subparsers(dest="maintenance_command", required=True)
    for command_name, help_text in (
        ("check", "Check command/docs/plugin drift and update machine-readable maintenance state"),
        ("audit", "Run the full maintenance pass, refresh docs, and update maintenance state"),
        ("fix-docs", f"Regenerate the human-facing {PUBLIC_DISPLAY_NAME} docs from current machine state"),
        ("render-report", "Render the maintenance Markdown page and JSON report"),
    ):
        parser = maintenance_subparsers.add_parser(command_name, help=help_text)
        parser.add_argument("--json", action="store_true", help="Emit JSON")


def add_config_subcommands(config_parser: argparse.ArgumentParser) -> None:
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)

    show_parser = config_subparsers.add_parser("show", help="Show effective or layered config")
    show_parser.add_argument("--repo", help="Repo root for repo-local config resolution")
    show_parser.add_argument("--json", action="store_true", help="Emit JSON")

    path_parser = config_subparsers.add_parser("path", help="Show the path for one config scope")
    path_parser.add_argument("--scope", choices=("bundled", "user", "repo"), default="user")
    path_parser.add_argument("--repo", help="Repo root for repo-local config resolution")
    path_parser.add_argument("--json", action="store_true", help="Emit JSON")

    for command_name, help_text in (("set", "Set one config key"), ("unset", "Unset one config key")):
        parser = config_subparsers.add_parser(command_name, help=help_text)
        parser.add_argument("key", help="Dotted config key, e.g. worker.mode")
        if command_name == "set":
            parser.add_argument("value", help="Config value")
        parser.add_argument("--scope", choices=("user", "repo"), default="user")
        parser.add_argument("--repo", help="Repo root for repo-local config resolution")
        parser.add_argument("--json", action="store_true", help="Emit JSON")


def add_inventory_subcommands(inventory_parser: argparse.ArgumentParser) -> None:
    inventory_subparsers = inventory_parser.add_subparsers(dest="inventory_command", required=True)

    refresh_parser = inventory_subparsers.add_parser("refresh", help="Refresh and persist the autodetected inventory snapshot")
    refresh_parser.add_argument("--repo", help="Repo root for repo-local inventory resolution")
    refresh_parser.add_argument("--json", action="store_true", help="Emit JSON")

    show_parser = inventory_subparsers.add_parser("show", help="Show the raw autodetected inventory")
    show_parser.add_argument("--kind", choices=("tools", "skills", "plugins", "apps", "mcp", "all"), default="all")
    show_parser.add_argument("--scope", choices=("user", "repo", "all"), default="all")
    show_parser.add_argument("--repo", help="Repo root for repo-local inventory resolution")
    show_parser.add_argument("--json", action="store_true", help="Emit JSON")

    item_parser = inventory_subparsers.add_parser("item", help="Show one raw inventory record by kind:name")
    item_parser.add_argument("selector", help="Inventory selector, e.g. tool:gh or skill:github:github")
    item_parser.add_argument("--repo", help="Repo root for repo-local inventory resolution")
    item_parser.add_argument("--json", action="store_true", help="Emit JSON")


def add_skill_map_subcommands(skill_map_parser: argparse.ArgumentParser) -> None:
    skill_map_parser.add_argument("--repo", help="Repo root for repo-local inventory resolution")
    skill_map_parser.add_argument("--json", action="store_true", help="Emit JSON")


def add_repo_intel_subcommands(repo_intel_parser: argparse.ArgumentParser) -> None:
    repo_intel_subparsers = repo_intel_parser.add_subparsers(dest="repo_intel_command", required=True)

    status_parser = repo_intel_subparsers.add_parser("status", help="Inspect repo-intel health for one repo")
    status_parser.add_argument("--repo", help="Repo root. Defaults to the current working directory.")
    status_parser.add_argument("--json", action="store_true", help="Emit JSON")

    ensure_parser = repo_intel_subparsers.add_parser("ensure", help="Create or refresh repo-intel artifacts for one repo")
    ensure_parser.add_argument("--repo", help="Repo root. Defaults to the current working directory.")
    ensure_parser.add_argument("--json", action="store_true", help="Emit JSON")

    update_parser = repo_intel_subparsers.add_parser("update", help="Refresh repo-intel artifacts using the lightest valid Graphify path")
    update_parser.add_argument("--repo", help="Repo root. Defaults to the current working directory.")
    mode_group = update_parser.add_mutually_exclusive_group()
    mode_group.add_argument("--code-only", action="store_true", help="Run the code-only update path")
    mode_group.add_argument("--semantic", action="store_true", help="Run the semantic/full rebuild path")
    mode_group.add_argument("--full", action="store_true", help="Run a full rebuild")
    update_parser.add_argument("--json", action="store_true", help="Emit JSON")

    query_parser = repo_intel_subparsers.add_parser("query", help="Query the local repo graph through Graphify")
    query_parser.add_argument("question", nargs="+", help="Natural-language graph query")
    query_parser.add_argument("--repo", help="Repo root. Defaults to the current working directory.")
    query_parser.add_argument("--budget", type=int, default=1500, help="Token budget to pass through to Graphify")
    query_parser.add_argument("--dfs", action="store_true", help="Use Graphify's DFS traversal instead of BFS")
    query_parser.add_argument("--json", action="store_true", help="Emit JSON")

    audit_parser = repo_intel_subparsers.add_parser("audit", help="Audit repo-intel state for one repo, all trusted repos, or all discovered repos")
    audit_parser.add_argument("--repo", help="Repo root. Defaults to the current working directory.")
    audit_parser.add_argument("--all-trusted", action="store_true", help="Audit every trusted repo from the user config")
    audit_parser.add_argument("--all-discovered", action="store_true", help="Audit every discovered repo from the machine-wide computer-intel registry")
    audit_parser.add_argument("--fix", action="store_true", help="Run ensure for each audited repo instead of read-only status")
    audit_parser.add_argument("--json", action="store_true", help="Emit JSON")

    serve_parser = repo_intel_subparsers.add_parser("serve", help="Prepare or launch the local Graphify MCP server for the current repo graph")
    serve_parser.add_argument("--repo", help="Repo root. Defaults to the current working directory.")
    serve_parser.add_argument("--json", action="store_true", help="Emit JSON instead of launching the server")


def add_computer_intel_subcommands(computer_intel_parser: argparse.ArgumentParser) -> None:
    computer_intel_subparsers = computer_intel_parser.add_subparsers(dest="computer_intel_command", required=True)

    status_parser = computer_intel_subparsers.add_parser("status", help="Inspect machine-wide computer-intel state")
    status_parser.add_argument("--json", action="store_true", help="Emit JSON")

    refresh_parser = computer_intel_subparsers.add_parser("refresh", help="Refresh the machine-wide laptop discovery index")
    refresh_parser.add_argument("--json", action="store_true", help="Emit JSON")

    search_parser = computer_intel_subparsers.add_parser("search", help="Search the machine-wide laptop discovery surface")
    search_parser.add_argument("query", nargs="+", help="Natural-language or path-fragment query")
    search_parser.add_argument("--kind", choices=("all", "repo", "vault", "graph", "service", "root", "path"), default="all")
    search_parser.add_argument("--limit", type=int, default=40, help="Maximum number of registry matches to keep")
    search_parser.add_argument("--json", action="store_true", help="Emit JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{PUBLIC_DISPLAY_NAME} is the capability-first Codex control plane for workflows, research, and installable agent tooling.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Check installed tools, wrappers, and auth health")
    doctor_parser.add_argument("--fix", action="store_true", help="Repair common local install/config issues before reporting health")
    doctor_parser.add_argument("--json", action="store_true", help="Emit JSON")

    capabilities_parser = subparsers.add_parser("capabilities", help="Emit the machine-readable capability inventory")
    capabilities_parser.add_argument("--json", action="store_true", help="Emit JSON")

    overview_parser = subparsers.add_parser("overview", help="Show a compact names-first overview of capabilities and local surface")
    overview_parser.add_argument("--repo", help="Repo root for repo-local inventory resolution")
    overview_parser.add_argument("--json", action="store_true", help="Emit JSON")

    capability_parser = subparsers.add_parser("capability", help="Show the drill-down page for a single capability")
    capability_parser.add_argument("key", help="Capability key, e.g. github-workflows")
    capability_parser.add_argument("--json", action="store_true", help="Emit JSON")

    status_parser = subparsers.add_parser("status", help="Inspect deep-workflow state")
    status_parser.add_argument("--repo", help="Repo root to inspect. Defaults to the current working directory.")
    status_parser.add_argument("--all", action="store_true", help="Read the global workflow registry instead of a single repo")
    status_parser.add_argument("--json", action="store_true", help="Emit JSON")

    run_parser = subparsers.add_parser("run", help="Launch or resume a deep workflow through the shared runner")
    run_parser.add_argument("workflow", help="Deep workflow name, e.g. ui-deep-audit")
    run_parser.add_argument("--repo", help="Repo root. Defaults to the current working directory.")
    run_parser.add_argument("--checklist", help="Optional checklist path override")
    run_parser.add_argument("--progress", help="Optional progress path override")
    run_parser.add_argument("--worker-command", help="Worker command used by the shared deep runner")
    run_parser.add_argument("--worker-mode", choices=("auto", "explicit", "codex"), default="auto", help="How agentctl should resolve the deep-workflow worker command")
    run_parser.add_argument("--max-iterations", type=int, default=30)
    run_parser.add_argument("--max-stagnant", type=int, default=3)

    loop_parser = subparsers.add_parser("loop", help="Run a generic long task through the shared disk-backed loop")
    loop_parser.add_argument("name", help="Workflow instance name, e.g. repo-cleanup")
    loop_parser.add_argument("--repo", help="Repo root. Defaults to the current working directory.")
    loop_parser.add_argument("--task", help="Task brief text for the loop")
    loop_parser.add_argument("--task-file", help="Existing task brief markdown file")
    loop_parser.add_argument("--checklist", help="Optional checklist path override")
    loop_parser.add_argument("--progress", help="Optional progress path override")
    loop_parser.add_argument("--worker-command", help="Worker command used by the shared loop runner")
    loop_parser.add_argument("--worker-mode", choices=("auto", "explicit", "codex"), default="auto", help="How the public CLI should resolve the loop worker command")
    loop_parser.add_argument("--max-iterations", type=int, default=30)
    loop_parser.add_argument("--max-stagnant", type=int, default=3)

    research_parser = subparsers.add_parser("research", help="Route research through the shared evidence contract")
    research_subparsers = research_parser.add_subparsers(dest="research_mode", required=True)
    for mode in ("web", "github", "scout"):
        mode_parser = research_subparsers.add_parser(mode, help=f"Run {mode} research")
        mode_parser.add_argument("query", nargs="+", help="Search query")
        mode_parser.add_argument("--limit", type=int, default=5, help="Maximum number of sources to keep")
        mode_parser.add_argument("--output-dir", help="Optional directory for evidence.json and brief.md")
        mode_parser.add_argument("--json-out", help="Optional explicit evidence.json path")
        mode_parser.add_argument("--brief-out", help="Optional explicit brief.md path")
        mode_parser.add_argument("--json", action="store_true", help="Emit JSON to stdout")

    skills_parser = subparsers.add_parser("skills", help="Wrap the official skills tooling with provenance and safety")
    add_skills_subcommands(skills_parser)

    maintenance_parser = subparsers.add_parser("maintenance", help=f"Audit and refresh {PUBLIC_DISPLAY_NAME}'s own docs, packaging, and state")
    add_maintenance_subcommands(maintenance_parser)

    config_parser = subparsers.add_parser("config", help="Inspect and update bundled, user, and repo config layers")
    add_config_subcommands(config_parser)

    inventory_parser = subparsers.add_parser("inventory", help="Inspect the raw autodetected inventory behind the curated capability menu")
    add_inventory_subcommands(inventory_parser)

    repo_intel_parser = subparsers.add_parser("repo-intel", help="Manage per-repo Graphify health, ensure/update flows, and workspace repo-intel audits")
    add_repo_intel_subcommands(repo_intel_parser)

    computer_intel_parser = subparsers.add_parser("computer-intel", help="Manage the machine-wide laptop discovery index without replacing per-repo Graphify graphs")
    add_computer_intel_subcommands(computer_intel_parser)

    skill_map_parser = subparsers.add_parser("skill-map", help="Generate the human-facing menu and skill map, plus a matching one-page PDF")
    add_skill_map_subcommands(skill_map_parser)

    upgrade_parser = subparsers.add_parser("upgrade", help=f"Upgrade the installed {PUBLIC_DISPLAY_NAME} bundle from its recorded release source")
    upgrade_parser.add_argument("--version", help="Optional explicit release version to install")
    upgrade_parser.add_argument("--skip-post-checks", action="store_true", help="Skip post-install checks")
    upgrade_parser.add_argument("--json", action="store_true", help="Emit JSON")

    self_check_parser = subparsers.add_parser("self-check", help="Compare wrapper version, bundle version, config schema, and plugin health")
    self_check_parser.add_argument("--repo", help="Repo root for repo-local config resolution")
    self_check_parser.add_argument("--json", action="store_true", help="Emit JSON")

    version_parser = subparsers.add_parser("version", help="Show wrapper and bundle version information")
    version_parser.add_argument("--json", action="store_true", help="Emit JSON")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command in {"doctor", "capabilities", "capability", "overview"}:
        repair_summary = None
        if args.command == "doctor" and getattr(args, "fix", False):
            repair_summary = {
                "install": repair_install(default_codex_home()),
                "config": repair_user_config(),
            }
        if args.command == "doctor":
            inventory = refresh_inventory_snapshot()
        elif args.command == "overview":
            inventory = refresh_inventory_snapshot(args.repo)
        else:
            inventory = load_inventory_snapshot()
        report = build_capabilities_report(inventory_snapshot=inventory)
        if args.command == "doctor":
            save_json(CAPABILITIES_PATH, report)
            guidance = load_guidance_snapshot(refresh=True)
            doctor_summary = dict(report.get("summary", {}))
            launcher_health = public_launcher_health()
            if not guidance.get("summary", {}).get("within_budget", True) and doctor_summary.get("status") == "ok":
                doctor_summary["status"] = "degraded"
            if launcher_health.get("status") != "ok" and doctor_summary.get("status") == "ok":
                doctor_summary["status"] = "degraded"
            if inventory.get("summary", {}).get("max_bucket_size", 0) > inventory.get("menu_budget", {}).get("max_items", 25):
                doctor_summary["status"] = "error"
            doctor_report = {
                **report,
                "summary": doctor_summary,
                "inventory_snapshot": inventory,
                "guidance_snapshot": guidance,
                "public_launcher": launcher_health,
            }
            if repair_summary is not None:
                doctor_report["repair"] = repair_summary
            save_json(DOCTOR_REPORT_PATH, doctor_report)
            print_doctor_human(doctor_report, as_json=args.json)
        elif args.command == "overview":
            overview = build_overview_report(capabilities_report=report, inventory_snapshot=inventory, repo=args.repo)
            print_overview_human(overview, as_json=args.json)
            return 0 if overview["summary"]["status"] != "error" else 1
        elif args.command == "capability":
            save_json(CAPABILITIES_PATH, report)
            detail = capability_detail(report, args.key)
            if detail is None:
                parser.error(f"unknown capability: {args.key}")
            print_capability_human(detail, as_json=args.json)
        else:
            save_json(CAPABILITIES_PATH, report)
            print_capabilities_human(report, as_json=args.json)
        return 0 if report["summary"]["status"] != "error" else 1

    if args.command == "status":
        result = workflow_status(repo=args.repo, use_registry=args.all)
        print_status_human(result, as_json=args.json)
        return 0 if result["summary"]["status"] != "error" else 1

    if args.command == "config":
        if args.config_command == "show":
            result = config_snapshot(args.repo)
        elif args.config_command == "path":
            result = config_path_payload(args.scope, repo=args.repo)
        elif args.config_command == "set":
            result = set_config_value(args.scope, args.key, parse_value(args.value), repo=args.repo)
        elif args.config_command == "unset":
            result = unset_config_value(args.scope, args.key, repo=args.repo)
        else:  # pragma: no cover
            parser.error(f"unknown config command: {args.config_command}")
        print_config_human(result, as_json=getattr(args, "json", False))
        return 0

    if args.command == "inventory":
        if args.inventory_command == "refresh":
            result = refresh_inventory_snapshot(args.repo)
        elif args.inventory_command == "show":
            result = filter_inventory_items(load_inventory_snapshot(args.repo), kind=args.kind, scope=args.scope)
        elif args.inventory_command == "item":
            result = inventory_item(load_inventory_snapshot(args.repo), args.selector)
            if result is None:
                parser.error(f"unknown inventory item: {args.selector}")
        else:  # pragma: no cover
            parser.error(f"unknown inventory command: {args.inventory_command}")
        print_inventory_human(result, as_json=getattr(args, "json", False))
        return 0

    if args.command == "repo-intel":
        if args.repo_intel_command == "status":
            result = repo_intel_status(args.repo)
            print_repo_intel_human(result, as_json=args.json)
            return 0 if result["status"] != "broken" else 1
        if args.repo_intel_command == "ensure":
            result = repo_intel_ensure(args.repo)
            print_repo_intel_human(result, as_json=args.json)
            return 0 if result["status"] in {"fresh", "disabled"} else 1
        if args.repo_intel_command == "update":
            mode = "auto"
            if args.code_only:
                mode = "code"
            elif args.semantic:
                mode = "semantic"
            elif args.full:
                mode = "full"
            result = repo_intel_update(args.repo, mode=mode)
            print_repo_intel_human(result, as_json=args.json)
            return 0 if result["status"] in {"fresh", "disabled"} else 1
        if args.repo_intel_command == "query":
            result = repo_intel_query(" ".join(args.question).strip(), repo=args.repo, budget=args.budget, dfs=args.dfs)
            print_repo_intel_human(result, as_json=args.json)
            return 0 if result.get("query_result", {}).get("ok", result["status"] not in {"broken", "missing", "disabled"}) else 1
        if args.repo_intel_command == "audit":
            result = repo_intel_audit(repo=args.repo, all_trusted=args.all_trusted, all_discovered=args.all_discovered, fix=args.fix)
            print_repo_intel_human(result, as_json=args.json)
            return 0 if result["summary"]["status"] == "ok" else 1
        if args.repo_intel_command == "serve":
            result = repo_intel_serve(args.repo, launch=not args.json)
            print_repo_intel_human(result, as_json=args.json)
            return 0 if result["status"] not in {"broken", "missing"} and result.get("action") != "blocked" else 1
        parser.error(f"unknown repo-intel command: {args.repo_intel_command}")

    if args.command == "computer-intel":
        if args.computer_intel_command == "status":
            result = computer_intel_status()
        elif args.computer_intel_command == "refresh":
            result = computer_intel_refresh()
        elif args.computer_intel_command == "search":
            result = computer_intel_search(" ".join(args.query).strip(), kind=args.kind, limit=args.limit)
        else:  # pragma: no cover
            parser.error(f"unknown computer-intel command: {args.computer_intel_command}")
        print_computer_intel_human(result, as_json=args.json)
        status = result.get("summary", {}).get("status", result.get("status", "ok"))
        return 0 if status not in {"error", "broken"} else 1

    if args.command == "skill-map":
        inventory = refresh_inventory_snapshot(args.repo)
        capabilities = build_capabilities_report(inventory_snapshot=inventory)
        result = write_skill_map_docs(capabilities, inventory, cwd=args.repo or Path.cwd())
        print_skill_map_human(result, as_json=args.json)
        return 0

    if args.command == "run":
        return run_workflow(
            workflow=args.workflow,
            repo=args.repo,
            checklist=args.checklist,
            progress=args.progress,
            worker_command=args.worker_command,
            worker_mode=args.worker_mode,
            max_iterations=args.max_iterations,
            max_stagnant=args.max_stagnant,
        )

    if args.command == "loop":
        if args.task and args.task_file:
            parser.error("use either --task or --task-file, not both")
        repo_root = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
        task_file = Path(args.task_file).resolve() if args.task_file else repo_root / ".codex-workflows" / args.name / "task.md"
        if args.task:
            task_file.parent.mkdir(parents=True, exist_ok=True)
            task_file.write_text(args.task.strip() + "\n", encoding="utf-8")
        elif not task_file.exists():
            parser.error("generic loops require --task or an existing --task-file")
        return run_workflow(
            workflow="loopsmith",
            workflow_name=args.name,
            skill_name="loopsmith",
            repo=str(repo_root),
            checklist=args.checklist,
            progress=args.progress,
            task_file=str(task_file),
            worker_command=args.worker_command,
            worker_mode=args.worker_mode,
            max_iterations=args.max_iterations,
            max_stagnant=args.max_stagnant,
        )

    if args.command == "research":
        result = run_research(
            mode=args.research_mode,
            query=" ".join(args.query).strip(),
            limit=args.limit,
            output_dir=args.output_dir,
            json_out=args.json_out,
            brief_out=args.brief_out,
        )
        print_research_human(result, as_json=args.json)
        return 0 if result["status"] != "error" else 1

    if args.command == "skills":
        if args.skills_command == "list":
            result = list_skills(global_scope=not args.project)
        elif args.skills_command == "add":
            result = add_skill(
                source=args.source,
                skill_names=args.skill_names or [],
                ref=args.ref,
                global_scope=not args.project,
            )
        elif args.skills_command == "check":
            result = check_skills(global_scope=not args.project)
        elif args.skills_command == "update":
            result = update_skills(global_scope=not args.project)
        else:  # pragma: no cover
            parser.error(f"unknown skills command: {args.skills_command}")
        print_skills_human(result, as_json=getattr(args, "json", False))
        return 0 if result.get("summary", {}).get("status", "ok") != "error" else 1

    if args.command == "maintenance":
        maintenance_cwd = Path.cwd()
        if args.maintenance_command == "check":
            result = maintenance_check(cwd=maintenance_cwd)
        elif args.maintenance_command == "audit":
            result = maintenance_audit(cwd=maintenance_cwd)
        elif args.maintenance_command == "fix-docs":
            result = maintenance_fix_docs(cwd=maintenance_cwd)
        elif args.maintenance_command == "render-report":
            result = maintenance_render_report(cwd=maintenance_cwd)
        else:  # pragma: no cover
            parser.error(f"unknown maintenance command: {args.maintenance_command}")
        print_maintenance_human(result, as_json=getattr(args, "json", False))
        return 0 if result["summary"]["status"] == "ok" else 1

    if args.command == "upgrade":
        result = upgrade_bundle(target_root=default_codex_home(), skip_post_checks=args.skip_post_checks, version=args.version)
        if args.json:
            print_json(result)
        else:
            print(f"Status: {result['status']}")
            print(f"Target: {result['target_codex_home']}")
            if result.get("install_metadata_path"):
                print(f"Install metadata: {result['install_metadata_path']}")
        return 0 if result["status"] == "ok" else 1

    if args.command == "self-check":
        inventory = refresh_inventory_snapshot(args.repo)
        guidance = load_guidance_snapshot(args.repo, refresh=True)
        capabilities = build_capabilities_report(inventory_snapshot=inventory)
        payload = build_self_check(capabilities, inventory=inventory, guidance=guidance, repo=args.repo)
        print_self_check(payload, as_json=args.json)
        return 0 if payload["status"] != "error" else 1

    if args.command == "version":
        inventory = load_inventory_snapshot()
        guidance = load_guidance_snapshot(refresh=False)
        capabilities = build_capabilities_report(inventory_snapshot=inventory)
        payload = build_self_check(capabilities, inventory=inventory, guidance=guidance)
        result = {
            "product": PUBLIC_DISPLAY_NAME,
            "public_command": PUBLIC_COMMAND,
            "compatibility_command": COMPATIBILITY_COMMAND,
            "wrapper_version": wrapper_version(),
            "bundle_version": payload.get("bundle_version"),
        }
        if args.json:
            print_json(result)
        else:
            print(f"{PUBLIC_DISPLAY_NAME} {result['wrapper_version'] or 'unknown'}")
            print(f"Bundle version: {result['bundle_version'] or 'unknown'}")
            print(f"Commands: `{PUBLIC_COMMAND}` (canonical), `{COMPATIBILITY_COMMAND}` (compatibility)")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
