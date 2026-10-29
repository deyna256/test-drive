# 5. The browser CLI is installed as a native binary, not through npm

**Status:** Accepted

## Context

`agent-browser` is a Rust program. Its npm package (about 120 MB) contains a binary for every platform
and a Node.js launcher that only selects one and starts it; the package requires Node.js 24 or newer.
Installing it through npm made Node.js 24 and npm a requirement for every user, and pnpm one for
development. Each GitHub release of agent-browser also publishes the binaries as single files
(16–18 MB) with SHA-256 digests.

## Decision

`test-drive setup-agent-browser` downloads the binary for the current platform from the tested
release, checks it against a SHA-256 digest stored in the package, makes it executable, checks its
version and moves it into place without replacing an existing directory. The tested version and its
digests are kept in one place in `agent_browser_setup.py`.

## Alternatives

- **npm with install scripts disabled** (the previous approach): needs Node.js 24 and npm, and
  downloads every platform's binary.
- **npm with install scripts**: also runs the package's postinstall script, which downloads files and
  changes global npm shims.
- **Homebrew or Cargo**: available only on some systems, or compiles for minutes.

## Consequences

- Users need uv and ffmpeg; the skill installs the browser CLI and, through it, Chrome for Testing.
- A platform without a published binary must install agent-browser another way and set
  `TEST_DRIVE_AGENT_BROWSER`.
- Dependabot no longer reports new agent-browser releases; updating means changing the version and the
  digests together and running the real browser test.
