"""Check that every version a release depends on was updated consistently."""

import argparse
import re
import subprocess
import sys
from pathlib import Path

SEMVER = r"(\d+)\.(\d+)\.(\d+)"


def parse(version: str) -> tuple[int, ...] | None:
    match = re.fullmatch(SEMVER, version)
    return tuple(map(int, match.groups())) if match else None


def problems(root: Path, tags: list[str]) -> list[str]:
    found = []
    pyproject = (root / "python" / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version = "([^"]+)"', pyproject)
    version = match.group(1) if match else ""
    current = parse(version)
    if current is None:
        return [f"python/pyproject.toml has no X.Y.Z version: {version or 'none'}"]

    released = [parsed for tag in tags if tag.startswith("v") and (parsed := parse(tag[1:]))]
    if released and current <= max(released):
        latest = ".".join(map(str, max(released)))
        found.append(f"Version {version} is not newer than the latest release v{latest}")

    lock = (root / "python" / "uv.lock").read_text(encoding="utf-8")
    locked = re.search(r'(?m)^name = "test-drive-skill"\nversion = "([^"]+)"', lock)
    if not locked or locked.group(1) != version:
        found.append(f"python/uv.lock does not record version {version}; run uv lock")

    # README and SKILL.md must state the versions; other skill files must not contradict them.
    required = ("README.md", "skills/test-drive/SKILL.md")
    names = {
        *required,
        *(p.relative_to(root).as_posix() for p in root.glob("skills/test-drive/**/*.md")),
    }
    documents = {name: (root / name).read_text(encoding="utf-8") for name in sorted(names)}
    ranges = {
        (name, low, high)
        for name, text in documents.items()
        for low, high in re.findall(r">=(\d+\.\d+\.\d+),<(\d+\.\d+\.\d+)", text)
    }
    for name in required:
        if not any(item[0] == name for item in ranges):
            found.append(f"{name} does not state the compatible package range")
    if len({(low, high) for _, low, high in ranges}) > 1:
        listed = ", ".join(sorted(f"{name}: >={low},<{high}" for name, low, high in ranges))
        found.append(f"Compatible package ranges differ: {listed}")
    for name, low, high in sorted(ranges):
        bounds = [tuple(map(int, bound.split("."))) for bound in (low, high)]
        if not bounds[0] <= current < bounds[1]:
            found.append(f"{name} range >={low},<{high} does not include {version}")

    setup = (root / "python" / "src" / "test_drive" / "agent_browser_setup.py").read_text(
        encoding="utf-8"
    )
    tested = re.search(r'(?m)^VERSION = "([^"]+)"', setup)
    if not tested:
        found.append("agent_browser_setup.py does not define VERSION")
    else:
        for name, text in documents.items():
            stated = set(re.findall(r"(\d+\.\d+\.\d+) is (?:the version )?tested", text))
            if stated != {tested.group(1)} and (name in required or stated):
                found.append(
                    f"{name} must state agent-browser {tested.group(1)} as the tested version"
                    f" (found {', '.join(sorted(stated)) or 'none'})"
                )
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    args = parser.parse_args()
    tags = subprocess.run(
        ["git", "-C", str(args.root), "tag", "--list", "v*"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    found = problems(args.root, tags)
    for problem in found:
        print(problem, file=sys.stderr)
    if found:
        return 1
    print("Versions are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
