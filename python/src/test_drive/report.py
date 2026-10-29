"""Build a portable HTML report from a run's JSON and local evidence files."""

import argparse
import html
import json
import math
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from string import Template
from urllib.parse import quote, urlsplit

STATUSES = {
    "passed": ("Passed", "Passed"),
    "failed": ("Failed", "Failed"),
    "blocked": ("Blocked", "Blocked"),
    "not_run": ("Not run", "Not run"),
}
LABELS = {
    "brand_note": "Test report",
    "report": "Test run",
    "summary": "Run summary",
    "scenarios": "Scenarios",
    "video": "Recording",
    "video_label": "Scenario recording",
    "video_unsupported": "Your browser does not support video.",
    "video_open": "Open recording",
    "video_missing": "Recording unavailable",
    "video_invalid": "The recording could not be decoded",
    "video_unverified": "The recording could not be verified with ffmpeg",
    "expected": "Expected",
    "actual": "Actual",
    "not_specified": "Not specified",
    "not_recorded": "Not recorded",
    "criteria": "Acceptance criteria",
    "observed": "Observed",
    "reason": "Reason",
    "evidence": "Screenshot",
    "steps": "Steps",
    "steps_missing": "Steps not recorded",
    "screenshot": "Result screenshot",
    "screenshot_alt": "Scenario result screenshot",
    "screenshot_missing": "Screenshot unavailable",
    "reproduction": "How to reproduce",
    "scope": "Scope",
    "assumptions": "Assumptions",
    "limitations": "Limitations",
    "empty": "No scenarios recorded. The test did not run.",
    "footnote": "The report and available artifacts are stored in the same folder.",
    "seek": "Go approximately to",
    "seek_outside": "The timestamp is outside the recording",
}
for status, (single, plural) in STATUSES.items():
    LABELS[status] = single
    LABELS[f"{status}_count"] = plural
# Older runs could specify Russian without storing translated labels.
LEGACY_RU_LABELS = {
    "brand_note": "Отчёт о проверке",
    "report": "Отчёт о прогоне",
    "summary": "Итоги прогона",
    "scenarios": "Сценарии",
    "video": "Запись прогона",
    "video_label": "Запись сценария",
    "video_unsupported": "Ваш браузер не поддерживает видео.",
    "video_open": "Открыть запись",
    "video_missing": "Запись недоступна",
    "video_invalid": "Не удалось декодировать запись",
    "video_unverified": "Не удалось проверить запись с помощью ffmpeg",
    "expected": "Ожидалось",
    "actual": "Получилось",
    "not_specified": "Не указано",
    "not_recorded": "Не зафиксировано",
    "criteria": "Критерии приёмки",
    "observed": "Наблюдалось",
    "reason": "Причина",
    "evidence": "Снимок",
    "steps": "Шаги",
    "steps_missing": "Шаги не записаны",
    "screenshot": "Снимок результата",
    "screenshot_alt": "Снимок результата сценария",
    "screenshot_missing": "Снимок недоступен",
    "reproduction": "Как воспроизвести",
    "scope": "Что проверяли",
    "assumptions": "Допущения",
    "limitations": "Ограничения",
    "empty": "Сценарии не записаны. Проверка не выполнена.",
    "footnote": "Отчёт и доступные материалы хранятся в одной папке.",
    "seek": "Перейти примерно к",
    "seek_outside": "Время шага за пределами записи",
    "passed": "Пройден",
    "passed_count": "Пройдено",
    "failed": "Ошибка",
    "failed_count": "Ошибок",
    "blocked": "Не удалось проверить",
    "blocked_count": "Не удалось проверить",
    "not_run": "Не запускался",
    "not_run_count": "Не запускалось",
}
TEMPLATE = Path(__file__).resolve().parent / "assets" / "report.html"


def text(value: object) -> str:
    return html.escape(str(value), quote=True)


def valid_time(value: object) -> bool:
    try:
        return (
            not isinstance(value, bool)
            and isinstance(value, (int, float))
            and math.isfinite(value)
            and value >= 0
        )
    except OverflowError:
        return False


def asset_url(root: Path, value: object) -> str | None:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return None
    try:
        file = (root / value).resolve()
        if not file.is_relative_to(root) or not file.is_file() or file.stat().st_size == 0:
            return None
        return quote(file.relative_to(root).as_posix(), safe="/")
    except (OSError, RuntimeError, ValueError):
        return None


