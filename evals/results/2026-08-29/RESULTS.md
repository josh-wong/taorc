# Eval results — 2026-08-29 (first MS6 baseline)

The first full baseline run of the scenario suite and the M4 trigger suite.
No tuning was done in this run: it exists to give MS7 (#9) a fixed set of
numbers to tune against, and to publish every metric against its PRD target,
misses included (design doc §10.5).

Two of the three matrix slots ran. The open-weights `qwen` slot was skipped
for want of a hosted-Qwen API key — see [Known gaps](#known-gaps).

## Method

Every input and script that produced a number below is listed here, so the
run can be reproduced or audited.

| Item | Value |
| ---- | ----- |
| Scenario suite | `evals/scenarios/` — 10 scenarios × 2 conditions (baseline / skill) |
| Trigger suite | `evals/triggers.json` — 100 prompts (60 positive, 40 negative) |
| Generator | `evals/run_bench.py` |
| Automated scoring | `evals/score.py` → `scores.json` |
| LLM judge | `evals/judge.py --seed 21` → `judgments/`, `judge_summary.json` |
| Trigger classifier | `evals/run_triggers.py` → `triggers/triggers_summary.json` |

### Models

Each slot's "skill" condition uses the artifact that model's real
distribution channel would ship, not the same file for all three (design
doc §14.3). The `qwen` slot did not run — see [Known gaps](#known-gaps).

| Slot | Provider model ID | Skill artifact for the "skill" condition |
| ---- | ----------------- | --------------------------------------- |
| claude | `claude-opus-5` (Anthropic Messages API) | full `skills/readable-code/SKILL.md` |
| gpt | `gpt-5.1` (OpenAI Chat Completions) | rendered `templates/agent-block.md` managed block |
| qwen | `qwen3.6-27b-instruct` — **not run** (no key) | would be `prompts/system-prompt.md` |

### Sampler settings

`evallib/models.py` `DEFAULT_SAMPLER`: **temperature 0.2, top_p 1.0**. The
`max_tokens` cap was raised from **4000** to **16000** partway through the
run, once it became clear the Claude and GPT reasoning tokens share that
budget with the written answer (scenario 06's Claude skill completion was
rejected as truncated at 4000). 23 completions carry `max_tokens: 4000` in
their `meta.json` and 17 carry `16000`; the exact value is in every
`raw/*/*/*.meta.json`. Every saved completion is complete regardless — a
completion that hits `max_tokens` is rejected, not stored, so no truncated
file was scored.

The `claude` slot ran at the **model's default sampling** — `claude-opus-5`
rejects a `temperature` / `top_p` override with an HTTP 400, so `max_tokens`
is its only sampler control. The `gpt` slot ran at the settings above. This
is recorded verbatim in each `raw/*/*/*.meta.json`.

### Judge

Blind pairwise, A/B order seeded (`--seed 21`), 2 passes per judge. Each
pair is judged by every matrix slot except the one that generated it, so:

- `claude`-generated pairs → judged by `gpt-5.1` (the `qwen` judge was skipped)
- `gpt`-generated pairs → judged by `claude-opus-5` (the `qwen` judge was skipped)

40 judgments landed (10 scenarios × 2 generators × 2 passes × 1 available
judge). The second cross-judge per pair is a [known gap](#known-gaps).

### Harness fixes made during this run

The baseline surfaced four harness bugs that would have invalidated the
numbers. All four are fixed in the same change set as this run. Two are
prerequisites (without them there are no numbers at all); one recovered a
dropped cell; and one — the `extract_code()` fix — **materially changed the
published M1 and judge results**. The metrics below were all computed after
these fixes, not before:

| File | Fix | Effect on the numbers |
| ---- | --- | --------------------- |
| `evallib/models.py` | Stop sending `temperature` / `top_p` to `claude-opus-5` (HTTP 400); add `applied_sampler()` so `meta.json` records what the provider actually honored. | Without it the entire `claude` slot fails to generate — no numbers at all. |
| `evallib/models.py` | Raise `DEFAULT_SAMPLER.max_tokens` 4000 → 16000 so reasoning tokens don't truncate the written answer. | Recovered one `claude` cell (scenario 06 skill) that was being dropped as truncated. |
| `score.py` | `tokenize.TokenizeError` → `tokenize.TokenError` (the former does not exist; any completion that failed to tokenize crashed the whole scoring run). | Without it `score.py` exits non-zero and writes no `scores.json` — no M1 or M3. |
| `score.py`, `judge.py` | `extract_code()` now prefers a fenced block whose language tag matches the scenario's output file, instead of the longest block of any language — a skill completion that adds a `text` findings list longer than its `python` block was being scored as prose. | **Material.** Before the fix, `claude` M1 was **−59.6%** (a miss) because the skill's prose was scored as buggy code; after, **−89.5%**. Scenario 10 (de-slop) `claude` skill scores went from lint 1 → 4 / empty-words 1 → 8 (prose) to lint 1 → 1 / empty-words 1 → 1 (the actual code). Judge inputs changed the same way, so `judge.py` was re-run with `--force`. |

## Automated scoring (M1, M3)

### M1 — `taorc-lint` findings per 100 LOC, skill vs. baseline

Target: **≥ 60% reduction.** Pooled across all 10 scenarios per slot
(total findings ÷ total LOC, so a large clean file isn't outweighed by a
small noisy one).

| Slot | Baseline (/100 LOC) | Skill (/100 LOC) | Reduction | vs. target |
| ---- | ------------------- | ---------------- | --------- | ---------- |
| claude | 3.26 (15 findings / 460 LOC) | 0.34 (1 / 291) | **−89.5%** | pass |
| gpt | 0.64 (2 findings / 314 LOC) | 0.32 (1 / 314) | **−50.0%** | miss (small n) |
| pooled | 2.20 | 0.33 | **−84.9%** | pass |

The `gpt` slot's baseline output was already close to lint-clean (2 findings
across 10 scenarios), so its "miss" is one finding removed out of two — not
a signal that the skill underperforms there. The `claude` slot is where the
skill has room to work and it takes it (15 → 1).

### M3 — diff-size inflation on the guardrail scenarios

Target: **≤ 10% inflation**, skill vs. baseline, on scenarios 02 / 03 / 09
(the ones that exist to catch the skill *widening* a diff, design doc §10.1).

| Slot | Inflation | vs. target |
| ---- | --------- | ---------- |
| claude | **−8.5%** | pass |
| gpt | −5.4% | pass |

Per scenario (diff lines of the edit vs. starter, baseline → skill):

| Scenario | claude | gpt |
| -------- | ------ | --- |
| 02-fix-bug | 3 → 3 | 3 → 3 |
| 03-add-feature | 8 → 8 | 9 → 9 |
| 09-add-error-handling | 43 → 32 | 31 → 26 |

On scenario 03 the two `claude` completions returned the edit in different
shapes — the baseline echoed the whole `cart.py`, the skill returned only
the new `remove_line` function — but both represent the same ~4-line
addition, so both now score an 8-line diff. Scenario 09 shows the skill
*reducing* the diff (43 → 32); scenario 02 is identical on both slots.

**Correction (#23).** The first version of this run scored `claude`
scenario 03 skill at a 24-line diff and reported M3 as **+58.1% (miss)**.
`diff_lines_vs_starter` diffed the returned fragment against the full
starter and counted every un-echoed starter line as a deletion. The fix
(`score.py` `reconstruct_edited_file`) applies a fragment onto the starter
before diffing, so the metric measures the edit rather than the output
format. `scores.json` and the numbers above were regenerated with the
fixed scorer; no other cell changed, and the M2/judge inputs are
untouched.

### Descriptive automated metrics (no PRD target)

Pooled per slot, baseline → skill:

| Metric | claude | gpt |
| ------ | ------ | --- |
| comment-to-code ratio | 0.082 → 0.071 | 0.085 → 0.049 |
| why-comment share | 0.93 → 1.00 | 1.00 → 0.94 |
| mean nesting depth | 1.66 → 1.78 | 1.83 → 1.90 |
| empty-word identifier count (total) | 6 → 1 | 2 → 0 |

The skill drives empty-word names to near zero on both slots. It also
shortens files (claude total LOC 460 → 291) and slightly raises mean
nesting — a by-product of the shorter files, not deeper logic (max nesting
is unchanged on almost every cell).

## LLM judge (M2)

### M2 — blind pairwise preference for the skill output

Target: **≥ 70%.**

| Grouping | Skill preferred | Rate |
| -------- | --------------- | ---- |
| **overall** | **18 / 40** | **45%** — miss |
| claude-generated pairs (judge: gpt-5.1) | 10 / 20 | 50% |
| gpt-generated pairs (judge: claude-opus-5) | 8 / 20 | 40% |

Per scenario (skill preferred / 4 judgments, both generators pooled):

| Scenario | skill wins | Scenario | skill wins |
| -------- | ---------- | -------- | ---------- |
| 01-implement-function | 2 / 4 | 06-api-handler | 2 / 4 |
| 02-fix-bug | 2 / 4 | 07-refactor-nesting | 1 / 4 |
| 03-add-feature | 2 / 4 | 08-cli-script | 2 / 4 |
| 04-write-tests | 3 / 4 | 09-add-error-handling | 2 / 4 |
| 05-parse-transform | 2 / 4 | 10-de-slop | **0 / 4** |

### Per-category rubric (1–5, mean across judged pairs, all slots pooled)

| Category | skill | baseline | delta |
| -------- | ----- | -------- | ----- |
| N (naming) | 4.38 | 4.50 | −0.12 |
| C (comments) | 3.77 | 4.10 | **−0.32** |
| F (control flow / structure) | 4.47 | 4.42 | +0.05 |
| S (structure / decomposition) | 4.22 | 4.30 | −0.08 |
| T (tests, n = 4) | 4.25 | 4.50 | −0.25 |

### Reading M1 and M2 together

M1 and M2 point in opposite directions: the skill cuts objective lint
findings by ~85% pooled, but blind judges slightly *prefer* the baseline
output and rate the skill's comments lower (C −0.32). The two are not
measuring the same thing — `taorc-lint` counts rule violations; the judge
answers "which would a new reader understand faster" — and this run says
the skill is winning the first and losing the second. Every scenario is
close (no scenario is worse than 1/4 except de-slop at 0/4), so this is a
calibration gap, not a broken skill. It is exactly the tension #9 exists to
resolve, and the de-slop scenario (0/4, and the M1 case that first exposed
the `extract_code` bug) is the place to start.

## Trigger suite (M4)

Target: **≥ 90% activation on the 60 positives, ≤ 10% false fire on the 40
negatives.** Tier-1 proxy classifier (`--model claude`, `claude-opus-5`),
classifier sampler temperature 0.0 / top_p 1.0 / max_tokens 1000.

| Metric | Value | vs. target |
| ------ | ----- | ---------- |
| activation rate (positives) | **98.3%** (59 / 60) | pass |
| false-fire rate (negatives) | **0.0%** (0 / 40) | pass |
| `meets_m4` | **true** | — |

False fire by negative category — the dangerous half held:

| Category | False fires |
| -------- | ----------- |
| prose-readability (10) | 0 |
| code-explanation (5) | 0 |
| other (25) | 0 |

The one positive that did not activate is **pos-48**: *"This reads like
boilerplate from a chatbot; make it look like a person wrote it."* — a
de-slop request phrased without any of the skill's vocabulary. Consistent
with de-slop being the weakest scenario in M2; worth a look when #9 tunes
the `description`.

Tier 2 (10-prompt end-to-end spot check in real Claude Code) is a manual
step and was **not** done for this run.

## Summary against PRD targets

Three of the four metrics meet their target as a baseline; M2 misses. That
miss does not block #21 — this run is the fixed point #9 tunes from — but it
is real and is analysed in its section above.

| Metric | Target | Result | Status |
| ------ | ------ | ------ | ------ |
| M1 — lint reduction, skill vs. baseline | ≥ 60% | −84.9% pooled (claude −89.5%, gpt −50.0%) | **pass** pooled; gpt slot misses on n = 2 |
| M2 — blind pairwise skill preference | ≥ 70% | 45% (18 / 40) | **miss** |
| M3 — diff inflation on scenarios 02/03/09 | ≤ 10% | claude −8.5%, gpt −5.4% | **pass** (regenerated after the #23 scorer fix) |
| M4 — trigger activation / false fire | ≥ 90% / ≤ 10% | 98.3% / 0.0% | **pass** |

## Known gaps

- **`qwen` slot not run.** No hosted-Qwen API key was available
  (`OPENROUTER_API_KEY` unset). Missing from this baseline: all 20 `qwen`
  completions, the end-to-end validation of `prompts/system-prompt.md` (the
  fallback prompt, design doc §14.3), and the second cross-judge on every
  pair. M2 therefore rests on a single judge per pair. `run_bench.py` skips
  a keyless slot with a warning, so the run was not blocked.
- **M3 scorer fix (#23), applied.** `diff_lines_vs_starter` had assumed a
  full-file completion and misfired when a completion returned only the
  changed function. Fixed in `score.py`; this run's `scores.json` and the
  M3 section were regenerated with the fixed scorer (see the correction
  note in the M3 section). A follow-up (#26) taught the reconstruction to
  detect single-definition starters and fragment deletions; the numbers in
  this run are unchanged by it.
- **`max_tokens` changed mid-run** (4000 → 16000). Every stored completion
  is complete, but the two halves were generated under different caps.
- **Tier-2 trigger spot check** (real Claude Code, 10 prompts) not done.
- **Ollama mini-prompt smoke** (`run_smoke_ollama.py`, design doc §14.3):
  not re-run. The existing `evals/results/2026-08-28/smoke-ollama/` output
  still stands and stays unpublished — not fed into any metric here.

## Raw data

Everything below is in this directory.

- `raw/` — every completion plus its `*.meta.json`.
- `scores.json` — `score.py` output (M1, M3, descriptive metrics).
- `judgments/` — one file per judgment (40 files). **Canonical for this run**:
  every number in this document comes from here.
- `judge_summary.json` — preference counts and per-category rubric means,
  aggregated from `judgments/`. Canonical.
- `judgments-fixed/` and `judge_summary-fixed.json` — the same 40 pairs
  re-judged later, under MS7's `code_as_left_on_disk` (#9), which splices a
  fragment completion onto its starter before handing it to the judge.
  Added by the MS7 tuning run to show what that measurement change does to
  an already-published run; **not canonical, and not a correction of the
  numbers above**. M2 is 45.0% in both. The rubric means differ (C −0.32 →
  −0.23, N −0.12 → −0.03, S −0.08 → +0.05), but that is mostly the judge
  answering a second time: 29 of the 40 judgments changed rubric scores while
  only 2 had different inputs. See [the 2026-09-01
  write-up](../2026-09-01/RESULTS.md#the-judge-fragment-fix-moved-no-verdict-on-the-two-judgments-that-tested-it).
  Note also that `judgments-fixed/` was produced before the splice was gated
  to the `measure_diff_size` scenarios, so it spliced more scenarios than
  `judge.py` does now.
- `triggers/` — `run_triggers.py` output: `raw/<id>.json` per prompt and
  `triggers_summary.json`.
