# 3. The evaluation verifier does not import the renderer

**Status:** Accepted

## Context

`tests/evals/verify.py` checks an agent's report against an evaluation case: criterion statuses, the
scenario status, consistency between `run.json` and `report.html`, and the recording. Some of these
rules also exist in `report.py`, such as how a scenario's status follows its criteria and how ffmpeg
is called without access to other files.

## Decision

The verifier keeps its own copy of these rules and parses the generated HTML instead of importing
`test_drive.report`. It runs with a plain `python3`, without the package installed.

## Alternatives

- **Import the renderer's functions**: less code, but a bug in a shared rule would pass both the
  report and its check, and the verifier would depend on the package being installed.

## Consequences

- A change to a shared rule must be made in both places; `tests/integration/test_evaluation_verifier.py`
  fails when they disagree on its cases.
