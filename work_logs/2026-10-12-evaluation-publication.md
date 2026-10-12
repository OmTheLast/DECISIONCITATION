# Evaluation publication round

Request: verify whether all ten seed scenarios passed and publish the tests and
results to GitHub.

## Start checkpoint

- Completed: inspected the clean repository, scenario definitions and saved reports.
- Historical artifacts: `eval/runs/qwen3-latest.json` and
  `eval/runs/qwen3-6-27b.json`, dated 2026-07-08.
- Proposed: rescore saved answers using the current evaluator; preserve public
  copies of reports and document scoring limitations and reproduction commands.
- No model inference or training is running as part of this round.
- Next action: verify saved answers and publish reports under `eval/results/`.

## Verification milestone

- Verified: both reports contain all ten unique scenario IDs; every saved score
  matches rescoring its saved answer with `score_scenario`.
- Verified: each report has 10 passed and 0 failed; qwen3:latest has two cases
  with unexpected law numbers, qwen3.6:27b has none.
- Completed: preserved full historical reports under `eval/results/2026-07-08/`;
  added `eval/README.md` and a root README summary.
- No new inference was run. Historical model digests and environment/source
  hashes are unavailable; documentation records this reproducibility limitation.
- Next action: check the diff, verify public copies, commit and push via SSH.
