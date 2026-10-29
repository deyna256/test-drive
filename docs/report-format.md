# Report data

The agent creates `run.json` in the run folder and updates it while executing scenarios. Initially, every planned scenario and criterion is marked `not_run`; after each scenario, the agent updates the data and rebuilds the report. From this checkout:

```bash
test-drive render-report test-drive-report/RUN-NAME/run.json
```

The command creates `report.html` next to the JSON file. Videos and screenshots must be in the same folder or its subfolders, and JSON paths are relative to `run.json`. Before embedding a video, the renderer asks ffmpeg to decode the opened file without accessing other files or network resources; playlists and videos requiring external segments are not supported. Failure or missing ffmpeg is reported as unavailable. Decoding does not prove the recording's content or completeness. Do not include passwords or tokens. The renderer rejects `site.url` and full HTTP, HTTPS, or file URLs in report text when they contain URL credentials, a query, or a fragment; it never edits the input file. This does not detect every secret. Use a sanitized copy of existing run data when necessary. A step's `at` value is the number of seconds from the beginning of **that** recording, captured when the action occurred. Omit it if unknown.

Alternatively, record `video_started_at` for a scenario and `recorded_at` for a step, using the same monotonic clock. Run `python3 -c 'import time; print(time.monotonic())'` immediately after recording starts and before the action; the report calculates the difference. Timestamps are approximate because recording confirmation and actions take time. A step may have `at` or `recorded_at`, but not both.

```json
{
  "site": {"name": "Shop", "url": "https://shop.example"},
  "started_at": "28 October 2026, 18:00",
  "duration": "1 min 30 sec",
  "scope": "Adding an item to the cart",
  "assumptions": "A test account is used",
  "limitations": "Checkout was not tested",
  "scenarios": [
    {
      "name": "Add an item to the cart",
      "source": "site/cart.md",
      "status": "failed",
      "criteria": [
        {"expected": "The cart contains one kettle", "status": "passed", "actual": "The cart contains one kettle"},
        {"expected": "The total is $19.90", "status": "failed", "actual": "The total is $29.90", "screenshot": "screenshots/cart.png"}
      ],
      "video": "videos/cart.webm",
      "screenshot": "screenshots/cart.png",
      "steps": [
        {"name": "Find the kettle", "status": "passed", "at": 2.4},
        {"name": "Add the item", "status": "passed", "at": 8.1}
      ]
    }
  ]
}
```

Required fields are `site.name`, a `scenarios` list, and `name` and `status` for each scenario. Use a `criteria` list for individual acceptance criteria. Each criterion requires `expected`, `status`, and either `actual` for `passed` or `failed`, or `reason` for `blocked` or `not_run`. A criterion can also have a `screenshot` and `at` or `recorded_at`.

The scenario status must match its criteria: any `failed` → `failed`; all `passed` → `passed`; all `not_run` → `not_run`; all other combinations → `blocked`. A scenario without identified criteria can be `blocked` or `not_run` with a scenario-level `reason`. Older reports without `criteria` can still use scenario-level `expected` and `actual`. Do not report an agent error or unknown requirement as a product defect.

Other fields are optional. Use the strings `scope`, `assumptions` and `limitations` where applicable. A step requires `name` and can have `status`, `detail`, and `at` or `recorded_at`. A failure can include a `reproduction` list of actions. When a recording is unavailable, explain why in `video_reason`. Missing, empty, and outside-folder files are not linked; unavailable recordings are indicated in the report.

The report interface defaults to English, including when regenerating an older `run.json` that has no `language` field; existing HTML files are not changed automatically. For another language, set `language` (for example, `fr` or `zh-Hans`) and translate every key in `labels`. For backward compatibility, `language: "ru"` also works without labels. Use `direction: "rtl"` for right-to-left text. Get the keys and English defaults with:

```bash
test-drive report-labels
```
