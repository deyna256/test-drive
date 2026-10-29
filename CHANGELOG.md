# Changelog

Notable changes to this project. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[semantic versioning](https://semver.org/spec/v2.0.0.html). While the version is `0.x` the CLI and
the report data may change in a minor release; the skill states the compatible range.

This file is built from fragments in `changelog.d/` when a release is made; see
[CONTRIBUTING.md](CONTRIBUTING.md#changelog). Do not edit it by hand.

<!-- towncrier release notes start -->

## [0.1.1] - 2026-10-29

### Changed

- The skill runs one browser session at a time, closes it after each scenario and stops before memory runs out, and explains how to handle socket, permission and network limits of the host.

## [0.1.0] - 2026-10-29

### Added

- The Test Drive skill: it checks user journeys in a real browser through agent-browser, from saved Markdown scenarios or a goal, and evaluates each acceptance criterion separately.
- The `test-drive` CLI: `check-scenarios`, `agent-browser-path`, `setup-agent-browser`, `render-report` and `report-labels`.
- A portable HTML report with recordings, steps that seek the video, screenshots and per-criterion results, in English or other languages.
