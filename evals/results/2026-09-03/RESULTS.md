# Eval results — 2026-09-03 (test-coverage guidance, #32)

The follow-up to the [2026-09-01 MS7 tuning run](../2026-09-01/RESULTS.md),
targeting the one regression that run left open: `04-write-tests` lost a
judgment on both slots, and T was the only negative rubric delta.

**The mechanism was fixed and the metric did not move.** On the slot that
actually had the defect the change did exactly what it was designed to do —
coverage went from 6 cases to 8, the completion's own reasoning reversed, and
the pair recovered a judgment. In aggregate T is unchanged at −0.25, and M2
fell from 70.0% to 68.4%, driven almost entirely by scenarios this change
cannot touch. Read the [Reading this run](#reading-this-run) section before
treating any number here as a result.

## Method

| Item | Value |
| ---- | ----- |
| Scenario suite | `evals/scenarios/` — 10 scenarios × 2 conditions (baseline / skill) |
| Generator | `evals/run_bench.py` |
| Automated scoring | `evals/score.py` → `scores.json` (**scorer version 2**) |
| LLM judge | `evals/judge.py --seed 21` → `judgments/`, `judge_summary.json` |
| Trigger suite | **not re-run** — see [M4](#m4--not-re-measured) |

### Models

| Slot | Provider model ID | Skill artifact for the "skill" condition |
| ---- | ----------------- | --------------------------------------- |
| claude | `claude-opus-5` (Anthropic Messages API) | full `skills/readable-code/SKILL.md` |
| gpt | `gpt-5.1` (OpenAI Chat Completions) | rendered `templates/agent-block.md` managed block |
| qwen | `qwen3.6-27b-instruct` — **not run** (no `OPENROUTER_API_KEY`) | would be `prompts/system-prompt.md` |

### Baseline completions were reused, not regenerated

All 20 baseline completions were copied forward from
`evals/results/2026-09-01/raw/`, which had itself copied them from
`2026-08-29`. Their `meta.json` files still carry their original 2026-08-29
generation timestamps, which is what makes the reuse auditable. All 20 skill
completions were generated fresh against the changed artifacts.

The baseline column is therefore numerically identical to both prior runs by
construction. Only the skill column moved.

### Sampler settings

`evallib/models.py` `DEFAULT_SAMPLER`: temperature 0.2, top_p 1.0, max_tokens
16000. The `claude` slot ran at the **model's default sampling** — `claude-opus-5`
rejects a `temperature` / `top_p` override with an HTTP 400 — so `max_tokens` is
its only sampler control, and adaptive thinking is on by default. This matters
for [the M3 artifact](#the-02-fix-bug-extraction-artifact) below.

## What was changed

The catalog's rule set was **not** changed. No rule was added, deprecated, or
renumbered, and no `instruction` field was edited, so the book-fidelity
re-check (design doc §13) is not triggered by this run.

That was the finding, not a shortcut, and it is the second run in a row to
reach it. Reading the losing completion against the catalog showed every T
rule was applied correctly — `T2`, `T3` and `T5` were all satisfied, and the
skill's test *names* were better than the baseline's. What failed was `X1`
reaching a place it does not govern.

The `claude` skill completion for `04-write-tests` said so itself, under its
own "What I did not do" heading:

> outside the four cases you listed (`X1`)

`X1` is a diff-width guardrail. On a `write`-mode task there is no diff to
widen, so it had nothing to bound and bound coverage instead. The five cases
it dropped each reach a different outcome — the `min()` boundary, a zero cap,
a non-binding cap, 100%-off with a cap, and validation ordering — so none was
reachable from a case it kept.

A catalog rule was rejected deliberately. "Each behavior with a distinct
outcome earns its own test" is an obligation about completeness, not about
how fast a reader understands a file; every existing T rule is about the
reading experience. A completeness rule would make T mean two things under one
permanent prefix, and rule IDs never move.

| File | Change |
| ---- | ------ |
| `skills/readable-code/SKILL.md` | A counter-pull paragraph under the T table, in the same shape as the ones C, E and the guardrails already carry. Self-check item 9 widened from `T3`-only to also ask whether each distinct outcome has a case. |
| `skills/readable-code/references/tests.md` | New section, "Brevity bounds the code, not the coverage" — the write-direction half of a bound the file previously stated only for review. |
| `templates/agent-block.md` | One line mirrored into the managed block (the `gpt` slot's artifact), regenerated into every adapter by `scripts/build.py`. |

Self-check item 9 and the managed-block line are both **scoped to a suite the
task asked for** ("Do not add cases to a suite the task did not ask you to
extend"), deliberately mirroring how the `C14` item was scoped in the MS7 run
to keep it off M3. That scoping held — see [M3](#m3--diff-size-inflation).

## The diagnosis did not hold on both slots

The issue recorded both slots regressing on `04-write-tests`. Only one of them
regressed for the reason the issue gives.

| Slot | Skill vs. baseline coverage, 2026-09-01 | Mechanism |
| ---- | -------------------------------------- | --------- |
| claude | 6 cases vs. 14 | Real. Coverage traded away, `X1` cited as the reason. |
| gpt | 8 cases vs. 8 — **identical** | None. No coverage delta exists to explain. |

The `gpt` regression was judge instability. Both passes had the skill labeled
`A`, and answered `A` then `B` — same inputs, same label assignment, opposite
verdicts. So the evidence behind this change was ever only one pair on one
slot, which is exactly the sample size the issue's own technical note says to
treat as noise.

## Did the change do what it was designed to do?

On the `claude` slot, yes, and unambiguously.

| Measure | 2026-09-01 | 2026-09-03 | Baseline |
| ------- | ---------- | ---------- | -------- |
| test functions | 5 | **7** | 11 |
| test cases (counting parametrization) | 6 | **8** | 14 |
| non-binding-cap branch covered | no | **yes** | yes |
| floor-division rounding covered | no | **yes** | no (baseline only suggests it in prose) |

The completion's own reasoning reversed. Where it previously justified the
omissions as "outside the four cases you listed (`X1`)", it now opens its notes
with:

> **Two tests beyond your four bullets.** Both pin a distinct outcome of the
> code as written, so I'd argue they belong

It also flagged the floor-division case as a decision for the author rather
than asserting intent — which is the "say where you stopped" half of the new
reference section doing its job.

Four cases the baseline covers are still missing: the cap-equals-discount
boundary, the zero cap, 100%-off-with-a-cap, and validation-before-capping. The
gap narrowed; it did not close.

On the `gpt` slot the managed-block line **did not land**: coverage is
unchanged at 4 functions / 8 cases, identical to both prior runs. One line in a
465-token block is evidently not enough leverage, and that slot had no defect
to fix in the first place.

## Automated scoring (M1, M3)

### M1 — lint findings per 100 LOC, skill vs. baseline

Target: **≥ 60% reduction.** Pooled per slot (total introduced findings ÷ total LOC).

This run is scored under **scorer version 2**, the #31 fix that stops charging a
completion for a finding it inherited unchanged from the starter. The published
`2026-09-01/scores.json` is version 1, so it is not directly comparable. Both
are given, with 2026-09-01 re-scored under v2 for the honest comparison. Its
published file was **not** overwritten.

| Slot | 2026-09-01 (v1, as published) | 2026-09-01 (v2, re-scored) | 2026-09-03 (v2) | vs. target |
| ---- | ----------------------------- | -------------------------- | --------------- | ---------- |
| claude | −70.9% | −79.2% | **−78.2%** (2 / 302 vs. 14 / 460) | pass |
| gpt | −100.0% | −100.0% | **−4.6%** (1 / 329 vs. 1 / 314) | **miss** |
| pooled | −79.1% | −84.2% | **−75.5%** | pass |

The old scorer *understated* the claude slot: one baseline and one skill
finding in the 2026-09-01 run were inherited from the starter rather than
introduced. That is the #31 comparison the last run left owing.

**The `gpt` slot's M1 has no resolving power and should not be read as a
regression.** Its baseline is a single finding across 314 LOC, so the metric
swings from −100% to 0% on one finding either way. The single skill finding
this run is a `C1` restating comment in the `04-write-tests` file
(`# 20% off 10_00 -> 2_00 discount`) — unrelated to coverage, and the kind of
line that appears or does not appear at sampling temperature. The previous
run's −100.0% was already published as not real, because it depended on an
`X3` breach; this run's −4.6% is not real either, for the opposite reason.
Neither run establishes `gpt` M1.

The two claude findings are the same two as the last run, both names the skill
is correct to leave alone: `state` in `07-refactor-nesting` (the starter's own
vocabulary, `X2`) and `value` in `06-api-handler`.

### M3 — diff-size inflation

Target: **≤ 10% inflation**, skill vs. baseline, on scenarios 02 / 03 / 09.
M3 is the **mean of per-scenario ratios**, so a single scenario can dominate it.

| Slot | As scored | Corrected | 2026-09-01 | vs. target |
| ---- | --------- | --------- | ---------- | ---------- |
| claude | **+232.8%** | **−11.6%** | +0.3% | miss as scored; **pass corrected** |
| gpt | **+3.0%** | +3.0% | −15.1% | pass |

Per scenario (diff lines vs. starter, baseline → skill):

| Scenario | claude | gpt |
| -------- | ------ | --- |
| 02-fix-bug | 3 → **25** (artifact; truly 3) | 3 → 3 |
| 03-add-feature | 8 → 8 | 9 → 13 |
| 09-add-error-handling | 43 → 28 | 31 → 20 |

#### The `02-fix-bug` extraction artifact

The claude completion delivered a **correct, minimal, one-operator fix** —
`available + qty` → `available - qty` — with an exemplary account of what it
left alone. It presented that fix as a **unified diff** rather than as a
function body:

```text
     def reserve(self, sku, qty):
         available = self.counts.get(sku, 0)
-        self.counts[sku] = available + qty
+        self.counts[sku] = available - qty
```

`score.extract_code()` returned those `-` / `+` markers verbatim, and
`reconstruct_edited_file()` spliced them into the starter as literal source
lines. The 25-line diff is the harness failing to parse a diff, not the model
over-editing. That one scenario contributes **+733%** to a three-scenario mean;
correcting it to its true 3 lines gives **−11.6%**, which is both a pass and an
improvement on 2026-09-01's +0.3%.

This is a third variant of a known harness gap. `#23` taught `score.py` to
splice a returned *fragment* onto the starter, and the MS7 run taught `judge.py`
the same. Neither handles a returned *diff*. It is a one-off in this run
(1 of 20 completions) and nothing about a test-coverage guidance change
plausibly causes a diff-formatted bugfix answer — the claude slot runs at the
model's default sampling, where presentation format varies freely.

**It was not re-rolled.** Regenerating a cell because its output is
inconvenient would be p-hacking; the artifact is reported and carried.

## LLM judge (M2)

### M2 — blind pairwise preference for the skill output

Target: **≥ 70%.**

| Grouping | Skill preferred | Rate | 2026-09-01 |
| -------- | --------------- | ---- | ---------- |
| **overall, as run** | **26 / 38** | **68.4% — miss** | 70.0% |
| **excluding the `02-fix-bug` extraction artifact** | **26 / 36** | **72.2% — pass** | 72.2% |
| claude-generated pairs (judge: gpt-5.1) | 11 / 20 | 55.0% | 75.0% |
| gpt-generated pairs (judge: claude-opus-5) | 15 / 18 | 83.3% | 65.0% |

`02-fix-bug`/gpt left identical files in both conditions and was correctly
detected as undecidable, not judged, and not billed — the fix the last run
described is working. `02-fix-bug`/claude is no longer identical **only
because of the extraction artifact**, and the judge saw a mangled fragment for
the skill against a clean file for the baseline. It went 0/2, for a reason that
has nothing to do with readability. Excluding it is the same correction
2026-09-01 applied to its four undecidable judgments.

Per pair (skill wins / 2 judgments):

| Scenario | claude | gpt |
| -------- | ------ | --- |
| 01-implement-function | 2/2 → 2/2 | 0/2 → **2/2** |
| 02-fix-bug | 1/2 → **0/2** (artifact) | 1/2 → undecidable, not judged |
| 03-add-feature | 2/2 → **1/2** | 2/2 → 2/2 |
| **04-write-tests** | **0/2 → 1/2** | 1/2 → 1/2 |
| 05-parse-transform | 2/2 → 2/2 | 2/2 → 2/2 |
| 06-api-handler | 2/2 → **1/2** | 1/2 → **2/2** |
| 07-refactor-nesting | 0/2 → 0/2 | 2/2 → **0/2** |
| 08-cli-script | 2/2 → 2/2 | 0/2 → 0/2 |
| 09-add-error-handling | 2/2 → 2/2 | 2/2 → 2/2 |
| 10-de-slop | 2/2 → 2/2 | 2/2 → 2/2 |

**The target pair recovered.** `04-write-tests`/claude went 0/2 → 1/2, and on
the pass that flipped, the judge's T score for the skill rose from 4 to 5.

**Eight of twenty pairs moved, and six of them are scenarios this change
cannot touch.** `01`/gpt gained two, `07`/gpt lost two, `06` flipped on both
slots in opposite directions. The only artifact difference on those scenarios
is one added line in the managed block and one paragraph in `SKILL.md`, both
about tests. This is resampling noise at a magnitude that swamps the effect
being measured. See [Reading this run](#reading-this-run).

### Per-category rubric (1–5, mean across judged pairs, both slots pooled)

| Category | skill | baseline | delta | 2026-09-01 delta |
| -------- | ----- | -------- | ----- | ---------------- |
| N (naming) | 4.45 | 4.32 | +0.13 | +0.28 |
| C (comments) | 4.05 | 3.95 | +0.11 | +0.38 |
| F (control flow / structure) | 4.39 | 4.21 | +0.18 | +0.33 |
| S (structure / decomposition) | 4.18 | 4.18 | +0.00 | +0.12 |
| **T (tests, n = 4)** | **4.25** | **4.50** | **−0.25** | **−0.25** |

**T did not move.** The delta is identical to 2026-09-01's to two decimal
places, and its composition changed underneath: on the claude slot the skill's
T rose 4 → 5 on one pass, and on the gpt slot it fell 5 → 4 on one pass. Those
cancelled exactly. With n = 4 judgments drawn from a single scenario, that is
a coincidence, not a finding.

N, C and F all fell relative to 2026-09-01 and now sit inside the ±0.1–0.25
noise floor that run measured. The MS7 gains are not clearly reversed, but they
are no longer clearly present either — which is a statement about the harness,
not about the change. Nothing in this change set touches naming or comments.

## M4 — not re-measured

Target: ≥ 90% activation / ≤ 10% false fire. **Carried forward from
2026-09-01: 100.0% / 0.0%.**

M4 is a function of the skill's `description` frontmatter, and this change does
not touch it — `git diff` over `skills/readable-code/SKILL.md` shows no change
above the `---`. Re-running 100 classifier prompts against a byte-identical
input would have cost roughly as much as the entire rest of this run to
re-confirm a number that cannot have moved. It is carried, not re-measured,
and that distinction is the reason this section exists.

## Summary against PRD targets

| Metric | Target | 2026-09-01 | 2026-09-03 | Status |
| ------ | ------ | ---------- | ---------- | ------ |
| M1 — lint reduction | ≥ 60% | −79.1% pooled (v1) | **−75.5% pooled** (v2); claude −78.2%, gpt −4.6% | **pass** pooled and on claude; `gpt` unmeasurable |
| M2 — blind pairwise preference | ≥ 70% | 70.0% | **68.4%** as run; **72.2%** excluding the artifact pair | **miss** as run, **pass** corrected |
| M3 — diff inflation on 02/03/09 | ≤ 10% | claude +0.3%, gpt −15.1% | **claude +232.8% as scored / −11.6% corrected; gpt +3.0%** | **miss** as scored, **pass** corrected |
| M4 — trigger activation / false fire | ≥ 90% / ≤ 10% | 100.0% / 0.0% | **carried forward** | not re-measured |

## Reading this run

The issue behind this change asked for T to stop being negative and for
`04-write-tests` to recover. One of those happened.

- **The mechanism is fixed, and that is verifiable without the judge.** The
  completion covers two more distinct outcomes than it did, and its stated
  reason for omitting them is gone. That is a file-level fact, not a metric.
- **T is unchanged at −0.25 and rests on n = 4.** It is one scenario's worth of
  judgments. The issue's own technical note said to treat a T improvement
  smaller than one full pair as noise; this run delivered exactly one pair, and
  the aggregate absorbed it. **T cannot carry weight until the suite has a
  second test-writing scenario** — filed as a separate concern in that issue and
  still the blocker.
- **M2's 1.6pp fall is not attributable to this change.** Six of the eight pairs
  that moved are on scenarios with no test content, where the only artifact
  difference is guidance about tests. Both directions of movement are noise.
- **Two of the four metrics now report a miss that inspection overturns.** M3's
  claude miss is a diff-parsing gap in the scorer; M2's miss is the same
  artifact reaching the judge. In both cases the corrected figure passes. A
  harness where the headline number depends this heavily on hand-correction is
  the thing most worth fixing next.

## Known gaps

- **`qwen` slot not run.** No `OPENROUTER_API_KEY`. Missing: all 20 `qwen`
  completions, end-to-end validation of `prompts/system-prompt.md`, and the
  second cross-judge on every pair. M2 rests on a single judge per pair, as in
  both prior runs.
- **`score.py` and `judge.py` cannot parse a completion returned as a unified
  diff.** One completion in this run (`02-fix-bug`/claude) triggered it, and it
  is single-handedly responsible for M3's claude miss and M2's fall below
  threshold. Worth a scorer fix and a re-score of this run; the completions are
  committed, so no regeneration would be needed.
- **T still rests on n = 4** from one scenario. A second test-writing scenario
  is a prerequisite for this metric meaning anything.
- **The `gpt` slot's M1 is unmeasurable**, at −100.0% last run and −4.6% this
  run, on a baseline of one finding. Not a regression; not a result.
- **The managed-block mirror did not change `gpt` behavior.** Coverage there is
  byte-identical across all three runs. If the `gpt` slot is expected to carry
  this guidance, one line in the block is not enough.
- **Pair-level judge noise exceeds the effect size.** Eight of twenty pairs
  moved between two runs whose only artifact difference concerns tests. More
  passes per judge, or the second cross-judge, are needed before a single-pair
  effect is measurable at all.
- **Baseline completions reused** from 2026-08-29 for the third run running, so
  baseline-vs-baseline drift remains unmeasured.
- **M4 carried forward, not re-run** (see above). **Tier-2 trigger spot check**
  (real Claude Code, 10 prompts) not done. **Ollama mini-prompt smoke** not
  re-run.

## Raw data

- `raw/` — every completion plus its `*.meta.json`. The 20 `skill.*` files were
  generated for this run; the 20 `baseline.*` files were copied from
  `../2026-09-01/raw/` and keep their original 2026-08-29 metadata. The 20
  `*.error.json` files are the `qwen` slot's missing key.
- `scores.json` — `score.py` output, scorer version 2.
- `judgments/` — one file per judgment (38 files; `02-fix-bug`/gpt undecidable
  and unbilled).
- `judge_summary.json` — preference counts and per-category rubric means.