def recording_url(root: Path, value: object) -> tuple[str | None, str | None]:
    url = asset_url(root, value)
    if not url or not isinstance(value, str):
        return None, None
    try:
        with (root / value).open("rb") as recording:
            for protocol, address in (("fd", "fd:"), ("pipe", "pipe:0")):
                recording.seek(0)
                result = subprocess.run(
                    [
                        "ffmpeg",
                        "-v",
                        "error",
                        "-xerror",
                        "-nostdin",
                        "-protocol_whitelist",
                        protocol,
                        "-i",
                        address,
                        "-map",
                        "0:v:0",
                        "-progress",
                        "pipe:1",
                        "-f",
                        "null",
                        "-",
                    ],
                    stdin=recording,
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=30,
                    check=False,
                )
                if protocol != "fd" or "Protocol not found" not in result.stderr:
                    break
    except (OSError, subprocess.TimeoutExpired):
        return None, "video_unverified"
    if result.returncode or not re.search(r"^frame=\s*[1-9]\d*\s*$", result.stdout, re.MULTILINE):
        return None, "video_invalid"
    return url, None


def validate_time(item: dict, started: int | float | None, number: int) -> None:
    at = item.get("at")
    recorded = item.get("recorded_at")
    if (at is not None and not valid_time(at)) or (
        recorded is not None and not valid_time(recorded)
    ):
        raise ValueError(f"Scenario {number} has an invalid step or criterion time")
    if recorded is not None and (at is not None or started is None or recorded < started):
        raise ValueError(f"Scenario {number} time does not match the recording start")


def criteria_status(criteria: list[dict]) -> str:
    statuses = {item["status"] for item in criteria}
    if "failed" in statuses:
        return "failed"
    if statuses == {"passed"}:
        return "passed"
    if statuses == {"not_run"}:
        return "not_run"
    return "blocked"


