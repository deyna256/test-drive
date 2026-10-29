# Changelog

Notable changes to this project. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[semantic versioning](https://semver.org/spec/v2.0.0.html). While the version is `0.x` the CLI and
the report data may change in a minor release; the skill states the compatible range.

This file is built from fragments in `changelog.d/` when a release is made; see
[CONTRIBUTING.md](CONTRIBUTING.md#changelog). Do not edit it by hand.

<!-- towncrier release notes start -->

## [0.1.2] - 2026-10-29

### Added

- The report has a dark theme with a toggle, status icons, and a timeline under each recording: every checked criterion is a marker you can click to jump to that moment, and the current step is highlighted while the video plays.

### Changed

- The skill runs the CLI and its timestamps through uv, so uv and ffmpeg are the only tools to install; the skill downloads the browser CLI and Chrome for Testing itself.
- The skill's instructions are a numbered workflow, with the report data format and troubleshooting in separate reference files that are read only when needed.
- `test-drive setup-agent-browser` downloads agent-browser's native binary for your system from its GitHub release and checks its SHA-256 digest, so Node.js and npm are no longer needed. Browsers installed by version 0.1.1 are still found.

### Fixed

- `check-scenarios` keeps a closing `#` that is part of a title, such as `# Learn C#`, and treats an empty `#` heading as a missing title.
- `check-scenarios` no longer treats a line such as ```` ```npm i``` ```` or a tab-indented fence as the start of a code block that hides the rest of the file.
- `render-report` gives `report.html` the usual file permissions instead of making it readable only by its owner.


## [0.1.1] - 2026-10-29

### Changed

- The skill runs one browser session at a time, closes it after each scenario and stops before memory runs out, and explains how to handle socket, permission and network limits of the host.

## [0.1.0] - 2026-10-29

### Added

- The Test Drive skill: it checks user journeys in a real browser through agent-browser, from saved Markdown scenarios or a goal, and evaluates each acceptance criterion separately.
- The `test-drive` CLI: `check-scenarios`, `agent-browser-path`, `setup-agent-browser`, `render-report` and `report-labels`.
- A portable HTML report with recordings, steps that seek the video, screenshots and per-criterion results, in English or other languages.
