from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def _fetch_release_metadata(package: str) -> dict | None:
    url = f"https://pypi.org/pypi/{package}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def wait_for_release(package: str, version: str, *, timeout: int, interval: int) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        payload = _fetch_release_metadata(package)
        if payload:
            releases = payload.get("releases", {})
            files = releases.get(version) or []
            if files:
                return True
        time.sleep(interval)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Wait for a specific package version to appear on PyPI."
    )
    parser.add_argument("--package", required=True, help="PyPI package name")
    parser.add_argument("--version", required=True, help="Expected version")
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Maximum number of seconds to wait before failing.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Number of seconds between PyPI checks.",
    )
    args = parser.parse_args()

    if wait_for_release(args.package, args.version, timeout=args.timeout, interval=args.interval):
        print(f"{args.package}=={args.version} is available on PyPI")
        return 0

    print(
        f"{args.package}=={args.version} did not become available on PyPI within {args.timeout} seconds",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