def validate(run: object) -> None:
    if not isinstance(run, dict) or not isinstance(run.get("site"), dict):
        raise ValueError("A site object with a name is required")
    if not isinstance(run["site"].get("name"), str) or not run["site"]["name"].strip():
        raise ValueError("site.name is required")
    if run["site"].get("url") is not None and not isinstance(run["site"]["url"], str):
        raise ValueError("site.url must be a string")
    if run["site"].get("url"):
        try:
            url = urlsplit(run["site"]["url"])
        except ValueError:
            raise ValueError(
                "site.url must be a valid address without credentials, query, or fragment"
            ) from None
        if url.username is not None or url.password is not None or url.query or url.fragment:
            raise ValueError("site.url must omit credentials, query, and fragment")
    values = [run]
    while values:
        value = values.pop()
        if isinstance(value, dict):
            values.extend(value.values())
        elif isinstance(value, list):
            values.extend(value)
        elif isinstance(value, str):
            for match in re.finditer(r"\b(?:https?|file)://[^\s<>\"`]+", value, re.IGNORECASE):
                try:
                    url = urlsplit(match.group())
                    unsafe = (
                        url.username is not None
                        or url.password is not None
                        or url.query
                        or url.fragment
                    )
                except ValueError:
                    unsafe = True
                if unsafe:
                    raise ValueError("Saved URLs must omit credentials, query, and fragment")
    for field in ("started_at", "duration", "scope", "assumptions", "limitations"):
        if run.get(field) is not None and not isinstance(run[field], str):
            raise ValueError(f"{field} must be a string")
    language = run.get("language", "en")
    if not isinstance(language, str) or not re.fullmatch(
        r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", language
    ):
        raise ValueError("language must be a language code, such as en or en-US")
    if run.get("direction", "ltr") not in ("ltr", "rtl"):
        raise ValueError("direction must be ltr or rtl")
    labels = run.get("labels", {})
    if not isinstance(labels, dict) or any(
        key not in LABELS or not isinstance(value, str) or not value.strip()
        for key, value in labels.items()
    ):
        raise ValueError("labels must contain known keys with non-empty strings")
    if language.split("-", 1)[0].lower() not in ("en", "ru") and labels.keys() != LABELS.keys():
        raise ValueError("Provide translations for all labels when using another language")
    if not isinstance(run.get("scenarios"), list):
        raise ValueError("A scenarios list is required")
    for number, scenario in enumerate(run["scenarios"], 1):
        if (
            not isinstance(scenario, dict)
            or not isinstance(scenario.get("name"), str)
            or not scenario["name"].strip()
        ):
            raise ValueError(f"Scenario {number} has no name")
        if not isinstance(scenario.get("status"), str) or scenario["status"] not in STATUSES:
            raise ValueError(f"Scenario {number} has an unknown status")
        for field in (
            "source",
            "expected",
            "actual",
            "reason",
            "video",
            "video_reason",
            "screenshot",
        ):
            if scenario.get(field) is not None and not isinstance(scenario[field], str):
                raise ValueError(f"Scenario {number} field {field} must be a string")
        if not isinstance(scenario.get("steps", []), list) or not isinstance(
            scenario.get("reproduction", []), list
        ):
            raise ValueError(f"Scenario {number} steps and reproduction must be lists")
        if any(
            not isinstance(item, str) or not item.strip()
            for item in scenario.get("reproduction", [])
        ):
            raise ValueError(f"Scenario {number} reproduction steps must be non-empty strings")
        started = scenario.get("video_started_at")
        if started is not None and not valid_time(started):
            raise ValueError(f"Scenario {number} has an invalid recording start time")
        criteria = scenario.get("criteria")
        if criteria is not None:
            if not isinstance(criteria, list):
                raise ValueError(f"Scenario {number} criteria must be a list")
            for item in criteria:
                if (
                    not isinstance(item, dict)
                    or not isinstance(item.get("expected"), str)
                    or not item["expected"].strip()
                ):
                    raise ValueError(
                        f"Scenario {number} has a criterion without an expected result"
                    )
                if not isinstance(item.get("status"), str) or item["status"] not in STATUSES:
                    raise ValueError(f"Scenario {number} has a criterion with an unknown status")
                for field in ("actual", "reason", "screenshot"):
                    if item.get(field) is not None and not isinstance(item[field], str):
                        raise ValueError(
                            f"Scenario {number} criterion field {field} must be a string"
                        )
                required = "actual" if item["status"] in ("passed", "failed") else "reason"
                if not (item.get(required) or "").strip():
                    raise ValueError(f"Scenario {number} criterion requires {required}")
                validate_time(item, started, number)
            if criteria and criteria_status(criteria) != scenario["status"]:
                raise ValueError(f"Scenario {number} status does not match its criteria")
            if not criteria and scenario["status"] in ("passed", "failed"):
                raise ValueError(f"Scenario {number} has no acceptance criteria")
        if not criteria:
            if scenario["status"] in ("passed", "failed"):
                if (
                    not (scenario.get("expected") or "").strip()
                    or not (scenario.get("actual") or "").strip()
                ):
                    raise ValueError(f"Scenario {number} requires expected and actual")
            elif not (scenario.get("reason") or "").strip():
                raise ValueError(f"Scenario {number} requires reason")
        for step in scenario.get("steps", []):
            if (
                not isinstance(step, dict)
                or not isinstance(step.get("name"), str)
                or not step["name"].strip()
            ):
                raise ValueError(f"Scenario {number} has a step without a name")
            if step.get("status") is not None and (
                not isinstance(step["status"], str) or step["status"] not in STATUSES
            ):
                raise ValueError(f"Scenario {number} has a step with an unknown status")
            if step.get("detail") is not None and not isinstance(step["detail"], str):
                raise ValueError(f"Scenario {number} step detail must be a string")
            validate_time(step, started, number)


def time_button(item: dict, has_video: bool, started: int | float | None, labels: dict) -> str:
    at = item.get("at")
    if at is None and item.get("recorded_at") is not None:
        at = item["recorded_at"] - started
    if at is not None and has_video:
        minutes, seconds = divmod(int(at), 60)
        clock = f"{minutes}:{seconds:02d}"
        return f'<button class="seek" type="button" data-time="{at:.3f}" aria-label="{text(labels["seek"])} {clock}">{clock}</button>'
    return ""


