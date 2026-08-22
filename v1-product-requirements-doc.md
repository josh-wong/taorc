# taorc – Product Requirements Document (v1)

**Project**: `taorc` – *The Art of Readable Code* as an AI agent skill
**Status**: Approved
**Author**: josh-wong
**Date**: 2026-08-21
**Related**: `v1-design-doc.md`

## 1. Summary

`taorc` is a portable **agent skill** that makes AI coding agents write, comment, and review code according to the principles of *The Art of Readable Code* (Boswell & Foucher, O'Reilly, 2011).

It ships as an [Agent Skills](https://agentskills.io/specification) package (`SKILL.md` + `references/`), plus per-agent adapters so it works in Claude Code, GitHub Copilot, Cursor, Codex, Gemini CLI, Windsurf, Cline, opencode, and any tool that reads `AGENTS.md`—and as a plain system prompt for models with no skill runtime at all (Llama, Qwen, local models, chat UIs).

The one-line pitch: **agents write code that runs; `taorc` makes them write code the next human can read in less time.**

## 2. Problem

### 2.1 The general problem

The book's central claim—its *Fundamental Theorem of Readability*—is that code should be written to minimize the time it takes someone else to understand it. Agents do not optimize for this. They optimize for producing something that satisfies the request and passes review at a glance.

### 2.2 The specific problem: LLM code has recognizable readability tells

This is the strongest reason to build `taorc`, and it is the reason to base it on *this* book rather than a general "clean code" corpus. The failure modes of LLM-authored code map almost one-to-one onto the chapters of *The Art of Readable Code*:

| LLM tell | Book chapter it violates |
|---|---|
| `// Loop through the users` above `for user in users:` | Ch. 5 – Knowing What to Comment |
| `// Step 1:` / `// Step 2:` narration of its own plan | Ch. 5, 6 |
| Docstrings that restate the signature and add nothing | Ch. 6 – Precise and Compact Comments |
| `data`, `result`, `output`, `temp`, `handler`, `process()`, `helper()` | Ch. 2 – Packing Information into Names |
| `delay`, `size`, `limit` with no unit or boundary semantics | Ch. 2, 3 |
| Deeply nested `if`/`else` where a guard clause would do | Ch. 7 – Control Flow |
| Giant boolean conditions assembled inline | Ch. 8 – Breaking Down Giant Expressions |
| Intermediate variables that exist only to be returned | Ch. 9 – Variables and Readability |
| Helper functions abstracted for a single call site | Ch. 10, 13 |
| Reimplementing what the standard library already does | Ch. 13 – Writing Less Code |
| Banner comments (`# ===== HELPERS =====`), emoji in comments | Ch. 4, 5 |
| Tests with heavy setup boilerplate and names like `test_1` | Ch. 14 – Testing and Readability |

Existing tooling does not catch these. Formatters (Prettier, Black, gofmt) normalize whitespace. Linters (ESLint, Ruff, Clippy) catch correctness and a narrow band of style. Neither can tell you that a comment adds no information, that a name is technically valid but semantically empty, or that a function is doing three things.

`vale-ai-tells` proved the demand for this category **on prose**. `taorc` is the equivalent **for code**—with a published book as its rule source rather than an ad-hoc list.

### 2.3 Why an agent skill rather than a linter

Readability judgments are semantic. "Does this comment tell me something the code does not?" cannot be answered by a regex. A subset of the rules *is* mechanically checkable (see R6), but the core of the product must be instructions an agent reasons with, applied at authoring time—before the bad code is written—not a report generated afterward.

## 3. Prior art

### 3.1 The three repos cited in the brief

| Repo | What it is | What `taorc` takes from it | Where `taorc` differs |
|---|---|---|---|
| [`juliusbrussee/caveman`](https://github.com/juliusbrussee/caveman) | Token-compression skill + proxy; `/caveman [lite\|full\|ultra]` modes; 8 agent integrations via JSON profiles | Mode switching; broad agent matrix; slash-command surface (`/taorc-review`) | Caveman optimizes *token cost*. `taorc` optimizes *human comprehension time*—often by spending more tokens, not fewer. Opposite objective. No proxy, no runtime, no BSL component. |
| [`AminBlg/SimpleEnglish`](https://github.com/AminBlg/SimpleEnglish) | ASD-STE100 Simplified Technical English as a skill; 53 numbered rules; measured 74.6% violation reduction | **The closest model for `taorc`.** Numbered-rule catalog, paraphrase-don't-reproduce approach to a copyrighted standard, `prompts/system-prompt.md` fallback, an evals harness with a lint scorer, pragmatic/strict modes | SimpleEnglish governs *prose*. `taorc` governs *code and code comments*—which means language-specific idioms, a diff-scoped operating model, and a much harder deterministic-scoring problem. |
| [`tbhb/vale-ai-tells`](https://github.com/tbhb/vale-ai-tells) | 111 Vale rules detecting AI-generated prose patterns; ships as versioned Vale packages; documents agent fix-loop workflows | The **"AI tells" framing** (see R5.3, `references/ai-code-tells.md`), stable rule IDs, structured findings the agent can loop on, pre-commit integration | Vale is a prose linter and cannot parse code. `taorc`'s equivalent layer needs AST tooling (ast-grep/Semgrep), and it is a *supporting* component here, not the product. |

### 3.2 The closest competitor (not in the brief)

**[`btseee/clean-code-skills`](https://github.com/btseee/clean-code-skills)** – this is the repo most similar to what you described, and you should look at it before we finalize the design.

- Content source: Robert C. Martin's *Clean Code*.
- Structure: `skills/clean-code/SKILL.md` + `references/{chapter-map,review-checklist,framework-map,project-refactor}.md`.
- Distribution: `curl | bash` and PowerShell installers, `.claude-plugin/`, `.codex-plugin/`, `gemini-extension.json`, `.cursor/rules/*.mdc`, `.github/skills/`, `.github/instructions/*.instructions.md`, `CLAUDE.md` / `AGENTS.md` / `GEMINI.md`, managed `<!-- clean-code-skills:begin -->` blocks with self-updating version detection, `scripts/validate.{sh,ps1}` + CI.
- Explicitly notes that copyrighted reference material is gitignored and the repo contains only original synthesis.

**Recommendation: treat its packaging as a reference architecture and its content as the thing to differentiate from.** The distribution problem is solved there and there is no reason to re-solve it. The content is genuinely different:

| | `clean-code-skills` | `taorc` |
|---|---|---|
| Source | *Clean Code* (Martin, 2008) | *The Art of Readable Code* (Boswell & Foucher, 2011) |
| Character | Design discipline: SRP, functions, classes, boundaries, error handling, TDD | Surface-level, measurable micro-decisions: naming, comments, control flow, expressions |
| Unit of advice | "This module has mixed responsibilities" | "This name is ambiguous"; "this comment restates the code" |
| Scope of change | Often structural – a refactor | Usually local – a rename, a deleted comment, an extracted variable |
| Contentiousness | High (small-functions dogma, comment-avoidance dogma, OO bias) | Low; the book is deliberately undogmatic and language-agnostic |
| Diff risk with agents | Encourages restructuring, so needs strong guardrails | Naturally diff-local, so it composes better with day-to-day agent work |

They are complements, not substitutes. `taorc` should say so in its README—that is a credibility signal, not a weakness.

### 3.3 Also surveyed

`ertugrul-dmr/clean-code-skills`, `aakashH242/clean-dry-code-skills`, LobeHub's `clean-code` skill. All are single or multi `SKILL.md` bundles restating general clean-code advice. None are grounded in a named book with a citable rule catalog, none ship a deterministic checker, none ship evals. **No existing skill is based on *The Art of Readable Code*.** The niche is open.

## 4. Goals and non-goals

### 4.1 Goals

- **G1** – Agents write more readable code *by default*, without being asked, on ordinary feature and bugfix work.
- **G2** – Agents stop producing the specific readability tells listed in §2.2.
- **G3** – Agents can *review* a diff and report readability findings with stable, citable rule IDs.
- **G4** – The skill runs unmodified across ≥10 agent harnesses, and degrades gracefully to a pasteable prompt for any LLM.
- **G5** – The improvement is **measured**, not asserted. A published before/after benchmark, as SimpleEnglish did.
- **G6** – The skill respects existing project conventions and never widens a diff to satisfy itself.
- **G7** – Zero copyright exposure: original prose, original code examples, no reproduction of the book's text or examples.

### 4.2 Non-goals for v1

- **NG1** – Not a formatter. `taorc` defers to Prettier/Black/gofmt/rustfmt on whitespace, line breaks, and casing.
- **NG2** – Not a correctness, security, or performance reviewer. Those are `/code-review` and `security-review` territory.
- **NG3** – Not an architecture or design-pattern skill. That is `clean-code-skills`'s job.
- **NG4** – No proxy, daemon, runtime, or hosted service. Files on disk only.
- **NG5** – Not a whole-codebase auto-refactor tool in v1 (see §8, v2).
- **NG6** – No paid tier, no telemetry, no phone-home.

## 5. Users and use cases

**Primary user**: a developer using an AI coding agent daily who is tired of deleting `// Increment the counter` from every generated file.

**Secondary user**: a tech lead standardizing agent output across a team, installing `taorc` at project scope and committing it.

**Tertiary user**: a reviewer running `taorc` in review mode against an agent-authored PR.

### Use cases

| ID | Use case | Trigger |
|---|---|---|
| UC1 | Agent writes new code with readable names, comments, and control flow | Skill auto-activates on any code-writing task |
| UC2 | Agent reviews a diff and reports readability findings with rule IDs | `/taorc-review`, or "review this for readability" |
| UC3 | Agent cleans up code it just wrote, before presenting it | Self-check step at the end of the operating loop |
| UC4 | Agent rewrites a specific file or function for readability | "make this readable", "clean up the comments in X" |
| UC5 | Developer pastes the condensed prompt into a chat UI or local model | No skill runtime available |
| UC6 | CI/pre-commit flags mechanically-detectable violations | `taorc-lint` on changed files |
| UC7 | Agent writes readable tests | Test-authoring tasks |

## 6. Requirements

### R1 – Rule catalog

The heart of the product. A numbered, stable, citable catalog derived from the book's structure, expressed entirely in original words with original examples.

**R1.1 – Categories and ID scheme.** Letter-prefixed, stable across versions, never renumbered (deprecate, don't reuse):

| Prefix | Category | Book chapters | Est. rules |
|---|---|---|---|
| `P` | Principles | 1 | 3 |
| `N` | Names – packing information in, avoiding misconstrual | 2, 3 | 12 |
| `A` | Aesthetics and layout | 4 | 5 |
| `C` | Comments – what to comment, and how | 5, 6 | 14 |
| `F` | Control flow | 7 | 7 |
| `E` | Expressions | 8 | 5 |
| `V` | Variables and scope | 9 | 5 |
| `S` | Structure – subproblems, one task at a time, less code | 10–13 | 8 |
| `T` | Tests and readability | 14 | 6 |
| `X` | **Agent guardrails** (original content, not from the book) | – | 8 |

Target: **65–75 rules**. Each rule is one line of instruction plus, where it earns its place, a compact before/after in a common language.

**R1.2 – The `X` category is original and load-bearing.** These are the rules the book could not have written because they are about *how an agent applies the other rules*:

- Do not widen the diff to satisfy a readability rule; mention what you did not change.
- Match the surrounding file's existing vocabulary and conventions over the catalog's preference.
- Never rename a public/exported symbol without being asked.
- Keep readability changes and behavior changes in separate steps.
- Defer all whitespace, line-length, and casing decisions to the project's formatter and linter config.
- When reviewing, cite rule IDs from this catalog; never invent one.
- Do not narrate your own plan in comments.
- Do not add file-header banners, section dividers, or emoji to code.

**R1.3 – Precedence.** The catalog must state its own tiebreakers explicitly, because these rules conflict in practice:

1. Correctness beats readability.
2. Project convention beats catalog preference.
3. Reader comprehension time beats brevity, cleverness, and rule-count compliance.
4. The formatter wins every whitespace argument.
5. When two rules conflict, prefer the one that reduces time-to-understand for a reader unfamiliar with the code.

**R1.4 – Chapter map.** `references/chapter-map.md` maps every rule ID to its originating chapter. This is the attribution mechanism and the "go read the real thing" pointer. It must not summarize chapters in enough detail to substitute for the book.

### R2 – Skill package

**R2.1** – Spec-compliant per [agentskills.io](https://agentskills.io/specification): directory name matches `name`; `name` and `description` required; `license`, `metadata.version` set.

**R2.2** – `SKILL.md` ≤ 500 lines and ≤ 5,000 tokens. Everything else goes in `references/`, each with an explicit *when to load this* instruction—"read `references/comments.md` before writing or editing any comment", not "see references for details."

**R2.3** – The `description` must trigger reliably. It has to fire on both explicit asks ("make this readable", "review the comments") and implicit ones (any code-writing task). Getting this right is its own tuning problem, measured on a **100-prompt trigger suite**: 60 positives spanning explicit asks, implicit code writing, review, test authoring, refactor, and de-slop requests; 40 negatives spanning prose editing, git operations, dependency upgrades, config edits, debugging, and code *explanation*. See §7 metric M4 and design doc §10.4.

Under-firing and over-firing are not symmetric costs. A skill that fails to fire on code writing does nothing at all; a skill that fires on a config edit spends about 4,500 tokens. The targets are set accordingly (≥90% / ≤10%).

**R2.4** – An **operating loop** the agent follows, not a wall of rules. Draft shape:

1. Read the local context—naming vocabulary, comment density, formatter config, test style.
2. Write the code.
3. Self-check against the catalog's checklist before presenting.
4. Report what you deliberately left alone.

**R2.5** – **Modes**, selectable and inferable from the request:

| Mode | Behavior | Default trigger |
|---|---|---|
| `write` | Apply the catalog while generating; no unrelated cleanup | Any code-writing task (default) |
| `review` | Report findings with rule IDs, no edits | "review", `/taorc-review` |
| `refactor` | Apply behavior-preserving readability fixes to a named target | "clean up X", "make X readable" |

**R2.6** – Language coverage. The catalog is language-agnostic; `references/language-map.md` supplies idiom adjustments for the top tier: Python, TypeScript/JavaScript, Go, Rust, Java, C#. Everything else falls back to the general rules.

### R3 – Multi-agent distribution

**R3.1** – Three canonical sources, each owning one thing:

| Source | Owns |
|---|---|
| `catalog/rules.yaml` | Every rule ID, and the metadata for each |
| `skills/readable-code/` | The skill prose—hand-written, generates nothing |
| `templates/agent-block.md` | The managed block every non-skill adapter embeds |

Every adapter, manifest, and condensed prompt is generated from those. **No hand-maintained duplicates**—this is the single biggest maintenance trap and drift is guaranteed without generation + CI validation.

**R3.2** – Required targets for v1:

| Target | Mechanism |
|---|---|
| Agent Skills runtimes (~30 agents) | `skills/readable-code/` + `npx skills add josh-wong/taorc` |
| Claude Code | `.claude-plugin/{plugin,marketplace}.json`; `.claude/skills/` |
| claude.ai / Claude Desktop | Release `.zip` of the skill directory for upload |
| GitHub Copilot (VS Code + cloud agent) | `.github/skills/readable-code/`, `.github/copilot-instructions.md`, `.github/instructions/readable-code.instructions.md` |
| Cursor | `.cursor/rules/readable-code.mdc` |
| Codex, Jules, Zed, Aider, opencode, Windsurf, Devin | `AGENTS.md` managed block |
| Gemini CLI | `gemini-extension.json` |
| Cline | `.clinerules/` |
| Any LLM (Llama, Qwen, local, chat UI) | `prompts/system-prompt.md` |

**R3.3** – Managed block convention: `<!-- taorc:begin v1.2.3 -->` … `<!-- taorc:end -->`, so installs are idempotent, updates are surgical, and uninstall is clean. Never clobber a user's existing `AGENTS.md` or `CLAUDE.md`.

**R3.4** – Install paths: `npx skills add josh-wong/taorc`, `claude plugin marketplace add josh-wong/taorc`, and `curl | bash` / PowerShell installers with `--project` and `--global` scopes.

**R3.5** – Claude Code note: as of August 2026 Claude Code reads `CLAUDE.md` rather than `AGENTS.md`, so ship both. Verify at implementation time.

### R4 – Portable prompt fallback

**R4.1** – `prompts/system-prompt.md`: a compressed version, target ≤ 800 tokens, that survives being pasted into a system-prompt box with no file access and no skill runtime. This is what makes the "works with Llama and Qwen" claim true.

**R4.2** – `prompts/system-prompt-mini.md`: a ~150-token version for tight context budgets. Required—the design depends on it for the open-weights smoke test and enforces its budget in CI.

**R4.3** – Both are generated from the catalog and validated in CI against a token ceiling.

### R5 – Examples

**R5.1** – `examples/before-after.md`: 15–20 pairs across languages, each labeled with the rule IDs it demonstrates. Every example original, written for this repo.

**R5.2** – Include at least three examples of **when not to apply a rule**—a `tmp` that is genuinely fine, a comment that looks redundant but is not, a one-line function that should stay inline. Over-application is the main failure mode of a skill like this, and showing restraint teaches restraint.

**R5.3** – `references/ai-code-tells.md`: the catalog's LLM-facing index. One row per recognizable AI code tell (§2.2), each mapped to the rule ID that governs it and a one-line fix. This is what a "de-slop this file" request resolves against, and it is entirely original work—no equivalent exists in the book or in any competing skill. It is the artifact most responsible for the project not reading as a book summary (§9).

### R6 – `taorc-lint` (deterministic checker)

**R6.1** – A checker covering the mechanically-detectable subset. Per the Q1 decision, v1 ships **10 high-precision rules** of the 73: comment-echoes-next-line, `// Step N:` narration, banner comments, emoji in comments, placeholder comments, commented-out code, empty-word identifiers, unit-free time/size names, negated boolean names, and test names without a scenario.

Structural checks that mainstream linters already do well—nesting depth, function length, boolean-expression complexity—are **out of scope by design**. `taorc` ships tuned `ruff`/`eslint` config for those instead of reimplementing them.

**R6.2** – Output must be **agent-consumable**: rule ID, file:line, matched text, and a concrete fix instruction—the `vale-ai-tells` pattern. The agent loops until clean.

**R6.3** – Language coverage in v1: Python and TypeScript/JavaScript. Tool choice (ast-grep vs. Semgrep vs. custom) is a design-doc decision; ast-grep is the leading candidate for its YAML rules, single binary, and tree-sitter multi-language support.

**R6.4** – Must ship with a false-positive fixture suite. A noisy linter here is worse than none—it trains users to ignore the whole product.

**R6.5** – **Scope**: resolved by Q1. The 10-rule, two-language v1 above is deliberately small so this component cannot sink the release; expansion is v1.x.

### R7 – Evals

**R7.1** – A scenario suite of ~10 code-writing tasks (new function, bugfix, refactor, test authoring, script, API handler) × baseline vs. skill-enabled.

**R7.2** – Scoring, dual-track:

- **Automated**: `taorc-lint` violations per 100 LOC; comment-to-code ratio; mean nesting depth; empty-word identifier count.
- **LLM judge**: blind pairwise preference on "which would take less time to understand", plus a rubric score per category.

**R7.3** – Cross-model: at minimum Claude, GPT, and one open-weights model (Qwen or Llama), to substantiate the cross-agent claim.

**R7.4** – Results published in `evals/results/` with raw outputs, as SimpleEnglish does. Reproducibility is the credibility.

**R7.5** – A **guardrail eval**: measure that skill-enabled runs do not produce larger diffs than baseline on bugfix tasks. This directly tests §6 G6 / R1.2, and it is the metric most likely to embarrass the project if unmeasured.

### R8 – Repo and docs

**R8.1** – `README.md` with the hook, a before/after that lands in five seconds, install matrix, benchmark numbers, and honest scope limits.
**R8.2** – `CONTRIBUTING.md` covering how to propose a rule and the bar for adding one (must be non-obvious to a frontier model, must be checkable by a human reviewer, must not duplicate an existing rule).
**R8.3** – `CHANGELOG.md`, semver, `VERSION` file.
**R8.4** – CI: skill validation (`skills-ref validate`), token-budget checks, managed-block sync across all adapters, linter fixture tests, markdown lint.

### R9 – Legal and attribution

**R9.1** – The repo contains **no text from the book**. All rule statements are original prose. All code examples are original.
**R9.2** – Ideas, methods, and systems are not copyrightable (17 U.S.C. §102(b)); their expression is. The catalog captures the ideas in our own words and cites chapters so readers can go to the source.
**R9.3** – Prominent disclaimer, mirroring SimpleEnglish's: *unofficial, not affiliated with or endorsed by O'Reilly Media or the authors.*
**R9.4** – README recommends buying the book, with a link. This is both the ethical move and the one that makes the project welcome rather than adversarial.
**R9.5** – Repo is MIT. Any working notes derived from the book stay gitignored and never enter a release artifact.
**R9.6** – Project name is `taorc`, not the book's title, reducing trademark surface. Verify the skill `description` describes function rather than leaning on the title.

## 7. Success metrics

| ID | Metric | Target |
|---|---|---|
| M1 | Reduction in `taorc-lint` violations per 100 LOC, skill vs. baseline | ≥ 60% |
| M2 | Blind pairwise judge preference for skill output | ≥ 70% |
| M3 | Diff-size inflation on bugfix tasks, skill vs. baseline | ≤ 10% |
| M4 | Skill activation on the 100-prompt trigger suite (R2.3) | ≥ 90% on the 60 positives, ≤ 10% on the 40 negatives |
| M5 | Linter false-positive rate on the fixture suite | ≤ 5% |
| M6 | `SKILL.md` token size | ≤ 5,000 |
| M7 | Harness coverage | ≥ 10 with automated file-placement checks; ≥ 4 verified end-to-end by hand |
| M8 | Adoption (GitHub stars + skills.sh installs at 90 days) | directional only |

## 8. Scope

### v1 (ship)

- Full rule catalog (R1) – all 10 categories
- `skills/readable-code/` with `SKILL.md` + `references/{naming,comments,control-flow,structure,tests,ai-code-tells,chapter-map,language-map,review-checklist}.md`
- Three modes (R2.5), including the `/taorc-review` slash command
- `prompts/system-prompt.md`
- `examples/before-after.md`
- Distribution to all R3.2 targets, generated from source, CI-validated
- `taorc-lint` v1: the 10 high-precision rules in R6.1, Python + TypeScript, ast-grep
- Claude Code output style for review-mode formatting
- Evals (R7) with published results, cross-model (Claude + GPT + open-weights)
- README, CONTRIBUTING, CHANGELOG, LICENSE, disclaimer
- `docs/harness-verification.md` — what was tested where, and on which versions (M7)

### v1.x (fast follow)

- `taorc-lint` rule expansion beyond the initial 10; Go, Rust, Java, C#
- Additional languages in `language-map.md`
- Pre-commit hook integration

### v2 (later)

- Whole-project readability audit protocol with a written ledger (the `project-refactor.md` pattern)
- Per-team catalog overrides (`.taorc.toml`: disable rules, adjust severity, add project rules)
- Editor integration surfacing findings inline
- Companion skill covering *Clean Code* design-level concerns, or an explicit compose-with recommendation

## 9. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| **Over-application** – agent renames and rewrites unrelated code | High. Kills trust immediately | `X` guardrails as first-class rules; §R5.2 restraint examples; M3 measured explicitly |
| **Context cost** – skill loads on every code task | Medium | Hard 5k budget; aggressive progressive disclosure; measure with the skill on vs. off |
| **Rule conflicts with project linters** | Medium | R1.3 precedence: formatter and project config always win |
| **Copyright** | High if wrong | R9 in full; original prose and examples only; chapter citations, not summaries |
| **Trigger tuning** – fires on prose tasks, or fails to fire on code tasks | Medium | M4 gated on the 100-prompt suite; the hardest negatives are prose-readability asks ("make this README clearer"), which are deliberately over-represented in it |
| **Linter noise** | Medium | R6.4 fixtures; ship rules conservatively; default to `suggestion` severity |
| **Adapter drift across 10 targets** | Medium | Single source + generation + CI sync check (R3.1, R8.4) |
| **"Just a book summary" perception** | Medium | The `X` category, `ai-code-tells.md`, the linter, and published evals are all original work and should be foregrounded in the README |
| **Book is from 2011** | Low | Its advice is language-agnostic and has aged well; the `X` layer and AI-tells layer are what make it current |

## 10. Dependencies

- Agent Skills spec (stable, Linux Foundation / Anthropic open standard since Dec 2025)
- `skills-ref` validator
- `npx skills` / skills.sh registry
- ast-grep (R6 only; Semgrep evaluated and not chosen)
- An eval runner (Python, following SimpleEnglish's `evals/run_bench.py` shape)
- A copy of the book, for fidelity of rule extraction (see Q3)

## 11. Decisions

*Resolved 2026-08-21. Carried into `v1-design-doc.md`.*

**Q1 – Is `taorc-lint` in v1 or v1.1?**
It is the single strongest differentiator versus every existing clean-code skill, and it is what makes the evals objective rather than vibes. It is also easily half the engineering effort. *My recommendation: build a deliberately small v1—8–10 high-precision rules, Python + TypeScript only, ast-grep. Enough to power M1 and prove the concept; expand in v1.1.*

Answer: Let's go with your recommendation.

**Q2 – Skill name.**
The directory name and the `name` field must match, and `description` triggering matters more than branding. Options: `readable-code` (best trigger surface), `taorc` (brandable, opaque to the model), `art-of-readable-code` (clear, more trademark surface). *My recommendation: `readable-code` inside a repo named `taorc`.*

Answer: Let's go with your recommendation.

**Q3 – Fidelity of rule extraction.**
Do you have the book to hand? Working from it directly produces a materially better catalog than working from summaries—the book's precision on things like `first`/`last` vs. `begin`/`end` boundaries, or the taxonomy of what deserves a comment, does not survive third-party summarization. Nothing from it enters the repo either way (R9).

Answer: Yes, I have the book to refer to.

**Q4 – Single skill or a bundle?**
`clean-code-skills` ships one skill; `ertugrul-dmr` ships several (`clean-names`, `clean-comments`, `clean-tests`). *My recommendation: one skill in v1—the categories are deeply interdependent and a bundle multiplies the trigger-tuning problem. Revisit if `SKILL.md` cannot fit the budget.*

Answer: Let's go with your recommendation.

**Q5 – Relationship to `clean-code-skills`.**
Position as an explicit complement in the README ("use both"), stay silent, or compete head-on? *My recommendation: explicit complement. It is true, it is generous, and it makes the differentiation legible to anyone deciding between them.*

Answer: Let's go with your recommendation.

**Q6 – Do we ship a Claude Code output style?**
SimpleEnglish does. Low cost, narrow benefit, Claude-only. *My recommendation: v1.x.*

Answer: Yes, let's ship it in the first release, v1.0.

**Q7 – Eval budget.**
R7.3 cross-model evals cost real API money. Confirm you want them in v1, or whether a single-model eval is enough to publish initially.

Answer: Yes, v1; I'm OK with the cost.

## 12. References

- Boswell, D. & Foucher, T. *The Art of Readable Code*. O'Reilly, 2011. ISBN 978-0596802295.
- Agent Skills specification – <https://agentskills.io/specification>
- Agent Skills authoring best practices – <https://agentskills.io/skill-creation/best-practices>
- `juliusbrussee/caveman` – <https://github.com/juliusbrussee/caveman>
- `AminBlg/SimpleEnglish` – <https://github.com/AminBlg/SimpleEnglish>
- `tbhb/vale-ai-tells` – <https://github.com/tbhb/vale-ai-tells>
- `btseee/clean-code-skills` – <https://github.com/btseee/clean-code-skills>
- AGENTS.md – <https://agents.md>
- ast-grep – <https://ast-grep.github.io>
- VS Code Agent Skills – <https://code.visualstudio.com/docs/agent-customization/agent-skills>
