"""Command-line entry point for the skill's runtime helpers."""

import argparse
import json
import sys
from importlib import metadata

from . import agent_browser, agent_browser_setup, report, scenarios


def main() -> int:
    parser = argparse.ArgumentParser(prog="test-drive", description="Test Drive skill helpers")
    parser.add_argument(
        "--version",
        action="version",
        version=f"test-drive-skill {metadata.version('test-drive-skill')}",
    )
    commands = {
        "agent-browser-path": agent_browser.main,
        "setup-agent-browser": agent_browser_setup.main,
        "check-scenarios": scenarios.main,
        "render-report": report.main,
    }
    parser.add_argument("command", choices=(*commands, "report-labels"))
    args = parser.parse_args(sys.argv[1:2])
    if args.command == "report-labels":
        argparse.ArgumentParser(prog="test-drive report-labels").parse_args(sys.argv[2:])
        print(json.dumps(report.LABELS, ensure_ascii=False, indent=2))
        return 0
    sys.argv = [f"test-drive {args.command}", *sys.argv[2:]]
    return commands[args.command]()
