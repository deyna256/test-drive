"""Check an independent agent's report against a development evaluation case."""

import argparse
import html
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path


class ReportParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.criteria = []
        self.scenarios = []
        self.current = None
        self.capture = None

    def handle_starttag(self, tag, attrs):
        classes = dict(attrs).get("class", "").split()
        if tag == "li" and "criterion" in classes:
            self.current = {"expected": "", "status": "", "detail": ""}
        elif tag == "span" and "badge" in classes:
            statuses = set(classes) & {"passed", "failed", "blocked", "not_run"}
            if len(statuses) == 1:
                if self.current is None:
                    self.scenarios.append(statuses.pop())
                else:
                    self.current["status"] = statuses.pop()
        elif self.current is not None and tag == "span" and not self.current["expected"]:
            self.capture = "expected"
        elif self.current is not None and tag == "p" and "criterion-detail" in classes:
            self.capture = "detail"

    def handle_data(self, data):
        if self.current is not None and self.capture:
            self.current[self.capture] += data

    def handle_endtag(self, tag):
        if (tag == "span" and self.capture == "expected") or (
            tag == "p" and self.capture == "detail"
        ):
            self.capture = None
        if tag == "li" and self.current is not None:
            self.criteria.append(self.current)
            self.current = None


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a Test Drive evaluation report")
    parser.add_argument("case", help="case id from cases.json")
    parser.add_argument("report", type=Path, help="directory containing run.json and report.html")
    args = parser.parse_args()
    try:
        cases = json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf-8"))[
            "cases"
        ]
        case = next(item for item in cases if item["id"] == args.case)
        root = args.report.resolve(strict=True)
        run = json.loads((root / "run.json").read_text(encoding="utf-8"))
        document = (root / "report.html").read_text(encoding="utf-8")
        if len(run["scenarios"]) != 1:
            raise ValueError("Expected one scenario")
        scenario = run["scenarios"][0]
        criteria = scenario["criteria"]
        parsed = ReportParser()
        parsed.feed(document)
        remaining = parsed.criteria.copy()
        for criterion in criteria:
            field = "actual" if criterion["status"] in ("passed", "failed") else "reason"
            observation = criterion.get(field) or ""
            match = next(
                (
                    row
                    for row in remaining
                    if row["expected"] == criterion["expected"]
                    and row["status"] == criterion["status"]
                    and observation in row["detail"]
                ),
                None,
            )
            if match is None:
                raise ValueError("Report criterion results do not match run data")
            remaining.remove(match)
        if remaining or parsed.scenarios != [scenario.get("status")]:
            raise ValueError("Report results do not match run data")
        expected = case.get("expected_criteria")
        if expected is not None:
            if len(criteria) != len(expected):
                raise ValueError("Criterion count does not match the case")
            for item in expected:
                matches = [
                    criterion
                    for criterion in criteria
                    if criterion.get("expected") == item["expected"]
                ]
                if len(matches) != 1 or matches[0].get("status") != item["status"]:
                    raise ValueError(f"Incorrect result for: {item['expected']}")
                actual = matches[0].get("actual", "")
                reason = matches[0].get("reason", "")
                if item["status"] in ("passed", "failed") and not actual.strip():
                    raise ValueError(f"Missing observation for: {item['expected']}")
                if item["status"] in ("blocked", "not_run") and not reason.strip():
                    raise ValueError(f"Missing reason for: {item['expected']}")
                if item.get("actual_contains") and item["actual_contains"] not in actual:
                    raise ValueError(f"Observation does not match: {item['expected']}")
                if item.get("actual_regex") and not re.search(item["actual_regex"], actual):
                    raise ValueError(f"Observation does not match: {item['expected']}")
                if html.escape(item["expected"]) not in document:
                    raise ValueError(f"Report omits: {item['expected']}")
                if html.escape(actual or reason) not in document:
                    raise ValueError(f"Report omits the result for: {item['expected']}")
        else:
            statuses = [item.get("status") for item in criteria]
            if (
                statuses.count("passed") < case["minimum_passed_criteria"]
                or statuses.count("failed") > case["maximum_failed_criteria"]
            ):
                raise ValueError("One-off criterion results do not match the case")
            if scenario.get("status") not in case["allowed_scenario_statuses"]:
                raise ValueError("Unexpected one-off scenario status")
            observations = " ".join(item.get("actual", "") for item in criteria)
            if any(not re.search(pattern, observations) for pattern in case["actual_regex"]):
                raise ValueError("One-off observations are incomplete")

        statuses = {item["status"] for item in criteria}
        overall = (
            "failed"
            if "failed" in statuses
            else "passed"
            if statuses == {"passed"}
            else "not_run"
            if statuses == {"not_run"}
            else "blocked"
        )
        if scenario.get("status") != overall:
            raise ValueError("Scenario status does not match its criteria")

        video = scenario.get("video")
        if case["recording_required"] and not video:
            raise ValueError("A recording is required")
        if video:
            path = (root / video).resolve(strict=True)
            if (
                not path.is_relative_to(root)
                or not path.is_file()
                or "<video controls" not in document
            ):
                raise ValueError("Recording is missing from the report")
            with path.open("rb") as recording:
                for protocol, address in (("fd", "fd:"), ("pipe", "pipe:0")):
                    recording.seek(0)
                    probe = subprocess.run(
                        [
                            "ffprobe",
                            "-v",
                            "error",
                            "-protocol_whitelist",
                            protocol,
                            "-i",
                            address,
                            "-select_streams",
                            "v:0",
                            "-show_entries",
                            "stream=codec_type",
                            "-of",
                            "csv=p=0",
                        ],
                        stdin=recording,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )
                    if protocol != "fd" or "Protocol not found" not in probe.stderr:
                        break
            if probe.returncode or probe.stdout.strip() != "video":
                raise ValueError("Recording has no readable video stream")
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        StopIteration,
        subprocess.TimeoutExpired,
    ) as exc:
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        return 1
    print("Evaluation checks passed; review the recording and evidence manually.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
