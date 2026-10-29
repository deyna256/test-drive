# Test Drive

Test Drive checks user journeys in websites and web apps through `agent-browser`. It can follow supplied scenarios or derive them from a goal, then create an HTML report with recordings and individual acceptance-criterion results.

## Install

The [skill folder](skills/test-drive/) contains the agent instructions and license. The helper CLI is distributed separately as the Python package `test-drive-skill`; the browser and recording tools are separate prerequisites.

To install the skill from a checkout for a supported agent, run the following command. If the destination already contains a skill you want to keep, back it up first.

```bash
npx skills add ./skills/test-drive --skill test-drive
```

You can also install it with `npx skills add deyna256/test-drive --skill test-drive`. The installer can target specific agents or install globally; see the [skills CLI documentation](https://github.com/vercel-labs/skills/blob/main/docs/commands.md).

The skill runs the helper CLI with `uvx`, which also provides Python, so you only need [uv](https://docs.astral.sh/uv/). To install the CLI yourself, use `uv tool install 'test-drive-skill>=0.1.0,<0.2.0'`. To use a development checkout, replace `test-drive` in the commands below with `uvx --from /absolute/path/to/this/checkout/python test-drive`. The package has no third-party Python runtime dependencies.

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

Install [uv](https://docs.astral.sh/uv/) and `ffmpeg` with the `libvpx` VP8 encoder for WebM recording: `sudo apt install ffmpeg`, `brew install ffmpeg` or `winget install Gyan.FFmpeg`. The skill sets up the rest on first use.

The browser is driven by a stable `agent-browser` 0.40.0 or newer; version 0.40.0 is tested with this project. The skill uses `TEST_DRIVE_AGENT_BROWSER` when set, then its managed runtime in `~/.test-drive/agent-browser`, then `agent-browser` on `PATH`. If none is compatible, `test-drive setup-agent-browser` downloads the tested release's native binary for your system from GitHub, checks its SHA-256 digest and saves it in the managed runtime, without Node.js or npm and without changing a global install. To use another runtime directory, pass `--directory PATH` and set `TEST_DRIVE_RUNTIME_DIR` to the same path. Chrome for Testing is then downloaded with `agent-browser install`; on Linux, missing system libraries need `agent-browser install --with-deps`, which uses sudo. Other systems can install agent-browser as described in its [installation guide](https://agent-browser.dev/installation) and set `TEST_DRIVE_AGENT_BROWSER`.

For development in this checkout, run `uv run --project python test-drive setup-agent-browser` and verify the selected executable with `uv run --project python test-drive agent-browser-path`.

## Development and contributing

Run `just test`, `just lint` and `just type` for the default checks. The real-browser test is opt-in; see [CONTRIBUTING.md](CONTRIBUTING.md) for setup, evaluation cases, release instructions and project conventions, and [ARCHITECTURE.md](ARCHITECTURE.md) for component boundaries. To check scenario file structure, run `test-drive check-scenarios sites/my-site/`; it prints file names, titles and errors, and leaves semantic validation to the agent.

Report vulnerabilities as described in [SECURITY.md](SECURITY.md). Licensed under the [MIT License](LICENSE).
