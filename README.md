# Test Drive

Test Drive checks user journeys in websites and web apps through `agent-browser`. It can follow supplied scenarios or derive them from a goal, then create an HTML report with recordings and individual acceptance-criterion results.

## Install

The [skill folder](skills/test-drive/) contains the agent instructions and license. The helper CLI is distributed separately as the Python package `test-drive-skill`; the browser and recording tools are separate prerequisites.

To install the skill from a checkout for a supported agent, run the following command. If the destination already contains a skill you want to keep, back it up first.

```bash
npx skills add ./skills/test-drive --skill test-drive
```

You can also install it with `npx skills add deyna256/test-drive --skill test-drive`. The installer can target specific agents or install globally; see the [skills CLI documentation](https://github.com/vercel-labs/skills/blob/main/docs/commands.md).

Install the compatible CLI with `uv tool install 'test-drive-skill>=0.1.0,<0.2.0'`, or let the skill run it with `uvx`. To use a development checkout, replace `test-drive` in the commands below with `uvx --from /absolute/path/to/this/checkout/python test-drive`. Python 3.10+ is required. The package has no third-party Python runtime dependencies.

For a Codex development checkout, a discovery link keeps the installed skill in sync with this folder:

```bash
mkdir -p .agents/skills
ln -s ../../skills/test-drive .agents/skills/test-drive
```

If `.agents/skills/test-drive` already contains the older local copy, back it up before creating the link:

```bash
mv .agents/skills/test-drive .agents/test-drive.previous
ln -s ../../skills/test-drive .agents/skills/test-drive
```

If `.agents/test-drive.previous` already exists, choose a different backup name.

## Write and run scenarios

Create a folder for each site, containing `index.md` and separate scenario files. The index describes the address, access method and shared data without passwords or tokens. Each scenario describes its purpose, initial state, steps and one or more acceptance criteria. Headings and content can use any language the agent understands. See the [site index](examples/shop/index.md) and [scenario](examples/shop/cart.md); the example address is fictional.

To start from the example, copy it and replace its contents:

```bash
mkdir -p sites
cp -R examples/shop sites/my-site
```

Start your agent after setting up the prerequisites below, then ask, for example:

```text
$test-drive Check all scenarios in sites/my-site/
$test-drive Check only sites/my-site/cart.md
$test-drive Check https://example.com: can a user find an item and add it to the cart?
```

You can also describe a one-off test or ask the agent to create scenarios in the conversation. Reports, videos and screenshots are saved in `test-drive-report/`. Recordings and screenshots may contain on-screen information; they remain local until you share the folder.

## Reports

Reports default to English. Regenerating an older `run.json` without a `language` field also uses English; set `language` to `ru` to retain Russian labels. Existing generated reports are not changed automatically.

Each criterion has its own result and observation or reason. The renderer checks that ffmpeg can decode a self-contained recording before embedding it; playlists and recordings requiring external files are not supported. Missing or unverified recordings are explained in the report. Decoding does not prove the recording's content or completeness. Saved URLs must omit credentials, query strings and fragments; the renderer rejects unsafe `site.url` values and full URLs in report text without modifying the input. It does not detect all secrets. See the [report data format](docs/report-format.md).

## Dependencies

Requirements are Python 3.10+, a stable `agent-browser` version 0.40.0 or newer, a compatible Chrome or Chromium, and `ffmpeg` with the `libvpx` VP8 encoder for WebM recording. The skill checks the browser version before using it; version 0.40.0 is tested with this project. It uses `TEST_DRIVE_AGENT_BROWSER` when set, then its managed runtime, then `agent-browser` on `PATH`.

If a compatible browser CLI is missing, run `test-drive setup-agent-browser`. The setup reuses a compatible CLI when available; otherwise it installs the tested version in `~/.test-drive/agent-browser` using Node.js 24+ and npm, with package install scripts disabled. It does not modify a global `agent-browser` install. To use another runtime directory, pass `--directory PATH` and set `TEST_DRIVE_RUNTIME_DIR` to the same path. The setup does not install Chrome or operating-system packages: see [agent-browser installation](https://agent-browser.dev/installation) for Chrome and system dependencies.

For development in this checkout, install the pinned browser with `pnpm -C tests/browser install --frozen-lockfile`, then set `TEST_DRIVE_AGENT_BROWSER="$PWD/tests/browser/node_modules/.bin/agent-browser"` and export it before starting the agent. This setup requires Node.js 24+ and pnpm 12.11+. If Chrome is not installed, `./tests/browser/node_modules/.bin/agent-browser install` downloads Chrome for Testing. Verify the selected executable with `test-drive agent-browser-path`.

## Development and contributing

Run `just test`, `just lint` and `just type` for the default checks. The real-browser test is opt-in; see [CONTRIBUTING.md](CONTRIBUTING.md) for setup, evaluation cases, release instructions and project conventions, and [ARCHITECTURE.md](ARCHITECTURE.md) for component boundaries. To check scenario file structure, run `test-drive check-scenarios sites/my-site/`; it prints file names, titles and errors, and leaves semantic validation to the agent.

Report vulnerabilities as described in [SECURITY.md](SECURITY.md). Licensed under the [MIT License](LICENSE).
