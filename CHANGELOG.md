# Changelog

All notable changes to taorc are recorded here. Each release entry has the same sections as its GitHub release page (Features, Improvements, Bug fixes, Documentation, Known limitations, Downloads, plus Success metrics when the release has eval results), because the release workflow publishes the entry as the release notes. The project uses [semantic versioning](https://semver.org/).

`VERSION` is the single source for every version field. `scripts/build.py` copies it into the plugin and extension manifests, into each managed block's `<!-- taorc:begin vX.Y.Z -->` marker, and into each installer's own version line, and `scripts/validate.py` fails CI if any of them disagree. The skill's own `metadata.version` in `SKILL.md` is hand-written, so it is updated by hand and checked by the same gate.

For this project, a rule ID is part of the public interface. Deprecating a rule is a minor change, because the ID stays valid and gains a `superseded_by` pointer. Removing or renumbering an ID would be a major change, and the catalog policy is never to do either.

## [Unreleased]

## [1.0.0] - 2026-11-23

This is the first release of **taorc**, an agent skill that makes AI coding agents write, comment, and review code so the next reader understands it quickly. It builds on the ideas in *The Art of Readable Code* (Boswell & Foucher, O'Reilly 2011) in original wording, and works in Claude Code, GitHub Copilot, Cursor, Codex, Gemini CLI, Cline, Windsurf, and any LLM you can give a system prompt. It is unofficial and contains no text from the book.

### ✨ Features

This release includes the following features:

- **Rule catalog.** `catalog/rules.yaml` holds 85 rules across ten categories (`P`, `N`, `A`, `C`, `F`, `E`, `V`, `S`, `T`, `X`), each with an original instruction, a severity, and the book chapter it draws on, validated against `catalog/schema.json`.
- **Skill.** `skills/readable-code/` is a hand-written `SKILL.md` (4,234 tokens, 323 lines) with `write`, `review`, and `refactor` modes, an operating loop, and a ten-item self-check, plus nine reference files loaded on demand. `references/ai-code-tells.md` maps recognizable habits of LLM-written code to the rule that governs each.
- **Linter.** `taorc-lint` is a stdlib-only Python script bundled inside the skill. It checks nine high-precision rules (`C1`, `C4`, `N1`, `N3`, `N11`, `S7`, `T3`, `X7`, `X8`) in Python and TypeScript/JavaScript through ast-grep, with inline suppressions and JSON output.
  - Ready-to-merge ruff and ESLint snippets for the structural checks it leaves out are in `lint/configs/`.
- **Adapters.** Generated managed blocks for `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, Cursor, GitHub Copilot, Cline, and Windsurf, plus Claude Code plugin, Codex plugin, and Gemini extension manifests, all built from `templates/agent-block.md` and `VERSION` by `scripts/build.py`.
- **Installers.** `scripts/install.sh` and `scripts/install.ps1` support `--project`, `--global`, `--agents`, `--detect`, and `--uninstall`. They only touch text between taorc's own markers. Each installer downloads the release it shipped with by default, and `TAORC_REF` selects any other branch, tag, or commit.
- **Fallback prompts.** `prompts/system-prompt.md` (506 tokens) and `prompts/system-prompt-mini.md` (144 tokens), for any LLM with no skill runtime.
- **Claude Code extras.** The `/taorc-review` command reviews the current diff, a path, or a pull request for readability. The "Readable Code Review" output style formats findings as rule citations with concrete fixes.
- **Examples.** `examples/before-after.md` has twenty original before/after pairs in nine languages, four of which show when *not* to apply a rule.
- **Evals.** A ten-scenario benchmark harness, a 100-prompt trigger suite, automated scoring through `taorc-lint`, and a blind pairwise LLM judge. Every run is published with its raw completions under `evals/results/`.

### 📈 Improvements

*Nothing to list – This is the initial release.*

### 🐛 Bug fixes

*Nothing to list – This is the initial release.*

### 📚 Documentation

- A README, a `CONTRIBUTING.md` with the rule bar and stable-ID policy, a changelog, and `docs/harness-verification.md` recording the manual per-harness smoke tests.

### 📊 Success metrics at release

These are the PRD §7 metrics from the most recent eval run, [`evals/results/2026-09-03`](https://github.com/josh-wong/taorc/blob/v1.0.0/evals/results/2026-09-03/RESULTS.md). Read its "Reading this run" and "Known gaps" sections before quoting any number on its own.

| Metric                             | Target                       | Result                                                                  | Status                                           |
| ---------------------------------- | ---------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------ |
| M1 — lint findings per 100 LOC     | ≥ 60% reduction              | −75.5% pooled; Claude −78.2%; GPT −4.6% on a baseline of one finding    | Pass pooled and on Claude; not measurable on GPT |
| M2 — blind pairwise preference     | ≥ 70%                        | 68.4% as run; 72.2% excluding one pair the scorer could not parse       | Miss as run, pass corrected                      |
| M3 — diff inflation on bugfixes    | ≤ 10%                        | Claude +232.8% as scored, −11.6% corrected; GPT +3.0%                   | Miss as scored, pass corrected                   |
| M4 — trigger activation            | ≥ 90% fire / ≤ 10% false     | 100.0% on 60 positives / 0.0% on 40 negatives                           | Pass (carried forward, not re-measured)          |
| M5 — linter false positives        | ≤ 5%                         | 0 findings across the 18 negative fixtures                              | Pass                                             |
| M6 — `SKILL.md` size               | ≤ 5,000 tokens               | 4,234 tokens                                                            | Pass                                             |
| M7 — harness coverage              | ≥ 10 placement / ≥ 4 by hand | 10 targets with automated placement checks; 4 verified by hand          | Pass                                             |
| M8 — adoption                      | Directional only             | Not measurable at release                                               | Measured at 90 days                              |

M4 was carried forward from the 2026-09-01 run and was not re-measured after the book-title sentence was dropped from the skill's `description`. That sentence was attribution only and none of the suite's prompts name the book, but the suite was not rerun against the final description.

### ⚠️ Known limitations

- The open-weights eval slot has not run yet, so `prompts/system-prompt.md` has not been validated end to end and every pairwise judgment rests on a single judge.
- `evals/score.py` and `evals/judge.py` cannot parse a completion that comes back as a unified diff. One completion in the latest run did, and it alone accounts for the M2 and M3 misses as scored.
- The test-writing (`T`) rubric score rests on four judgments from a single scenario.
- `taorc-lint` covers Python and TypeScript/JavaScript only.

### 📦 Downloads

| Platform                  | Downloadable                                                                                                                      |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **macOS, Linux, Windows** | [taorc-skill-v1.0.0.zip](https://github.com/josh-wong/taorc/releases/download/v1.0.0/taorc-skill-v1.0.0.zip)                      |

To install without the zip, run `npx skills add josh-wong/taorc`.

[Unreleased]: https://github.com/josh-wong/taorc/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/josh-wong/taorc/releases/tag/v1.0.0
