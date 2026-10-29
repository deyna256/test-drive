# 1. The agent drives the browser and judges criteria; the CLI does not

**Status:** Accepted

## Context

A test of a user journey needs two kinds of work. Reading a scenario in any language, using a page as
a person would and deciding whether what is visible meets a plain-language criterion needs judgement.
Checking file structure, finding a compatible browser CLI, validating run data, verifying recordings
and writing a report must give the same result every time.

## Decision

The agent, following `skills/test-drive/SKILL.md`, reads scenarios, drives `agent-browser`, records
observations and decides each criterion's status. The `test-drive` CLI only does the deterministic
work: `check-scenarios` checks structure, `agent-browser-path` and `setup-agent-browser` find or
install the browser CLI, and `render-report` validates `run.json` and builds `report.html`.

## Alternatives

- **A CLI that runs scenarios itself** with selectors or a script: it would need a scenario language
  and could not follow scenarios written for people.
- **A CLI that calls a model to judge**: it would need API keys and a provider, and would duplicate
  the agent already running the skill.

## Consequences

- Scenarios are ordinary Markdown in any language, and no credentials are needed by the CLI.
- The CLI cannot tell whether an observation is true. It enforces consistency instead: a scenario's
  status must follow its criteria, artifacts must exist inside the report folder and recordings must
  decode. Evaluations in `tests/evals/` check the agent's judgement separately.