def step_markup(step: dict, has_video: bool, started: int | float | None, labels: dict) -> str:
    time = time_button(step, has_video, started, labels)
    status = step.get("status")
    label = f'<span class="step-status {status}">{text(labels[status])}</span>' if status else ""
    detail = f'<p class="step-detail">{text(step["detail"])}</p>' if step.get("detail") else ""
    return f'<li class="step"><div class="step-title">{time}<span>{text(step["name"])}</span>{label}</div>{detail}</li>'


def criterion_markup(
    root: Path, item: dict, has_video: bool, started: int | float | None, labels: dict
) -> str:
    status = item["status"]
    field = "actual" if status in ("passed", "failed") else "reason"
    field_label = labels["observed"] if field == "actual" else labels["reason"]
    evidence = asset_url(root, item.get("screenshot"))
    evidence_link = f'<a href="{text(evidence)}">{text(labels["evidence"])}</a>' if evidence else ""
    time = time_button(item, has_video, started, labels)
    return (
        f'<li class="criterion"><div class="criterion-heading"><span>{text(item["expected"])}</span>'
        f'<span class="badge {status}">{text(labels[status])}</span></div>'
        f'<p class="criterion-detail"><strong>{text(field_label)}:</strong> {text(item[field])}</p>'
        f'<div class="criterion-evidence">{time}{evidence_link}</div></li>'
    )


def scenario_panel(root: Path, scenario: dict, number: int, labels: dict) -> str:
    status = scenario["status"]
    source = ""
    if scenario.get("source"):
        source_url = asset_url(root, scenario["source"])
        source_label = text(scenario["source"])
        source = (
            f'<p class="source"><a href="{text(source_url)}">{source_label}</a></p>'
            if source_url
            else f'<p class="source">{source_label}</p>'
        )
    expected = text(scenario.get("expected") or labels["not_specified"])
    actual = text(scenario.get("actual") or labels["not_recorded"])
    reason = f'<p class="reason">{text(scenario["reason"])}</p>' if scenario.get("reason") else ""
    video, video_error = recording_url(root, scenario.get("video"))
    if video:
        video_block = (
            f'<div class="video-wrap"><video controls preload="metadata" src="{text(video)}" '
            f'aria-label="{text(labels["video_label"])}: {text(scenario["name"])}" aria-describedby="scenario-{number}-steps">'
            f'{text(labels["video_unsupported"])}</video></div><a class="asset-link" href="{text(video)}">{text(labels["video_open"])}</a>'
        )
    else:
        reasons = [labels[video_error]] if video_error else []
        if scenario.get("video_reason"):
            reasons.append(scenario["video_reason"])
        explanation = f": {text('; '.join(reasons))}" if reasons else ""
        video_block = f'<div class="missing">{text(labels["video_missing"])}{explanation}</div>'
    steps = "".join(
        step_markup(step, bool(video), scenario.get("video_started_at"), labels)
        for step in scenario.get("steps", [])
    )
    steps_block = (
        f'<ol class="steps">{steps}</ol>'
        if steps
        else f'<div class="missing">{text(labels["steps_missing"])}</div>'
    )
    criteria = scenario.get("criteria") or []
    if criteria:
        entries = "".join(
            criterion_markup(root, item, bool(video), scenario.get("video_started_at"), labels)
            for item in criteria
        )
        outcomes = f'<section class="section"><h3>{text(labels["criteria"])}</h3><ol class="criteria">{entries}</ol></section>'
    else:
        outcomes = (
            f'<div class="outcomes"><div class="outcome"><div class="outcome-label">{text(labels["expected"])}</div><p>{expected}</p></div>'
            f'<div class="outcome"><div class="outcome-label">{text(labels["actual"])}</div><p>{actual}</p></div></div>'
        )
    screenshot = asset_url(root, scenario.get("screenshot"))
    if screenshot:
        screenshot_block = (
            f'<section class="section"><h3>{text(labels["screenshot"])}</h3><a href="{text(screenshot)}">'
            f'<img class="evidence" src="{text(screenshot)}" alt="{text(labels["screenshot_alt"])}" loading="lazy"></a></section>'
        )
    elif scenario.get("screenshot"):
        screenshot_block = f'<section class="section"><h3>{text(labels["screenshot"])}</h3><div class="missing">{text(labels["screenshot_missing"])}</div></section>'
    else:
        screenshot_block = ""
    reproduction = scenario.get("reproduction", [])
    reproduction_block = (
        (
            f"<details><summary>{text(labels['reproduction'])}</summary><ol>"
            + "".join(f"<li>{text(item)}</li>" for item in reproduction)
            + "</ol></details>"
        )
        if reproduction
        else ""
    )
    return (
        f'<section class="panel" id="scenario-{number}"><div class="panel-heading"><div>'
        f'<h2>{text(scenario["name"])}</h2>{source}</div><span class="badge {status}">{text(labels[status])}</span></div>'
        f'<section class="section"><h3>{text(labels["video"])}</h3>{video_block}</section>'
        f"{outcomes}{reason}"
        f'<section class="section" id="scenario-{number}-steps"><h3>{text(labels["steps"])}</h3>{steps_block}</section>{screenshot_block}{reproduction_block}</section>'
    )


