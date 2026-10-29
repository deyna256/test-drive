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


def runtime_browsers(directory: Path) -> list[Path]:
    """The native binary, then the npm layout that version 0.1 of this package installed."""
    windows = os.name == "nt"
    return [
        directory / ("agent-browser.exe" if windows else "agent-browser"),
        directory / "node_modules" / ".bin" / ("agent-browser.cmd" if windows else "agent-browser"),
    ]


def check(browser: str | Path) -> tuple[Path | None, str]:
    """Return the resolved path of a compatible browser CLI, or why it is not one."""
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
        return None, f"Cannot run agent-browser at {browser}: {exc}"

    version = result.stdout.strip()
    match = re.fullmatch(
        r"agent-browser (0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\+[0-9A-Za-z.-]+)?", version
    )
    if result.returncode != 0 or not match or tuple(map(int, match.groups())) < (0, 40, 0):
        return None, (
            f"Test Drive requires a stable agent-browser >=0.40.0; {path} reported {version or 'no version'}."
        )
    return path, ""


def find() -> tuple[Path | None, str]:
    """Check the configured browser, else the first compatible managed or PATH browser."""
    configured = os.environ.get("TEST_DRIVE_AGENT_BROWSER")
    if configured:
        return check(configured)
    candidates = [path for path in runtime_browsers(runtime_directory()) if path.is_file()]
    on_path = shutil.which("agent-browser")
    if on_path:
        candidates.append(Path(on_path))
    error = "agent-browser >=0.40.0 was not found; run test-drive setup-agent-browser or set TEST_DRIVE_AGENT_BROWSER to its executable path."
    for candidate in candidates:
        path, reason = check(candidate)
        if path:
            return path, ""
        error = reason
    return None, error


def main() -> int:
    argparse.ArgumentParser(description="Find a compatible agent-browser CLI").parse_args()
    path, error = find()
    if not path:
        print(error, file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
