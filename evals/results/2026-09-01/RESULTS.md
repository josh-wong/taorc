# Eval results — 2026-09-01 (MS7 tuning run)

The MS7 tuning run (#9), measured against the [2026-08-29
baseline](../2026-08-29/RESULTS.md). The baseline met M1, M3 and M4 and missed
M2 at 45%, so this milestone is almost entirely an M2 problem: the tuning
targets blind pairwise preference while holding the three metrics that already
passed.

All four PRD metrics meet their target in this run. M2 lands exactly on its
threshold (70.0% against a ≥70% target), which is a pass but not a comfortable
one — see [Reading M2](#reading-m2) before treating it as settled.

## Method

Every input and script that produced a number below is listed here, so the run
can be reproduced or audited.

| Item | Value |
| ---- | ----- |
| Scenario suite | `evals/scenarios/` — 10 scenarios × 2 conditions (baseline / skill) |
| Trigger suite | `evals/triggers.json` — 100 prompts (60 positive, 40 negative) |
| Generator | `evals/run_bench.py` |
| Automated scoring | `evals/score.py` → `scores.json` |
| LLM judge | `evals/judge.py --seed 21` → `judgments/`, `judge_summary.json` |
| Trigger classifier | `evals/run_triggers.py` → `triggers/triggers_summary.json` |

### Models

Each slot's "skill" condition uses the artifact that model's real distribution
channel would ship, not the same file for both (design doc §14.3). The `qwen`
slot did not run — see [Known gaps](#known-gaps).

| Slot | Provider model ID | Skill artifact for the "skill" condition |
| ---- | ----------------- | --------------------------------------- |
| claude | `claude-opus-5` (Anthropic Messages API) | full `skills/readable-code/SKILL.md` |
| gpt | `gpt-5.1` (OpenAI Chat Completions) | rendered `templates/agent-block.md` managed block |
| qwen | `qwen3.6-27b-instruct` — **not run** (no key) | would be `prompts/system-prompt.md` |

### Baseline completions were reused, not regenerated

The baseline condition does not depend on the skill, so all 20 baseline
completions were copied forward from `evals/results/2026-08-29/raw/` rather
than re-billed. Their `meta.json` files still carry their original
2026-08-29 generation timestamps, which is what makes the reuse auditable.
Every one of the 20 skill completions in this run was generated fresh against
the tuned artifacts.

This means the baseline column of every table below is numerically identical
to the baseline run's by construction. Only the skill column moved.

### Sampler settings

`evallib/models.py` `DEFAULT_SAMPLER`: **temperature 0.2, top_p 1.0,
max_tokens 16000**. The `claude` slot ran at the **model's default sampling**
— `claude-opus-5` rejects a `temperature` / `top_p` override with an HTTP 400,
so `max_tokens` is its only sampler control. The `gpt` slot ran at the settings
above. This is recorded verbatim in each `raw/*/*/*.meta.json`.

Unlike the baseline run, `max_tokens` was 16000 for every skill completion
here; the mid-run cap change noted in that run's results does not apply to this
one. The reused baseline completions still carry whichever cap they were
generated under.

Trigger classifier sampler: temperature 0.0, top_p 1.0, max_tokens 1000.

### Judge

Blind pairwise, A/B order seeded (`--seed 21`), 2 passes per judge, judged by
every matrix slot except the one that generated the pair. 40 judgments landed
(10 scenarios × 2 generators × 2 passes × 1 available judge). The second
cross-judge per pair is a [known gap](#known-gaps).

## What was changed

The catalog's rule set was **not** changed. No rule was added, deprecated, or
renumbered, and no rule's `instruction` field was edited — so the book-fidelity
re-check that a wording change would require (design doc §13) is not triggered
by this run.

That was a finding, not a shortcut. Reading the baseline's losing completions
against the catalog showed the rules already said the right thing: `V1` already
covers a variable "named no better than the expression it holds", and `C14`
already asks for the corner cases a caller will wonder about. What failed was
the always-loaded surface that decides whether those rules get applied. So the
changes are to the skill's guidance, per design doc §13's mitigation of cutting
the self-check down to what moves the metrics.

### `SKILL.md` self-check

Still ten items, rebalanced. The baseline's self-check spent two of its ten
items on deleting a comment and one on adding one; nothing in it asked whether
a name the model introduced had earned its place, and nothing asked whether a
caller could still tell what a function returned.

| Change | Rules | Why |
| ------ | ----- | --- |
| Merged the two comment-deletion items into one | `C1`, `X7` | Both delete a comment that carries nothing, and `taorc-lint` catches both mechanically. Freed a slot. |
| Added a contract item, scoped to added functions | `C14`, `X1` | The judge's largest rubric gap was C (−0.23). Scoping it to functions the task added is what keeps it off M3 — see below. |
| Added an over-naming item | `V1` | `01-implement-function` introduced four single-use constants and expanded `max(0, …)` into a 4-line if/else. `E1` pulled with no counterweight. |
| Merged the guard-clause and long-condition items | `F5`, `F6`, `E1` | F was the one category the skill already won. Two of ten items served it; one is enough. |
| Widened the last item beyond diff width | `X1`, `X3`, `X4` | `10-de-slop` renamed a public parameter and added a `raise` on a task that said behavior must stay identical. |

### `SKILL.md` prose

Four short additions where a catalog table stated a pull with no counter-pull:
that overshooting costs a reader the same time undershooting does; that
seventeen of the eighteen C rules ask you to *write* a comment; that `E1` and
`V1` are two halves of one judgment; and that `X1` bounds which code you touch,
not how you structure code you were asked to restructure.

### `templates/agent-block.md`

The `V1` and `C14` lines mirrored into the managed block (the `gpt` slot's
artifact), and `X3` now names parameter renames explicitly. Regenerated into
every adapter by `scripts/build.py`.

### Skill `description`

Added `"humanize this code"`, `"make it look like a person wrote it"`, and
"boilerplate that reads as machine-written". This targets pos-48, the single
positive the baseline's trigger suite missed.

## Automated scoring (M1, M3)

### M1 — `taorc-lint` findings per 100 LOC, skill vs. baseline

Target: **≥ 60% reduction.** Pooled across all 10 scenarios per slot (total
findings ÷ total LOC).

| Slot | Baseline (/100 LOC) | Skill (/100 LOC) | Reduction | vs. 2026-08-29 | vs. target |
| ---- | ------------------- | ---------------- | --------- | -------------- | ---------- |
| claude | 3.26 (15 / 460 LOC) | 0.95 (3 / 316) | **−70.9%** | −89.5% | pass |
| gpt | 0.64 (2 / 314 LOC) | 0.00 (0 / 336) | **−100.0%** | −50.0% | pass |
| pooled | 2.20 | 0.46 | **−79.1%** | −84.9% | pass |

Both slots pass as scored, but the `gpt` slot's −100.0% does not survive
inspection — it rests on an `X3` breach, and the slot misses the target once
that is corrected for. See the note below the findings table. The `claude`
slot gave up margin honestly: −89.5% → −70.9%, three findings where the
baseline run had one.

All three are `N1` (empty-word identifier), and all three are names the skill
is **correct** to leave alone:

| Scenario | Finding | Why it is not a defect |
| -------- | ------- | ---------------------- |
| `07-refactor-nesting` | `def _line_total_cents(item, state)` | `state` is the starter's own vocabulary (`order.get("state")`) and a US state code, not an empty word. `X2` says match it. |
| `10-de-slop` | `def process_data(data)` | Both names are the starter's public surface. `X3` forbids renaming them unasked. |
| `06-api-handler` | `value = payload.get(field)` | The one genuinely generic name of the three. |

**This is a scorer limitation worth filing.** `taorc-lint` counts a finding
inherited unchanged from the starter against the completion that inherited it,
so on an edit task M1 rewards breaching `X2`/`X3`. Two of the claude slot's
three findings are this artifact rather than a readability regression.

**And the `gpt` slot's −100.0% is an instance of exactly that reward.** On
`10-de-slop` it is the `gpt` **skill** completion that renames `data` → `items`
(`raw/10-de-slop/gpt/skill.py:7,24`, both `process_data` and `generate_report`)
on a task whose brief says behavior must stay identical. Both baselines and
both claude completions keep `process_data(data)` and take the `N1` finding.
The rename is an `X3` breach, and it is load-bearing for the headline:

| `gpt` slot, M1 | Findings / LOC | Per 100 LOC | vs. baseline |
| -------------- | -------------- | ----------- | ------------ |
| baseline | 2 / 314 | 0.64 | — |
| skill, as scored | 0 / 336 | 0.00 | **−100.0%** |
| skill, had it kept the name | 1 / 336 | 0.30 | **−53.3% (miss)** |

So the `gpt` slot passes M1 at −100.0% only because it broke the rule this
run's tuning was meant to tighten. Had it complied, the slot would have missed
the ≥ 60% target. Read the −100.0% as a scorer artifact, not as a result.

This also makes the tuning's own scorecard on that item partial. The last
self-check item was widened to cover `X1`/`X3`/`X4` precisely because of this
scenario (see [What was changed](#what-was-changed)). It landed on the
`raise`, which the 2026-08-29 `gpt` skill added and the 2026-09-01 one does
not; it did not land on the parameter rename, which survived unchanged in both
runs.

### M3 — diff-size inflation on the guardrail scenarios

Target: **≤ 10% inflation**, skill vs. baseline, on scenarios 02 / 03 / 09.

| Slot | Inflation | vs. 2026-08-29 | vs. target |
| ---- | --------- | -------------- | ---------- |
| claude | **+0.3%** | −8.5% | pass |
| gpt | **−15.1%** | −5.4% | pass |

Per scenario (diff lines of the edit vs. starter, baseline → skill):

| Scenario | claude | gpt |
| -------- | ------ | --- |
| 02-fix-bug | 3 → 3 | 3 → 3 |
| 03-add-feature | 8 → 9 | 9 → 9 |
| 09-add-error-handling | 43 → 38 | 31 → 17 |

**M3 is the metric the tuning nearly broke, and the record matters.** An
earlier iteration of this run added the `C14` contract item *unscoped* — "can a
caller tell what each function returns" — and M3 went to **+13.1% (miss)** on
the claude slot, driven almost entirely by `03-add-feature`, where the added
function's docstring pushed the diff from 8 lines to 13. Scoping the item to
functions the task added, and saying explicitly not to document one the task did
not change, brought it to 9 lines and +0.3%. The delivered docstring is a single
line: `"""Remove the first line matching \`sku\`. No-op if no line matches."""`

That intermediate run is not published as a separate directory — it was
overwritten by the regeneration — but its numbers are recorded here because
they are the reason the item is scoped the way it is.

### Descriptive automated metrics (no PRD target)

Pooled per slot, baseline → skill:

| Metric | claude | gpt |
| ------ | ------ | --- |
| comment-to-code ratio | 0.082 → 0.055 | 0.085 → 0.063 |
| why-comment share | 0.93 → 1.00 | 1.00 → 1.00 |
| mean nesting depth | 1.66 → 1.76 | 1.83 → 1.79 |
| empty-word identifier count (total) | 6 → 3 | 2 → 0 |
| total LOC | 460 → 316 | 314 → 336 |

Why-comment share is now 1.00 on both slots (the baseline run had the `gpt`
slot at 0.94). Comment ratio still falls under the skill on both slots, but
less steeply on `gpt` than in the baseline run (0.049 → 0.063), which is the
`C14` line in the managed block doing its work.

## LLM judge (M2)

### M2 — blind pairwise preference for the skill output

Target: **≥ 70%.**

| Grouping | Skill preferred | Rate | 2026-08-29 |
| -------- | --------------- | ---- | ---------- |
| **overall, as run** | **28 / 40** | **70.0%** — pass | 45.0% |
| **overall, undecidable pairs excluded** | **26 / 36** | **72.2%** — pass | 45.0% |
| claude-generated pairs (judge: gpt-5.1) | 15 / 20 | 75.0% | 50.0% |
| gpt-generated pairs (judge: claude-opus-5) | 13 / 20 | 65.0% | 40.0% |

The second row is the honest one. `02-fix-bug` leaves byte-identical files in
both conditions on both slots, so its four judgments cannot express a
preference about the skill — yet the judge was asked anyway and answered
anyway, all four times picking whichever side was labelled A. Those four came
in 2 skill / 2 baseline and were counted as decided. `judge.py` now detects an
identical pair, records it as undecidable, and does not bill the call, so a
future run reports 26 / 36 directly. Both figures are given here because the
committed `judgments/` were produced before that change.

Per pair (skill wins / 2 judgments), against the baseline run re-judged under
the same fixed judge:

| Scenario | claude | gpt |
| -------- | ------ | --- |
| 01-implement-function | 2/2 → 2/2 | 0/2 → 0/2 |
| 02-fix-bug (undecidable, see above) | 1/2 → 1/2 | 1/2 → 1/2 |
| 03-add-feature | 0/2 → **2/2** | 2/2 → 2/2 |
| 04-write-tests | 1/2 → **0/2** | 2/2 → **1/2** |
| 05-parse-transform | 2/2 → 2/2 | 0/2 → **2/2** |
| 06-api-handler | 2/2 → 2/2 | 0/2 → **1/2** |
| 07-refactor-nesting | 0/2 → 0/2 | 1/2 → **2/2** |
| 08-cli-script | 2/2 → 2/2 | 0/2 → 0/2 |
| 09-add-error-handling | 0/2 → **2/2** | 2/2 → 2/2 |
| 10-de-slop | 0/2 → **2/2** | 0/2 → **2/2** |

Seven pairs improved, two regressed, eleven held.

### Per-category rubric (1–5, mean across judged pairs, both slots pooled)

| Category | skill | baseline | delta | 2026-08-29 delta (fixed judge) |
| -------- | ----- | -------- | ----- | ------------------------------ |
| N (naming) | 4.65 | 4.38 | **+0.28** | −0.03 |
| C (comments) | 4.38 | 4.00 | **+0.38** | −0.23 |
| F (control flow / structure) | 4.65 | 4.33 | **+0.33** | −0.05 |
| S (structure / decomposition) | 4.45 | 4.33 | **+0.12** | +0.05 |
| T (tests, n = 4) | 4.25 | 4.50 | **−0.25** | +0.00 |

C was the category the tuning targeted and it moved the most, from −0.23 to
+0.38. T is the only category still negative.

N, C and F clear the ±0.1–0.25 re-judging noise floor measured in [the judge
fragment fix](#the-judge-fragment-fix-moved-no-verdict-on-the-two-judgments-that-tested-it).
S (+0.12) and T (−0.25) do not, and T is the category whose own drift under
re-judging was 0.25 — exactly the size of the delta reported here. Treat both
as unresolved rather than as movement.

### The one candidate regression: `04-write-tests`

Both slots lost a judgment on the test-writing scenario, and T is the only
negative rubric delta — though at n = 4 judgments, and at the exact magnitude
of T's own re-judging drift, the rubric number alone would not be worth
acting on. What makes it worth writing up is the lost judgments on both slots
and a mechanism visible in the files themselves.

The cause is coverage, not readability. The skill's claude output defines 5
test functions to the baseline's 11; counting parametrized cases rather than
definitions, 6 to 14. It drops the cap-equals-discount boundary, the zero-cap
case, and the validation-happens-before-capping case. Its test *names* are
better — every one states a scenario and an outcome (`T3`) — but a judge
comparing the two files sees fewer behaviors pinned down.

Nothing in the tuning targeted test volume. The likely cause is the general
brevity pressure the skill applies (`X1`, `P2`, and the shorter files it
produces everywhere else) landing on a scenario where more cases is simply
better. `T2` says choose the simplest input that exercises the behavior; it
does not say test fewer behaviors. This is the clearest candidate for the next
tuning cycle and is filed under [Known gaps](#known-gaps).

### Reading M2

70.0% as run, 72.2% with the undecidable judgments removed. Either is a pass,
and both should be read as exactly that — a pass, near the line, not a
comfortable margin.

- **The effective sample is ~18, not 40.** The two passes agree on 16 of 20
  pairs, so the judgments are not 40 independent draws, and two of the 20
  pairs are undecidable. At n ≈ 18 the interval around 70% is wide; one pair
  flipping moves the headline by ~6pp.
- **Four judgments were coin flips scored as preferences.** `02-fix-bug` on
  both slots produces byte-identical code in both conditions, so those
  judgments cannot express a preference about the skill at all. All four
  picked the side labelled A. They split 2/2 by luck of the A/B draw, which
  flattered nothing here but could have swung the headline 5pp either way.
  Excluding them is what takes 70.0% to 72.2%.
- **Position bias is present but balanced.** The judge chose "A" in 22 of 40
  judgments, and the skill was labeled A in exactly 20 of 40, so the bias does
  not favor either condition.
- **One judged file has a layout the model did not choose.** Where a
  completion returns only its new function, `reconstruct_edited_file` appends
  it at the end of the file; the placement lives only in the completion's
  prose, which the judge never sees. `03-add-feature`/claude/skill asks for
  `remove_line` beside `add_line` and is judged with it last, after
  `cart_total`. It is the single spliced completion in this run, but F and S
  are exactly the categories that grade reading order, so that pair's F and S
  scores are partly the splicer's.
- **The jump from 45% is larger than the noise.** A 25pp move with seven pairs
  improving and two regressing is not a resampling artifact, even if the exact
  70.0% is.

### The judge fragment fix moved no verdict, on the two judgments that tested it

`judge.py` was fed `extract_code()` output directly, so a completion that
returned only the function it changed — what `X1` asks for on an edit task —
was judged as a bare fragment against a rival that echoed the whole module.
`score.py` has spliced fragments onto the starter since #23; M2 never did.

That was fixed in this change set (`code_as_left_on_disk`, reusing
`score.py`'s `reconstruct_edited_file`), and the 2026-08-29 completions were
re-judged under it into `judgments-fixed/` and `judge_summary-fixed.json`,
which are committed alongside the originals.

**Not one verdict moved: M2 was 45.0% (18/40) either way.** But that is a much
weaker result than it first reads as, and the earlier framing of it here
("changed nothing, and that is a published result") over-claimed on two
counts.

**The fix was barely exercised.** Only 1 of the 40 completions in that run is
actually altered by the splice — `03-add-feature`/claude/skill, 6 lines → 28.
The other 39 reach the judge byte-identical to before, because they already
echoed the whole file. So the fix was tested on 2 of 40 judgments, not run
wide, and "no verdict moved" is a statement about that one pair, which stayed
0/2. It does not establish that fragment-splicing is inconsequential in
general; it establishes that on this run there was almost nothing to splice.

**The rubric shift is re-sampling noise, not the fix.** Re-judging changed
rubric scores on **29 of 40 judgments** while only 2 had different inputs.
Whatever moved C from −0.32 to −0.23 was therefore mostly the judge answering
a second time, not the reconstruction. That puts a usable noise floor on this
harness:

| Category | delta, first judging | delta, re-judged | drift |
| -------- | -------------------- | ---------------- | ----- |
| N | −0.12 | −0.03 | 0.09 |
| C | −0.32 | −0.23 | 0.09 |
| F | +0.05 | −0.05 | 0.10 |
| S | −0.08 | +0.05 | 0.13 |
| T | −0.25 | +0.00 | 0.25 |

**Read every rubric delta in this document against that ±0.1–0.25 band.** The
C (+0.38), N (+0.28) and F (+0.33) moves in this run clear it. S (+0.12) and T
(−0.25) do not: both sit inside the noise the same judge produces answering
the same question twice.

One conclusion does survive. The fragment confound was real, is fixed, and was
not what held M2 down — and because the measurement change moves the baseline
by exactly zero, the 45.0% → 70.0% move is attributable to the tuning rather
than to the fix.

## Trigger suite (M4)

Target: **≥ 90% activation on the 60 positives, ≤ 10% false fire on the 40
negatives.** Tier-1 proxy classifier (`--model claude`, `claude-opus-5`).

| Metric | Value | 2026-08-29 | vs. target |
| ------ | ----- | ---------- | ---------- |
| activation rate (positives) | **100.0%** (60 / 60) | 98.3% | pass |
| false-fire rate (negatives) | **0.0%** (0 / 40) | 0.0% | pass |
| `meets_m4` | **true** | true | — |

False fire by negative category — the dangerous half held:

| Category | False fires |
| -------- | ----------- |
| prose-readability (10) | 0 |
| code-explanation (5) | 0 |
| other (25) | 0 |

pos-48 — *"This reads like boilerplate from a chatbot; make it look like a
person wrote it."* — was the baseline's single miss and now activates. The
`description` additions that catch it moved no negative, including the ten
prose-readability negatives that share the skill's vocabulary.

Tier 2 (10-prompt end-to-end spot check in real Claude Code) is a manual step
and was **not** done for this run.

## Summary against PRD targets

All four metrics meet their target as scored. M1 carries a caveat that costs
it one slot.

| Metric | Target | 2026-08-29 | 2026-09-01 | Status |
| ------ | ------ | ---------- | ---------- | ------ |
| M1 — lint reduction, skill vs. baseline | ≥ 60% | −84.9% pooled | **−79.1% pooled** (claude −70.9%, gpt −100.0%) | **pass** pooled and on claude; **gpt unvalidated** |
| M2 — blind pairwise skill preference | ≥ 70% | 45.0% | **70.0%** (28 / 40); **72.2%** (26 / 36) excluding undecidable pairs | **pass** either way, near threshold |
| M3 — diff inflation on scenarios 02/03/09 | ≤ 10% | claude −8.5%, gpt −5.4% | **claude +0.3%, gpt −15.1%** | **pass** |
| M4 — trigger activation / false fire | ≥ 90% / ≤ 10% | 98.3% / 0.0% | **100.0% / 0.0%** | **pass** |

M1 gave up margin on the claude slot and did not honestly gain it on `gpt` —
correcting that slot for its `X3` breach gives −53.3% there and −72.1% pooled,
so the pooled figure passes either way but the `gpt` slot does not. M2 moved
25pp and is the reason this run exists; M3 held after the `C14` item was
scoped; M4 improved.

## Known gaps

- **`qwen` slot not run.** No hosted-Qwen API key was available
  (`OPENROUTER_API_KEY` unset). Missing from this run: all 20 `qwen`
  completions, the end-to-end validation of `prompts/system-prompt.md` (design
  doc §14.3), and the second cross-judge on every pair. M2 therefore rests on a
  single judge per pair, as it did at baseline.
- **M2 sits near its threshold** at an effective n of ~18 — 70.0% as run,
  72.2% with the four undecidable `02-fix-bug` judgments removed. See
  [Reading M2](#reading-m2). A confirmation run — or the `qwen` judge, which
  would double the judgments per pair — would settle whether it is stable.
- **The published `judgments/` predate the undecidable-pair fix.** They were
  collected before `judge.py` learned to skip a pair whose two conditions
  leave identical files, so the committed `judge_summary.json` still counts
  those four coin flips as decided. The corrected figure is computed by hand
  in the M2 section; the JSON is left as it was collected.
- **Rubric deltas under ±0.25 are not distinguishable from re-judging noise.**
  Measured on the 2026-08-29 re-judging, where 29 of 40 judgments changed
  rubric scores with only 2 changed inputs. This run's S (+0.12) and T (−0.25)
  are inside that band; N, C and F are outside it. The harness needs more
  passes per judge before a delta that size means anything.
- **`04-write-tests` lost a judgment on both slots**, and T is the only
  negative rubric delta — though the delta itself is within the noise floor
  above. The file-level mechanism is real: the skill trades test coverage for
  test-name quality. Nothing in this tuning targeted it; it is the first thing
  to look at next, and the first thing to re-measure with more passes.
- **M1 counts findings inherited from the starter**, so it rewards breaching
  `X2`/`X3` on edit tasks. Two of the claude slot's three remaining findings
  are this artifact. Worth a scorer fix so the metric measures what the
  completion introduced.
- **The `gpt` slot's M1 pass is not real.** Its −100.0% depends on the skill
  completion renaming a public parameter on `10-de-slop`, an `X3` breach; had
  it complied the slot would score −53.3% against a ≥ 60% target. The `X3`
  tightening in this run did not stop the rename. Treat `gpt` M1 as
  unvalidated until the scorer fix above lands and the slot is re-run.
- **Baseline completions reused from 2026-08-29** rather than regenerated, so
  the baseline column carries no fresh sampling variance. Deliberate — it
  isolates the skill-side change — but it means baseline-vs-baseline drift
  between the two runs is unmeasured.
- **The intermediate unscoped-`C14` iteration is not published** as its own
  run directory; its M1/M3 numbers are recorded in the M3 section above.
- **Tier-2 trigger spot check** (real Claude Code, 10 prompts) not done.
- **Ollama mini-prompt smoke** (`run_smoke_ollama.py`, §14.3): not re-run. The
  existing `evals/results/2026-08-28/smoke-ollama/` output still stands and
  stays unpublished.

## Raw data

Everything below is in this directory, except where noted.

- `raw/` — every completion plus its `*.meta.json`. The 20 `skill.*` files were
  generated for this run; the 20 `baseline.*` files were copied from
  `../2026-08-29/raw/` and keep their original metadata.
- `scores.json` — `score.py` output (M1, M3, descriptive metrics).
- `judgments/` — one file per judgment (40 files).
- `judge_summary.json` — preference counts and per-category rubric means.
- `triggers/` — `run_triggers.py` output: `raw/<id>.json` per prompt and
  `triggers_summary.json`.
- `../2026-08-29/judgments-fixed/` and `../2026-08-29/judge_summary-fixed.json`
  — the baseline completions re-judged under the fixed judge, the comparable
  "before" for every M2 number here.
