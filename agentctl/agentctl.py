#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from lib.capabilities import (
    build_capabilities_report,
    print_capabilities_human,
    print_doctor_human,
    print_research_human,
    print_skills_human,
    print_status_human,
)
from lib.common import save_json
from lib.maintenance import (
    maintenance_audit,
    maintenance_check,
    maintenance_fix_docs,
    maintenance_render_report,
    print_maintenance_human,
)
from lib.paths import CAPABILITIES_PATH, DOCTOR_REPORT_PATH
from lib.research import run_research
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
        ("fix-docs", "Regenerate the human-facing agentctl docs from current machine state"),
        ("render-report", "Render the maintenance Markdown page and JSON report"),
    ):
        parser = maintenance_subparsers.add_parser(command_name, help=help_text)
        parser.add_argument("--json", action="store_true", help="Emit JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex-first control plane for skills, workflows, and CLI-backed research.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Check installed tools, wrappers, and auth health")
    doctor_parser.add_argument("--json", action="store_true", help="Emit JSON")

    capabilities_parser = subparsers.add_parser("capabilities", help="Emit the machine-readable capability inventory")
    capabilities_parser.add_argument("--json", action="store_true", help="Emit JSON")

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

    maintenance_parser = subparsers.add_parser("maintenance", help="Audit and refresh agentctl's own docs, packaging, and state")
    add_maintenance_subcommands(maintenance_parser)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command in {"doctor", "capabilities"}:
        report = build_capabilities_report()
        save_json(CAPABILITIES_PATH, report)
        save_json(DOCTOR_REPORT_PATH, report)
        if args.command == "doctor":
            print_doctor_human(report, as_json=args.json)
        else:
            print_capabilities_human(report, as_json=args.json)
        return 0 if report["summary"]["status"] != "error" else 1

    if args.command == "status":
        result = workflow_status(repo=args.repo, use_registry=args.all)
        print_status_human(result, as_json=args.json)
        return 0 if result["summary"]["status"] != "error" else 1

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
        if args.maintenance_command == "check":
            result = maintenance_check()
        elif args.maintenance_command == "audit":
            result = maintenance_audit()
        elif args.maintenance_command == "fix-docs":
            result = maintenance_fix_docs()
        elif args.maintenance_command == "render-report":
            result = maintenance_render_report()
        else:  # pragma: no cover
            parser.error(f"unknown maintenance command: {args.maintenance_command}")
        print_maintenance_human(result, as_json=getattr(args, "json", False))
        return 0 if result["summary"]["status"] == "ok" else 1

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
