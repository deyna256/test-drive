"""Check a site's index and Markdown scenarios without exposing their contents."""

import argparse
import json
import re
import sys
from pathlib import Path


def inspect(path: Path) -> dict:
    result = {"path": str(path), "name": "", "errors": []}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        result["errors"].append(f"Could not read file: {error}")
        return result

    fence = None
    has_content = False
    skip_underline = False
    for index, line in enumerate(lines):
        if skip_underline:
            skip_underline = False
            continue
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            chars, tail = marker.groups()
            if fence is None:
                fence = (chars[0], len(chars))
            elif chars[0] == fence[0] and len(chars) >= fence[1] and not tail.strip():
                fence = None
            continue
        atx = re.match(r"^\s{0,3}#\s+(.+?)\s*#*\s*$", line) if fence is None else None
        setext = (
            fence is None
            and not atx
            and index + 1 < len(lines)
            and line.strip()
            and re.match(r"^ {0,3}\S", line)
            and not re.match(r"^ {0,3}(?:[>#+*`~]|-\s|\d+[.)]\s)", line)
            and re.fullmatch(r" {0,3}=+[ \t]*", lines[index + 1])
        )
        if atx or setext:
            if result["name"]:
                result["errors"].append("File has multiple top-level headings")
            else:
                result["name"] = atx.group(1) if atx else line.strip()
            skip_underline = bool(setext)
        elif (
            result["name"]
            and fence is None
            and line.strip()
            and not re.match(r"^\s{0,3}#{1,6}\s", line)
        ):
            has_content = True

    if not result["name"]:
        result["errors"].append("Site or scenario title is missing")
    elif not has_content:
        result["errors"].append("File has no content outside headings and code examples")
    return result


def check(path: Path) -> dict:
    if path.is_dir():
        directory = path
        scenarios = sorted(file for file in directory.glob("*.md") if file.name != "index.md")
    elif path.is_file() and path.name == "index.md":
        return check(path.parent)
    elif path.is_file() and path.suffix == ".md":
        directory = path.parent
        scenarios = [path]
    else:
        return {
            "validation": "structure_only",
            "site": {
                "path": str(path),
                "name": "",
                "errors": ["Folder or Markdown file not found"],
            },
            "scenarios": [],
        }

    site = inspect(directory / "index.md")
    cases = [inspect(file) for file in scenarios]
    if not cases:
        site["errors"].append("Folder has no scenario files")
    return {"validation": "structure_only", "site": site, "scenarios": cases}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check file structure; the agent checks meaning and acceptance criteria"
    )
    parser.add_argument("path", type=Path, help="site folder or individual scenario file")
    args = parser.parse_args()
    result = check(args.path)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    try:
        output.encode(sys.stdout.encoding or "utf-8")
    except UnicodeEncodeError:
        output = json.dumps(result, ensure_ascii=True, indent=2)
    print(output)
    return (
        2 if result["site"]["errors"] or any(case["errors"] for case in result["scenarios"]) else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
