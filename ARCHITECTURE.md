# Architecture

Test Drive combines an agent skill with a small Python CLI. The agent conducts each journey through
`agent-browser`; the CLI handles deterministic preparation and report generation. It does not
drive the browser or decide whether a criterion passed.

- `skills/test-drive/` is the installable skill: its instructions define the workflow and the
  compatible CLI version. It contains no development tests.
- `python/` is the independent `test-drive-skill` Python project. Its `src/test_drive/` package
  includes the CLI, browser setup, scenario checks and report template. The wheel has no Python
  runtime dependencies.
- `tests/package/` checks the installed Python package. `tests/integration/` checks interactions
  among components. `tests/evals/` contains a synthetic site, saved scenarios and a verifier for
  independent agent evaluations. `tests/browser/` holds the browser CLI dependency used in development.
- `examples/` contains material a user can adapt; `docs/` contains project documentation.

The skill and Python package are installed separately. For each run, the agent checks the package
version, checks scenarios, drives the browser and records observations, then asks the CLI to render
the report. Reports and evidence remain in the chosen local output folder. During development the
CLI can be run directly from `python/`; after release it can be installed from PyPI.

A release tag must match the Python package version. The publish workflow runs CI, builds and tests
the distribution, then uploads it to PyPI. The skill's supported CLI range must be updated when
commands or report data change incompatibly. This structure follows the
[Agent Skills specification](https://agentskills.io/specification) and the Python
[src-layout guidance](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/).