def render(run: dict, root: Path) -> str:
    validate(run)
    language = run.get("language", "en")
    defaults = LEGACY_RU_LABELS if language.split("-", 1)[0].lower() == "ru" else LABELS
    labels = defaults | run.get("labels", {})
    scenarios = run["scenarios"]
    counts = Counter(scenario["status"] for scenario in scenarios)
    summary = "".join(
        f'<div class="stat"><div class="stat-number {status}">{counts[status]}</div>'
        f'<div class="stat-label">{text(labels[f"{status}_count"])}</div></div>'
        for status in STATUSES
    )
    metadata = "".join(
        f"<span>{text(value)}</span>"
        for value in (run["site"].get("url"), run.get("started_at"), run.get("duration"))
        if value
    )
    context = "".join(
        f"<p><strong>{text(labels[field])}:</strong> {text(run[field])}</p>"
        for field in ("scope", "assumptions", "limitations")
        if run.get(field)
    )
    context = f'<div class="context">{context}</div>' if context else ""
    if scenarios:
        default = next(
            (i for i, scenario in enumerate(scenarios, 1) if scenario["status"] == "failed"), 1
        )
        links = "".join(
            f'<a class="scenario-link" href="#scenario-{i}"{(" data-default" if i == default else "")}>'
            f'<span class="scenario-number">{i:02d}</span><span class="scenario-name">{text(scenario["name"])}'
            f'<span class="scenario-status {scenario["status"]}">{text(labels[scenario["status"]])}</span></span></a>'
            for i, scenario in enumerate(scenarios, 1)
        )
        panels = "".join(
            scenario_panel(root, scenario, i, labels) for i, scenario in enumerate(scenarios, 1)
        )
        content = (
            f'<div class="workspace"><aside class="sidebar"><div class="sidebar-heading">{text(labels["scenarios"])}'
            f'<span>{len(scenarios)}</span></div><nav class="scenario-nav" aria-label="{text(labels["scenarios"])}">{links}</nav></aside>'
            f"<div>{panels}</div></div>"
        )
    else:
        content = f'<div class="empty">{text(labels["empty"])}</div>'
    return Template(TEMPLATE.read_text(encoding="utf-8")).substitute(
        page_title=text(run["site"]["name"]),
        site_name=text(run["site"]["name"]),
        metadata=metadata,
        context=context,
        summary=summary,
        content=content,
        language=text(language),
        brand_note=text(labels["brand_note"]),
        direction=text(run.get("direction", "ltr")),
        report_label=text(labels["report"]),
        summary_aria=text(labels["summary"]),
        footnote=text(labels["footnote"]),
        seek_outside=text(labels["seek_outside"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Test Drive report from a run")
    parser.add_argument("run", type=Path, help="path to run.json inside the report directory")
    args = parser.parse_args()
    temporary = None
    try:
        run_file = args.run.resolve(strict=True)
        output = run_file.parent / "report.html"
        if output == run_file:
            raise ValueError("Input file must not be named report.html")
        run = json.loads(run_file.read_text(encoding="utf-8"))
        report = render(run, run_file.parent)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output.parent,
            prefix=".report-",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary = Path(file.name)
            file.write(report)
        temporary.replace(output)
    except (OSError, ValueError, KeyError) as error:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                print("Could not remove the temporary report file.", file=sys.stderr)
        print(f"Could not create report: {error}", file=sys.stderr)
        return 2
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
