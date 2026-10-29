# Contributing to Test Drive

Use plain English in issues, commits, documentation and code comments. Follow the
[architecture](ARCHITECTURE.md) and [Code of Conduct](CODE_OF_CONDUCT.md). Distinguish implemented
behaviour from plans.

## No signatures

Do not add generated-by lines, tool attribution or similar signatures to commits, issues, pull
requests, reviews, comments, documentation or code. Do not add co-author or sign-off trailers.

## Development

The skill is in `skills/test-drive/`; the independent `test-drive-skill` Python project is in
`python/`. Development tests, the browser CLI's development dependency and evaluation fixtures live
in `tests/` and are not installed with the skill or wheel. Package tests are in `tests/package/`;
product-level tests are in `tests/integration/`, and agent evaluation cases are in `tests/evals/`.
Install Python 3.10+, [uv](https://docs.astral.sh/uv/) and [Just](https://just.systems/). Sync the
locked development environment and run the relevant checks before submitting a change:

```bash
uv sync --locked --project python
just test
just lint
just type
```

`just format` applies Ruff fixes and formatting; `just build` builds the Python distributions. The
test suite uses the standard library; Ruff and ty are development dependencies only. CI checks the
lockfile, formatting and types and tests the installed package on supported Python versions and OSes.

Default tests do not call real agents or require credentials. Report tests verify recordings when
ffmpeg is available. To run the real browser integration test,
install a compatible `agent-browser`, Chrome and ffmpeg with VP8 support, then run:

```bash
TEST_DRIVE_E2E=1 uv run --project python python -B -m unittest discover -s tests/integration -p test_browser_journey.py -v
```

The integration test uses a local synthetic site and a separate browser session. The independent
agent evaluation cases and their expected outcomes are described in [tests/evals](tests/evals/).
Use synthetic data in tests and keep credentials, private scenarios and recordings out of the repo.

The browser CLI version in `tests/browser/package.json` must match the version installed by
`setup-agent-browser`. When updating it, review the installer and skill instructions and run the
real browser test before accepting the update.

## Releases

The `publish.yml` workflow checks the version and builds the wheel and source distribution after a
`v<version>` tag is pushed. It runs the CI checks before publishing those artifacts to PyPI.
Configure a [pending Trusted Publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
on PyPI with project `test-drive-skill`, owner `deyna256`, repository `test-drive`, workflow
`publish.yml`, and environment `pypi`. A pending publisher does not reserve the name until the first
publication. The package version in `python/pyproject.toml` must match the tag, and `python/uv.lock`
must be current; `uv version --project python <version>` updates both. Update the skill's compatible
package range when making a breaking CLI change. No PyPI API token is needed for the workflow.

## Issues

Check existing issues before opening one. Use the [issue template](.github/ISSUE_TEMPLATE/issue.md)
to describe one clear outcome, why it matters and the observable checks that complete it. Report
vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

Give each issue one type label: `bug`, `feature`, `maintenance`, `docs` or `question`. Add `ci`
for CI and developer tooling and `good first issue` for small, self-contained work. Close duplicates
and declined issues with the matching close reason and link the original issue when applicable.

## Branches and commits

For issue work, branch from `main` and use the issue number as the branch name. Without an issue,
use a short descriptive branch name. Use a one-line commit message beginning with an action, such as
`#1: validate recordings` or `document setup`. Do not add a commit body. Keep unrelated changes out
of the commit and inspect the staged diff before committing.

## Pull requests and reviews

Use the [pull request template](.github/pull_request_template.md) to describe the problem, resulting
behaviour and checks, including anything not run. Link the issue and use `Closes #<number>` when
appropriate. Keep the PR focused and update its description if the change evolves.

Open a draft while work is in progress. When ready, mark it ready for review and request a review if
another maintainer is available; request it again after addressing their findings.

Review correctness, test coverage, changes to the skill's instructions and compatibility, and
whether reports or logs can expose private data. Put code-specific findings in inline comments, with
the consequence and a concrete fix or check. Mark non-blocking findings `Nit:` or `Question:`;
other findings block the merge. Use the review body for the verdict, cross-cutting findings and
checks performed. Use a separate issue for work outside the PR's scope.

## Documentation and local notes

Keep shared documentation in Markdown and update it with the behaviour it describes. Use `.local/`
for research, drafts and plans; it is ignored by Git. Move accepted decisions and their reasons into
shared documentation so a fresh clone contains the information needed to work on the project.
