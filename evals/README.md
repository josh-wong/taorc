# Eval harness

This is the harness for MS6 (`v1-design-doc.md` §10): a scenario suite run
baseline vs. skill-enabled across a cross-model matrix, scored two ways, and
published with raw outputs. Read `v1-design-doc.md` §10 and
`v1-product-requirements-doc.md` R7 before changing anything here.

## Layout

Everything under this directory is generated or consumed by the three
scripts below; nothing here is a hand-maintained duplicate of what they
produce.

- `scenarios/` — the ten scenarios (§10.1), each a directory with `meta.json`,
  `task.md`, and any starter files the task edits.
- `evallib/` — shared code: model clients, scenario loading, and the
  baseline/skill system-prompt resolution.
- `run_bench.py` — calls every scenario × condition × model in the matrix and
  writes raw completions.
- `score.py` — the automated scoring track (`taorc-lint` findings per 100
  LOC, comment ratio and why-comment share, nesting depth, empty-word count,
  diff size).
- `judge.py` — the LLM-judge track (blind pairwise preference, plus a
  per-category N/C/F/S/T rubric aggregated into a skill-vs-baseline delta).
- `run_smoke_ollama.py` — the unpublished local smoke test for
  `prompts/system-prompt-mini.md` (§14.3). Never fed into `score.py` or
  `RESULTS.md`.
- `results/<date>/` — one directory per run: `raw/` (every completion plus
  its generation metadata), `scores.json`, `judgments/`, `judge_summary.json`,
  and `RESULTS.md`.

## Running a full matrix

Each model slot needs its own API key (see `evallib/models.py`'s
`MODEL_MATRIX`):

```bash
export ANTHROPIC_API_KEY=...
export OPENAI_API_KEY=...
export OPENROUTER_API_KEY=...   # or whichever host serves Qwen3.6-27B

python evals/run_bench.py --out evals/results/2026-08-28
python evals/score.py --run evals/results/2026-08-28
python evals/judge.py --run evals/results/2026-08-28
```

A model with no key set is skipped with a warning rather than failing the
run, so you can gather keys incrementally. Use `--dry-run` on `run_bench.py`
to see what would be sent without calling anything or spending money.

Both `run_bench.py` and `judge.py` resume: a completion or judgment already
on disk is kept, not re-billed, so an interrupted run finishes by being
re-invoked with the same `--out`/`--run`. Pass `--force` to regenerate. A
generation that fails leaves a `<condition>.error.json`, which `score.py`
lists under `generation_errors` so a missing cell reads as a known gap
rather than a zero. Transient provider errors (timeouts, 429/5xx) are
retried with backoff before a cell is given up on.

Sampler settings are fixed in `evallib/models.py`'s `DEFAULT_SAMPLER` and
written into every completion's `.meta.json` — copy them into `RESULTS.md`
verbatim (§10.3's reproducibility requirement is about sampler settings,
not model choice).

## What "skill-enabled" means here

A raw completion call has no file access and no tool runtime, so it can't
run the operating loop's "read local context" or "run taorc-lint" steps.
What this harness actually measures is narrower: does injecting the
artifact each model's real distribution channel would use (full `SKILL.md`
for Claude, the `AGENTS.md` managed block for GPT, `system-prompt.md` for
the open-weights slot — see `evallib/skill_artifacts.py`) change what gets
written, in the direction the catalog intends. See that module's docstring
for the reasoning and the limitation.

## Trigger suite (M4)

This is a separate, much cheaper harness from the scenario run above. It
measures activation — does the skill fire on the tasks it claims and stay
quiet on the ones it doesn't (`v1-design-doc.md` §10.4, PRD R2.3) — not the
quality of what gets written.

`triggers.json` holds 100 prompts: 60 the readable-code skill should
activate on and 40 it must not. The 40 negatives are split the way §10.4
fixes them — 10 prose-readability (the dangerous half that shares the
skill's whole vocabulary), 5 code-explanation (reading is not writing), 25
other. The prompts are written to what the skill actually covers, not to
the current `description`; the point of the run is to measure the gap so
the `description` can be tuned against it.

`run_triggers.py` is the tier-1 proxy classifier: for each prompt, one
classification call given only the skill's `name` and `description`
(resolved live from `skills/readable-code/SKILL.md` frontmatter, so it
tracks what ships) — no agent run, no tools. A full pass costs cents and
finishes in under a minute.

```bash
export ANTHROPIC_API_KEY=...

python evals/run_triggers.py --out evals/results/2026-08-29 --dry-run  # no key needed
python evals/run_triggers.py --out evals/results/2026-08-29 --limit 5  # cheap smoke test
python evals/run_triggers.py --out evals/results/2026-08-29            # full pass
```

Results land under `<out>/triggers/`, following `run_bench.py`'s layout:
one `raw/<id>.json` per classified prompt (verdict plus the raw response),
`raw/<id>.error.json` for a call that failed, and `triggers_summary.json`
with the headline numbers. Like `run_bench.py`, it resumes — a prompt
already on disk is kept, not re-billed — and takes `--force` to
re-classify. A kept cell must match the current skill `description` and
`--model`; when either changed since it was saved the cell is re-classified
automatically, so a rerun after a `description` edit needs no `--force`.
`--model` picks the classifier slot (default `claude`, the skill's primary
harness).

`triggers_summary.json` reports the activation rate on the 60 positives and
the false-fire rate on the 40 negatives against M4 (≥90% activation, ≤10%
false fire), plus `positives_not_activated` and `negatives_activated` so a
miscalibrated `description` points straight at the prompts that moved.
`meets_m4` is `true` only when every prompt classified — a run with a failed
cell or a `--limit` reports `false` regardless of the partial rates and
exits non-zero. Failed cells are listed in `failed_prompt_ids`; rerun with
the same `--out` to retry just those. A `--limit` smoke test writes
`triggers_summary.partial.json` instead, so it never overwrites a full
pass's `triggers_summary.json` in the same `--out` directory.
`evallib/triggers.py` refuses to load a suite that has drifted off the
60/40/10-5-25 shape — `scripts/validate.py` runs that same check in CI.

Tier 2 (a 10-prompt end-to-end spot check in real Claude Code, confirming
the proxy tracks reality) is a manual step recorded alongside the run it
validates, not automated here.

This run is not wired into any per-PR workflow: it needs an API key, and a
docs-only commit must not spend one or block on a provider outage (§10.4).
Run it on demand and whenever `SKILL.md` frontmatter or `catalog/rules.yaml`
changes.

## Publishing

Every metric goes in `RESULTS.md`, including ones that miss their target —
selective reporting defeats the point of publishing raw outputs at all
(§10.5). Commit `raw/`, `scores.json`, and `judgments/` alongside it.
