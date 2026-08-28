# Eval results template

Copy this file to `evals/results/<date>/RESULTS.md` after a `run_bench.py` +
`score.py` + `judge.py` run and fill it in. Publish every number below, even
one that misses its target — a target missed and reported is useful; a
target missed and omitted is not (design doc §10.5).

## Method

Record exactly what produced the numbers below, since that is what makes a
published run reproducible.

- Scenario suite: `evals/scenarios/` (10 scenarios, see `evals/README.md`).
- Models: fill in the exact provider model IDs used, from each run's
  `raw/*/*/*.meta.json`.
- Sampler settings: temperature, top_p, max_tokens — copy from the same
  metadata files.
- Judge model: which model judged which pairs (`evals/judge.py`'s
  `judge_model_for` — never the model that generated the pair).

| Model slot | Provider model ID | Skill artifact used |
| ---------- | ------------------ | -------------------- |
| claude     |                     | `skills/readable-code/SKILL.md` |
| gpt        |                     | `templates/agent-block.md` (rendered) |
| qwen       |                     | `prompts/system-prompt.md` |

## Automated scoring

These come straight from `scores.json` (design doc §10.2); M1 and M3 are the
two with published PRD targets.

| Metric | Target | claude | gpt | qwen |
| ------ | ------ | ------ | --- | ---- |
| taorc-lint findings / 100 LOC reduction, skill vs. baseline (M1) | ≥ 60% | | | |
| Diff-size inflation on bugfix/error-handling scenarios (M3) | ≤ 10% | | | |
| Comment-to-code ratio, skill vs. baseline | — | | | |
| Mean nesting depth, skill vs. baseline | — | | | |
| Empty-word identifier count, skill vs. baseline | — | | | |

## LLM judge

From `judgments/`, aggregated across every judged pair.

| Metric | Target | Value |
| ------ | ------ | ----- |
| Blind pairwise preference for skill output (M2) | ≥ 70% | |

Per-category rubric (1-5, averaged across judged pairs):

| Category | claude | gpt | qwen |
| -------- | ------ | --- | ---- |
| N (naming) | | | |
| C (comments) | | | |
| F (control flow / structure) | | | |
| S (structure / decomposition) | | | |
| T (tests) | | | |

## Notes and misses

Record any metric that missed its target, any scenario that had to be
excluded or re-run, and any judge response that failed to parse.

## Raw data

Everything below lives alongside this file in the same run directory.

- `raw/` — every completion plus its generation metadata.
- `scores.json` — `score.py`'s output.
- `judgments/` — one JSON file per judged pair.
