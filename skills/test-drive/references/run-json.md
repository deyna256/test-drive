# Report data: run.json

Put `run.json`, recordings, and screenshots in the report folder or its subfolders. `test-drive render-report REPORT_DIR/run.json` writes `report.html` next to it; it does not modify the input.

## Shape

Create all planned criteria as `not_run` before running them; then replace the reason with the actual observation and update the criterion and scenario statuses. Values below are illustrative, not requirements for the user's site.

```json
{
  "site": {"name": "Shop", "url": "https://shop.example"},
  "language": "en",
  "scope": "Adding an item to the cart",
  "assumptions": "A test account is used",
  "limitations": "Payment was not checked",
  "scenarios": [{
    "name": "Add item",
    "source": "site/cart.md",
    "status": "not_run",
    "criteria": [
      {"expected": "The cart contains one kettle", "status": "not_run", "reason": "Not checked yet"},
      {"expected": "The total is $19.90", "status": "not_run", "reason": "Not checked yet"}
    ],
    "steps": []
  }]
}
```

## Fields

- Run: `site.name` and a `scenarios` list are required. Optional `started_at`, `duration`, `scope`, `assumptions`, and `limitations` are strings. If the index lacks a usable site name, use the site folder name in `site.name` and explain the blockage.
- Scenario: `name` and `status` are required. It can include `source`, `criteria`, `steps`, `video`, `video_reason`, `video_started_at`, `screenshot`, `reason`, and a `reproduction` list of strings. A blocked or unstarted scenario with no identifiable criteria can omit `criteria` and must include a scenario-level `reason`. Do not copy credentials into source references.
- Criterion: `expected` and `status` are required, plus `actual` for `passed`/`failed` or `reason` for `blocked`/`not_run`. It may include `screenshot` and either `at` or `recorded_at`.
- Step: `name` is required; it can include `status`, `detail`, and either `at` or `recorded_at`.
- Times: `at` is seconds from the beginning of that scenario's recording; `recorded_at` uses the clock of the scenario's `video_started_at`, which it requires. An item has at most one of them.
- Recording: if there is none, explain why in `video_reason`. If `record stop` failed, omit `video` and identify the partial file and the failure in `video_reason`.
- Artifacts: all paths are relative to the report folder and must point to existing non-empty files inside it; others are not linked.
- Older run files without `criteria` keep the legacy scenario-level `expected` and `actual` fields; new runs must use the criterion list.

## What the renderer enforces

- A scenario's status must match its criteria (see the skill's rule).
- It rejects `site.url` and full HTTP, HTTPS, or file URLs anywhere in the data if they contain credentials, a query, or a fragment. It does not detect every secret.
- It embeds a recording only after ffmpeg decodes it without accessing other files or network resources; playlists and videos requiring external segments are not supported. A missing or failed verification is explained in the report. Decoding does not prove the recording's content or completeness.

## Language

The HTML interface defaults to English. Set `language` to a BCP 47 code. Russian labels are built in for compatibility; other non-English languages require translations for all keys in `labels`. For a right-to-left report set `direction` to `rtl`. Get the current default keys with:

```bash
test-drive report-labels
```
