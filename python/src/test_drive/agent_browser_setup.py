"""Set up the browser CLI without changing a global installation."""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .agent_browser import runtime_browser, runtime_directory


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up Test Drive's browser CLI")
    parser.add_argument("--directory", type=Path, default=runtime_directory())
    args = parser.parse_args()
    existing = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("agent_browser.py"))],
        capture_output=True,
        text=True,
        check=False,
    )
    if existing.returncode == 0:
        print(f"Using agent-browser: {existing.stdout.strip()}")
        return 0
    if os.environ.get("TEST_DRIVE_AGENT_BROWSER"):
        print(existing.stderr.strip(), file=sys.stderr)
        return 1

    target = args.directory.expanduser().resolve()
    if target.exists():
        if runtime_browser(target).is_file():
            env = os.environ.copy()
            env["TEST_DRIVE_AGENT_BROWSER"] = str(runtime_browser(target))
            found = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("agent_browser.py"))],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if found.returncode == 0:
                print(f"Using agent-browser: {found.stdout.strip()}")
                return 0
        print(
            f"Runtime directory already exists: {target}. Choose another directory; it was not changed.",
            file=sys.stderr,
        )
        return 1
    npm, node = shutil.which("npm"), shutil.which("node")
    if not npm or not node:
        print("Node.js 24+ and npm are required to install agent-browser.", file=sys.stderr)
        return 1
    npm_command = [npm]
    if os.name == "nt" and Path(npm).suffix.lower() in (".cmd", ".bat"):
        npm_cli = Path(npm).parent / "node_modules" / "npm" / "bin" / "npm-cli.js"
        if not npm_cli.is_file():
            print("Could not locate npm-cli.js for a safe local installation.", file=sys.stderr)
            return 1
        npm_command = [node, str(npm_cli)]
    try:
        node_version = subprocess.run(
            [node, "--version"], capture_output=True, text=True, timeout=10, check=False
        )
        match = re.fullmatch(r"v(\d+)\.\d+\.\d+", node_version.stdout.strip())
        if node_version.returncode or not match or int(match.group(1)) < 24:
            print("Node.js 24+ is required to install agent-browser.", file=sys.stderr)
            return 1
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".test-drive-", dir=target.parent) as directory:
            stage = Path(directory)
            installed = subprocess.run(
                [
                    *npm_command,
                    "install",
                    "--prefix",
                    str(stage),
                    "--no-global",
                    "--no-save",
                    "--no-package-lock",
                    "--ignore-scripts",
                    "agent-browser@0.40.0",
                ],
                cwd=stage,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            if installed.returncode:
                error = re.search(
                    r"(?m)^npm (?:error|ERR!) code ([A-Z][A-Z0-9_]+)\s*$", installed.stderr
                )
                code = f", {error.group(1)}" if error else ""
                print(
                    f"npm installation failed (exit {installed.returncode}{code}); check npm and network settings.",
                    file=sys.stderr,
                )
                return 1
            env = os.environ.copy()
            env["TEST_DRIVE_AGENT_BROWSER"] = str(runtime_browser(stage))
            verified = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("agent_browser.py"))],
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if verified.returncode:
                print(
                    "The installed agent-browser could not be verified for this platform.",
                    file=sys.stderr,
                )
                return 1
            stage.rename(target)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"Could not set up agent-browser: {exc}", file=sys.stderr)
        return 1
    print(f"Installed agent-browser: {runtime_browser(target)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
