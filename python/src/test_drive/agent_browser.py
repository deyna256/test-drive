"""Find the browser CLI version used by Test Drive."""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def runtime_directory() -> Path:
    return Path(
        os.environ.get("TEST_DRIVE_RUNTIME_DIR") or Path.home() / ".test-drive" / "agent-browser"
    ).expanduser()


def runtime_browser(directory: Path) -> Path:
    return (
        directory
        / "node_modules"
        / ".bin"
        / ("agent-browser.cmd" if os.name == "nt" else "agent-browser")
    )


def main() -> int:
    argparse.ArgumentParser(description="Find a compatible agent-browser CLI").parse_args()
    managed = runtime_browser(runtime_directory())
    browser = os.environ.get("TEST_DRIVE_AGENT_BROWSER") or (
        str(managed) if managed.is_file() else shutil.which("agent-browser")
    )
    if not browser:
        print(
            "agent-browser >=0.40.0 was not found; set TEST_DRIVE_AGENT_BROWSER to its executable path.",
            file=sys.stderr,
        )
        return 1

    try:
        path = Path(browser).expanduser().resolve(strict=True)
        result = subprocess.run(
            [str(path), "--version"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"Cannot run agent-browser at {browser}: {exc}", file=sys.stderr)
        return 1

    version = result.stdout.strip()
    match = re.fullmatch(
        r"agent-browser (0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\+[0-9A-Za-z.-]+)?", version
    )
    if result.returncode != 0 or not match or tuple(map(int, match.groups())) < (0, 40, 0):
        print(
            f"Test Drive requires a stable agent-browser >=0.40.0; {path} reported {version or 'no version'}.",
            file=sys.stderr,
        )
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
