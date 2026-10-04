# Changelog

All notable changes to taorc are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [semantic versioning](https://semver.org/).

`VERSION` is the single source for every version field. `scripts/build.py` copies it into the plugin and extension manifests, into each managed block's `<!-- taorc:begin vX.Y.Z -->` marker, and into each installer's own version line, and `scripts/validate.py` fails CI if any of them disagree. The skill's own `metadata.version` in `SKILL.md` is hand-written, so it is updated by hand and checked by the same gate.

For this project, a rule ID is part of the public interface. Deprecating a rule is a minor change, because the ID stays valid and gains a `superseded_by` pointer. Removing or renumbering an ID would be a major change, and the catalog policy is never to do either.

## [Unreleased]

These changes will ship as 1.0.0, the first public release. The version heading and date are added on the day it is tagged.

### Added

- **Rule catalog:** `catalog/rules.yaml`, 85 rules across ten categories (`P`, `N`, `A`, `C`, `F`, `E`, `V`, `S`, `T`, `X`), each with an original instruction, a severity, and the book chapter it draws on, validated against `catalog/schema.json`.
- **Skill:** `skills/readable-code/`, a hand-written `SKILL.md` (4,234 tokens, 323 lines) with `write`, `review`, and `refactor` modes, an operating loop, and a ten-item self-check, plus nine reference files loaded on demand. `references/ai-code-tells.md` maps recognizable habits of LLM-written code to the rule that governs each.
- **Linter:** `taorc-lint`, a stdlib-only Python script bundled inside the skill, which checks nine high-precision rules (`C1`, `C4`, `N1`, `N3`, `N11`, `S7`, `T3`, `X7`, `X8`) in Python and TypeScript/JavaScript through ast-grep, with inline suppressions and JSON output. Ready-to-merge ruff and ESLint snippets for the structural checks it deliberately leaves out ship under `lint/configs/`.
- **Adapters:** generated managed blocks for `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, Cursor, GitHub Copilot, Cline, and Windsurf, plus Claude Code plugin, Codex plugin, and Gemini extension manifests, all built from `templates/agent-block.md` and `VERSION` by `scripts/build.py`.
- **Installers:** `scripts/install.sh` and `scripts/install.ps1`, with `--project`, `--global`, `--agents`, `--detect`, and `--uninstall`. They only ever touch text between taorc's own markers. By default each installer downloads the release it shipped with, and `TAORC_REF` selects any other branch, tag, or commit.
- **Fallback prompts:** `prompts/system-prompt.md` (506 tokens) and `prompts/system-prompt-mini.md` (144 tokens), for any LLM with no skill runtime.
- **Claude Code extras:** the `/taorc-review` command (`commands/taorc-review.md`), which reviews the current diff, a path, or a pull request for readability, and the "Readable Code Review" output style (`output-styles/readable-code-review.md`), which formats review findings as rule citations with concrete fixes.
- **Examples:** `examples/before-after.md`, twenty original before/after pairs in nine languages, four of which show when *not* to apply a rule.
- **Evals:** a ten-scenario benchmark harness (`evals/`), a 100-prompt trigger suite, automated scoring through `taorc-lint`, and a blind pairwise LLM judge. Every run is published with its raw completions under `evals/results/`.
- **Docs:** `README.md`, `CONTRIBUTING.md`, this changelog, and `docs/harness-verification.md`.

### Success metrics at release

These are the PRD §7 metrics. M1 to M4 come from the most recent eval run, [`evals/results/2026-09-03`](https://github.com/josh-wong/taorc/blob/v1.0.0/evals/results/2026-09-03/RESULTS.md). M4 was carried forward from [`2026-09-01`](https://github.com/josh-wong/taorc/blob/v1.0.0/evals/results/2026-09-01/RESULTS.md) because the skill's `description` did not change between the two runs. Read the "Reading this run" and "Known gaps" sections of that `RESULTS.md` before quoting any of these numbers on their own.

| Metric                             | Target                       | Result                                                                                                        | Status                                                  |
| ---------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| M1 — lint findings per 100 LOC     | ≥ 60% reduction              | −75.5% pooled; Claude −78.2%; GPT −4.6% on a baseline of one finding                                          | Pass pooled and on Claude; not measurable on GPT        |
| M2 — blind pairwise preference     | ≥ 70%                        | 68.4% as run; 72.2% excluding one pair the scorer could not parse                                             | Miss as run, pass corrected                             |
| M3 — diff inflation on bugfixes    | ≤ 10%                        | Claude +232.8% as scored, −11.6% corrected for the same parse failure; GPT +3.0%                              | Miss as scored, pass corrected                          |
| M4 — trigger activation            | ≥ 90% fire / ≤ 10% false     | 100.0% on 60 positives / 0.0% on 40 negatives                                                                 | Pass                                                    |
| M5 — linter false positives        | ≤ 5%                         | 0 findings across the 18 negative fixtures                                                                    | Pass                                                    |
| M6 — `SKILL.md` size               | ≤ 5,000 tokens               | 4,234 tokens                                                                                                  | Pass                                                    |
| M7 — harness coverage              | ≥ 10 placement / ≥ 4 by hand | 10 targets with automated placement checks; 4 verified by hand                                                | Pass                                                    |
| M8 — adoption                      | Directional only             | Not measurable at release                                                                                     | Measured at 90 days                                     |

### Known limitations

- The open-weights eval slot has not run yet, so `prompts/system-prompt.md` has not been validated end to end and every pairwise judgment rests on a single judge.
- `evals/score.py` and `evals/judge.py` cannot parse a completion that comes back as a unified diff. One completion in the latest run did, and it alone accounts for the M2 and M3 misses as scored.
- The test-writing (`T`) rubric score rests on four judgments from a single scenario.
- `taorc-lint` covers Python and TypeScript/JavaScript only.

[Unreleased]: https://github.com/josh-wong/taorc/commits/main
