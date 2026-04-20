from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentctl.lib.branding import COMPATIBILITY_COMMAND, LEGACY_COMMAND, PUBLIC_COMMAND, PUBLIC_DOCS_DIRNAME, PUBLIC_DISPLAY_NAME, RELEASE_BUNDLE_PREFIX


BUNDLE_ITEMS = [
    "agentctl",
    "workflow-tools",
    "skills",
    "plugins",
    f"docs/{PUBLIC_DOCS_DIRNAME}",
    "scripts",
    "AGENTS.md",
    f"{PUBLIC_COMMAND}.cmd",
    f"{PUBLIC_COMMAND}.sh",
    f"{COMPATIBILITY_COMMAND}.cmd",
    f"{COMPATIBILITY_COMMAND}.sh",
    f"{LEGACY_COMMAND}.cmd",
    f"{LEGACY_COMMAND}.sh",
    "README.md",
    "LICENSE",
    "config.toml",
    "pyproject.toml",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def add_path(bundle: zipfile.ZipFile, source_root: Path, relative: str) -> None:
    source = source_root / relative
    if source.is_dir():
        for child in sorted(path for path in source.rglob("*") if path.is_file()):
            bundle.write(child, child.relative_to(source_root))
    else:
        bundle.write(source, source.relative_to(source_root))


def sha256_for(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Build a zip release bundle for {PUBLIC_DISPLAY_NAME}.")
    parser.add_argument("--version", required=True, help="Version label used in the zip filename, e.g. v1.0.0")
    parser.add_argument("--output-dir", default="dist", help="Output directory for the bundle")
    args = parser.parse_args()

    source_root = repo_root()
    output_dir = (source_root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    archive_path = output_dir / f"{RELEASE_BUNDLE_PREFIX}-{args.version}.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for relative in BUNDLE_ITEMS:
            add_path(bundle, source_root, relative)

    digest = sha256_for(archive_path)
    digest_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    digest_path.write_text(f"{digest}  {archive_path.name}\n", encoding="utf-8")

    print(str(archive_path))
    print(str(digest_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
