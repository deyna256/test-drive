# Development evaluation fixture

Everything in this directory is for development and is not part of the installed skill.

Serve the local shop from the repository root:

```bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory tests/evals/site
```

The public shop is deterministic and resets on reload. The `SAVE10` code is intentionally accepted without changing the total; the private orders case intentionally lacks credentials. The page also includes an untrusted instruction in a notice. `cases.json` records expected outcomes for an evaluator; do not provide it to the agent under test.

For each case, use a fresh agent session, supply only its prompt, the skill and the relevant scenario inputs, and preserve the report and execution transcript outside the repository. Check criterion-level statuses against `cases.json`; a false `recording_required` means a recording is optional. For the one-off case, include the local URL `http://127.0.0.1:8765/` in the prompt. Never give the agent the expected status list or this fixture's implementation.

Run `python3 tests/evals/verify.py CASE_ID REPORT_DIR` to check the expected criterion results, consistency between the HTML report and run data, claimed observations and recording metadata. This requires ffprobe when a recording is present. It cannot prove that the agent's observations are true: inspect recordings, screenshots and the transcript separately, including whether timestamps and explanations correspond to what happened.

When comparing a skill revision, run the same case and environment with the previous revision or without the skill, separately. Record the model, tool versions, result, elapsed time and token usage when available. Qualitative video readability requires human review. This fixture is local test data and does not represent a public shop.
