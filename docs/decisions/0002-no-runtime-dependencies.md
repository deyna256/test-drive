# 2. The Python package has no runtime dependencies

**Status:** Accepted

## Context

The skill runs the CLI with `uvx` on the user's machine, often for the first time in a session and
sometimes with restricted network access. Every dependency adds download time, a possible conflict
and code that reads users' scenarios and run data.

## Decision

`test-drive-skill` uses only the Python standard library: `argparse` for commands, `json` for run
data, `html` and `string.Template` for the report, `subprocess` for ffmpeg and the browser CLI, and
`urllib` to download the browser CLI. Ruff and ty are development dependencies only.

## Alternatives

- **A template engine** (Jinja2) for the report: the report is one page with escaped values; f-strings
  with `html.escape` are enough.
- **A schema library** (pydantic, msgspec) for `run.json`: clearer validation code, but a dependency
  for a few dozen fields.
- **A Markdown parser** for `check-scenarios`: the check needs only top-level headings and code fences.

## Consequences

- `uvx` installs only the package itself, and nothing can conflict with it.
- Validation in `report.py` and heading parsing in `scenarios.py` are written by hand and must be
  tested by hand, including CommonMark edge cases.
