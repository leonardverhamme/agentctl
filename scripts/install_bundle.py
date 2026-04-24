from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentctl.bundle_install import (  # noqa: E402
    BUNDLE_ITEMS,
    cleanup_legacy_plugin,
    copy_item,
    default_codex_home,
    ensure_plugin_enabled,
    evaluate_post_check,
    install_bundle,
    repo_root,
    run_post_install_checks,
)
from agentctl.lib.branding import PUBLIC_COMMAND, PUBLIC_DISPLAY_NAME  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Install the {PUBLIC_DISPLAY_NAME} bundle into a CODEX_HOME directory.")
    parser.add_argument("--codex-home", help="Target CODEX_HOME. Defaults to $CODEX_HOME or ~/.codex")
    parser.add_argument("--skip-post-checks", action="store_true", help="Skip post-install doctor/capabilities/maintenance checks")
    parser.add_argument("--publish-shims", dest="publish_shims", action="store_true", help="Force publishing PATH launcher shims after install")
    parser.add_argument("--no-publish-shims", dest="publish_shims", action="store_false", help="Skip publishing PATH launcher shims after install")
    parser.set_defaults(publish_shims=None)
    args = parser.parse_args()

    source_root = repo_root()
    target_root = Path(args.codex_home).resolve() if args.codex_home else default_codex_home()
    summary = install_bundle(
        source_root=source_root,
        target_root=target_root,
        skip_post_checks=args.skip_post_checks,
        publish_shims=args.publish_shims,
    )

    print(f"Installed {PUBLIC_DISPLAY_NAME} into {target_root}")
    print(f"Run: python {target_root / 'agentctl' / 'agentctl.py'} doctor")
    print(f"Primary command: {PUBLIC_COMMAND}")
    launchers = summary.get("launchers")
    if isinstance(launchers, dict) and launchers.get("launcher_dir"):
        print(f"Launcher shims: {launchers['status']} | {launchers['launcher_dir']}")
    if args.skip_post_checks:
        print("Post-install checks: skipped")
        return 0
    print(f"Post-install checks: {summary['status']}")
    print(f"Bootstrap report: {target_root / 'agentctl' / 'state' / 'bootstrap-report.json'}")
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
