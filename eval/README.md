# Seed evaluation and recorded results

Both saved runs from 2026-07-08 passed all ten seed scenarios under the automated
scoring rule. On 2026-10-12, the saved answers were rescored using the current
evaluator and matched every recorded score. No new model inference was performed
during that verification.

| Recorded model identifier | Passed | Cases with unexpected law numbers |
| --- | --- | --- |
| `qwen3:latest` | 10/10 | 2 |
| `qwen3.6:27b` | 10/10 | 0 |

The model identifiers are those recorded by the runner. Model digests, inference
settings, runtime versions and a source PDF hash were not captured, so these
historical runs are not fully reproducible. In particular, `latest` is mutable.

## Tests and evidence

- [Scenario inputs and expectations](scenarios.json)
- [Scoring implementation](../src/evaluate.py)
- [Full qwen3:latest answers and scores](results/2026-07-08/qwen3-latest.json)
- [Full qwen3.6:27b answers and scores](results/2026-07-08/qwen3-6-27b.json)

| Scenario ID | Expected laws | qwen3:latest | qwen3.6:27b |
| --- | --- | --- | --- |
| `penalty_trip_001` | 12, 14 | Pass | Pass |
| `direct_free_kick_trip_001` | 12 | Pass; extra 14 | Pass |
| `reckless_tackle_yellow_001` | 12 | Pass | Pass |
| `excessive_force_red_001` | 12 | Pass | Pass |
| `handball_penalty_001` | 12, 14 | Pass | Pass |
| `goalkeeper_backpass_001` | 12 | Pass; extra 14 | Pass |
| `offside_interference_001` | 11 | Pass | Pass |
| `offside_not_active_001` | 11 | Pass | Pass |
| `dogso_penalty_attempt_ball_001` | 12, 14 | Pass | Pass |
| `insufficient_info_contact_001` | 12, 14 | Pass | Pass |

## What passing means

Each scenario supplies an incident description, a stated referee call, expected
law numbers and an optional requirement for uncertainty. The runner calls
`explain_call`, then checks:

1. Every expected law number appears in the output citations.
2. When uncertainty is required, the `uncertainties` field is nonempty.

Unexpected law numbers are reported but do not cause failure. The scenario
`notes` describe desired behavior but are not automatically scored. Uncertainty
content is not assessed beyond whether the field is nonempty.

These results measure expected-law coverage and uncertainty presence, not 100%
football decision accuracy. They do not verify explanation correctness, card
severity, exact clause/page alignment, grounding of every claim, or whether a
referee's call was justified. The stated call is an input, not a prediction being
graded. Citation postprocessing can add supporting laws, so this evaluates the
whole explanation pipeline rather than the language model in isolation.

The small seed set is development evidence, not an independent held-out benchmark
or referee-expert validation. Keyword and embedding retrieval have not been
compared on it.

## Run locally

From the repository root, with Ollama running and the selected model installed:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.cli ingest
OLLAMA_MODEL=qwen3:latest python -m src.cli eval --save --progress
OLLAMA_MODEL=qwen3.6:27b python -m src.cli eval --save --progress
```

New reports are saved in `eval/runs/`, which is ignored by Git. The historical
reports in `eval/results/2026-07-08/` are preserved public copies and are not
overwritten by these commands. New outputs can differ from the recorded runs.
