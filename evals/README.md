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
  LOC, comment ratio, nesting depth, empty-word count, diff size).
- `judge.py` — the LLM-judge track (blind pairwise preference, per-category
  rubric).
- `run_smoke_ollama.py` — the unpublished local smoke test for
  `prompts/system-prompt-mini.md` (§14.3). Never fed into `score.py` or
  `RESULTS.md`.
- `results/<date>/` — one directory per run: `raw/` (every completion plus
  its generation metadata), `scores.json`, `judgments/`, and `RESULTS.md`.

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

## Publishing

Every metric goes in `RESULTS.md`, including ones that miss their target —
selective reporting defeats the point of publishing raw outputs at all
(§10.5). Commit `raw/`, `scores.json`, and `judgments/` alongside it.
