# taorc – Design Document (v1)

**Project**: `taorc` – *The Art of Readable Code* as an AI agent skill
**Status**: Approved
**Author**: josh-wong
**Date**: 2026-08-21
**Implements**: `v1-product-requirements-doc.md` (all decisions in §11 resolved)

## 1. Design summary

Four components, one join key.

| Component | What it is | Why it exists |
|---|---|---|
| **Catalog** | `catalog/rules.yaml` – the machine-readable registry of all 85 rule IDs | Single source of truth for IDs. Everything else references it; CI enforces referential integrity |
| **Skill** | `skills/readable-code/` – hand-written `SKILL.md` + `references/` | The product. Prose quality matters, so it is authored, not generated |
| **Adapters** | Generated managed blocks + manifests for 10+ harnesses | Distribution. Generated because they must be byte-identical |
| **Linter** | `taorc-lint`, 10 high-precision rules, bundled in the skill's `scripts/` | Objective scoring for evals; a fix-loop the agent can close |

The join key is the **rule ID** (`N7`, `C4`, `X2`). It appears in the catalog, in the skill prose, in linter output, in eval scores, and in agent review findings. If an ID appears anywhere and is not in the catalog, CI fails.

**Generation policy**: generate what must be *identical* (managed blocks, version fields, manifest metadata). Hand-write what must *read well* (`SKILL.md`, `references/`, `prompts/`). Generated prose reads like generated prose, and this project's whole thesis is that readable output is worth the effort.

## 2. Repository layout

```text
taorc/
├── README.md                      # hook, before/after, install matrix, benchmarks, disclaimer
├── CONTRIBUTING.md                # the bar for adding a rule
├── CHANGELOG.md
├── LICENSE                        # MIT
├── VERSION                        # single source for all version fields
│
├── catalog/
│   ├── rules.yaml                 # THE registry – every rule ID, one entry
│   └── schema.json                # JSON Schema for rules.yaml, enforced in CI
│
├── skills/readable-code/
│   ├── SKILL.md                   # <=500 lines, <=5000 tokens
│   ├── references/
│   │   ├── naming.md              # N rules: rationale, examples, when not to apply
│   │   ├── comments.md            # C rules
│   │   ├── control-flow.md        # F, E, V rules
│   │   ├── structure.md           # S rules
│   │   ├── tests.md               # T rules
│   │   ├── ai-code-tells.md       # the differentiator; maps LLM habits -> rule IDs
│   │   ├── language-map.md        # Python, TS/JS, Go, Rust, Java, C# idiom deltas
│   │   ├── review-checklist.md    # review-mode scan order + finding format
│   │   └── chapter-map.md         # rule ID -> book chapter (attribution)
│   └── scripts/                   # travels with every install method (14.1)
│       ├── taorc_lint.py          # single-file CLI, stdlib only
│       ├── sgconfig.yml
│       └── rules/                 # ast-grep YAML, one file per rule per language
│           ├── python/*.yml
│           └── typescript/*.yml
│
├── prompts/
│   ├── system-prompt.md           # <=800 tokens, hand-written (6.1)
│   └── system-prompt-mini.md      # <=150 tokens, hand-written (6.1)
│
├── commands/
│   └── taorc-review.md            # /taorc-review slash command (v1.0)
│
├── output-styles/
│   └── readable-code-review.md    # Claude Code output style (v1.0 per Q6)
│
├── examples/
│   └── before-after.md            # 18 pairs + 3 restraint examples
│
├── lint/                          # development + docs only; does NOT travel (14.1)
│   ├── configs/                   # recommended ruff/eslint config for structural rules
│   │   ├── ruff.toml
│   │   └── eslintrc.readability.json
│   └── fixtures/
│       ├── positive/              # must fire
│       └── negative/              # must NOT fire (false-positive suite)
│
├── docs/
│   └── harness-verification.md    # the M7 record: what was tested, where, when
│
├── evals/
│   ├── scenarios.json             # 10 code-writing tasks
│   ├── triggers.json              # 100-prompt trigger suite (60 pos / 40 neg)
│   ├── run_triggers.py            # tier-1 proxy classifier (§10.4)
│   ├── run_bench.py               # baseline vs skill, N models
│   ├── judge.py                   # blind pairwise + rubric
│   ├── score.py                   # automated metrics from taorc-lint
│   └── results/<date>/            # RESULTS.md + raw/
│
├── templates/
│   └── agent-block.md             # THE managed block, source for all adapters
│
├── scripts/
│   ├── build.py                   # catalog + templates -> all generated artifacts
│   ├── validate.py                # CI gate (see §9)
│   ├── install.sh / install.ps1
│   └── remote-install.sh / remote-install.ps1
│
├── .claude-plugin/{plugin,marketplace}.json
├── .codex-plugin/plugin.json
├── gemini-extension.json
├── .cursor/rules/readable-code.mdc            # generated
├── .github/
│   ├── copilot-instructions.md                # generated
│   ├── instructions/readable-code.instructions.md   # generated
│   ├── skills/readable-code/                  # copy of skills/readable-code (14.2)
│   └── workflows/{ci,release}.yml
├── .clinerules/readable-code.md               # generated
├── .windsurf/rules/readable-code.md           # generated
├── AGENTS.md   CLAUDE.md   GEMINI.md          # generated managed blocks
└── .gitignore                                  # includes notes/ – see §11
```

Note: `skills/readable-code/` sits at a path `npx skills` discovers natively (`skills/<name>/SKILL.md`), so `npx skills add josh-wong/taorc` works with no extra configuration.

## 3. The catalog

### 3.1 Schema

```yaml
# catalog/rules.yaml
version: 1
rules:
  - id: N3
    slug: encode-units-and-formats-in-names
    category: names
    title: Put units, formats, or encodings in the name when the value could be misread
    instruction: >
      When a number carries a unit, put the unit in the identifier.
      Bare `delay`, `size`, and `limit` force the reader to hunt for the unit.
    rationale: >
      The reader's alternative is to trace the value back to its source, which
      is the cost `P1` exists to minimize.
    chapter: 2
    severity: warning        # error | warning | suggestion
    lintable: true
    lint_rule: taorc-n3-unit-free-name
    applies_to: [all]
    examples:
      - lang: typescript
        before: "const timeout = 30;"
        after:  "const timeoutSecs = 30;"
    exceptions: >
      Skip when the project has a pervasive typed unit (a `Duration` type,
      `chrono::Duration`, `datetime.timedelta`) – the type already says it.

precedence:
  - Correctness beats readability. ...
```

Required: `id`, `slug`, `category`, `title`, `instruction`, `chapter`, `severity`, `lintable`. The top-level `precedence` list is also required; see §3.2.1.

The entry above shows `lintable: true` to illustrate the field. In the shipped catalog every rule is `lintable: false` until MS4 adds the matching `scripts/rules/*/` file, because CI checks that pairing in both directions.

- `chapter: 0` marks original content with no book source. That is the entire `X` category, plus any rule in another category that the book does not cover; see §3.2.
- `severity` ranks findings in review mode and sets the linter's level for lintable rules. CI asserts the two never disagree: a lint rule's `severity` must equal its catalog entry's.
- `applies_to` is a list of language identifiers (`python`, `typescript`, `go`, `rust`, `java`, `csharp`) or the literal `all`. It exists for the handful of rules that are language-specific — a rule about docstring conventions does not apply to Go. Defaults to `[all]` when omitted.
- `lint_rule` is required when `lintable: true` and must name a rule file that exists under `scripts/rules/`; CI checks both directions.

### 3.2 Categories and budget

| Prefix | Category | Chapters | Est. | Shipped | Reference file |
|---|---|---|---|---|---|
| `P` | Principles | 1 | 3 | 3 | in `SKILL.md` |
| `N` | Names | 2, 3 | 12 | 16 | `naming.md` |
| `A` | Aesthetics | 4 | 5 | 7 | `naming.md` |
| `C` | Comments | 5, 6 | 14 | 18 | `comments.md` |
| `F` | Control flow | 7 | 7 | 7 | `control-flow.md` |
| `E` | Expressions | 8 | 5 | 6 | `control-flow.md` |
| `V` | Variables | 9 | 5 | 5 | `control-flow.md` |
| `S` | Structure | 10–13 | 8 | 9 | `structure.md` |
| `T` | Tests | 14 | 6 | 6 | `tests.md` |
| `X` | Agent guardrails | – | 8 | 8 | in `SKILL.md` |
| | | | **73** | **85** | |

The **Est.** column is the pre-drafting estimate this document and PRD R1.1 were sized against; **Shipped** is the catalog as built. Nearly all the overrun is in chapters 2–6, which held more separable rules than estimated; chapters 7–14 came in at 32 against an estimate of 31, as §11 predicted they would. The 65–75 target in PRD R1.1 is superseded by this table.

`chapter: 0` marks a rule with no source in the book. That is the whole `X` category by construction, and `E4`, which catalogues a habit common in generated code that the book never discusses. Two further departures — `S6` inverting chapter 10's emphasis, and chapter 7's `goto` section having no rule — are recorded in `references/chapter-map.md` and in the `rationale` of the rule concerned.

### 3.2.1 Precedence

`catalog/rules.yaml` carries a top-level `precedence` list (PRD R1.3) alongside `rules`. It is ordered — earlier entries win — and it is the tiebreaker set `SKILL.md` §4 renders for the agent. It lives in the catalog rather than only in prose so that a conflict between two rules resolves against a validated source rather than a paraphrase in whichever adapter the agent happens to have loaded.

### 3.3 ID stability

IDs are permanent. A withdrawn rule gets `deprecated: true` and a `superseded_by`; the number is never reused. Renumbering would silently invalidate every review comment, eval result, and lint suppression ever written.

## 4. `SKILL.md`

### 4.1 Token budget

Hard ceiling 5,000; target 4,400 to leave headroom for growth.

| Section | Budget | Content |
|---|---|---|
| Frontmatter | 200 | See §4.2 |
| The premise | 150 | The Fundamental Theorem, in our words, and why it binds agents specifically |
| When this applies / modes | 350 | Mode table, mode inference |
| Operating loop | 500 | 5 steps |
| Rule catalog | 2,200 | All 85 rules, one line each, in tables by category |
| Precedence | 250 | The 5 tiebreakers |
| Self-check | 350 | The pre-delivery checklist |
| Reference map | 250 | When to load which file |
| Finding format | 200 | Shared with the linter |
| **Total** | **~4,450** | |

The full 73 one-liners live in `SKILL.md`, not in references. A rule the agent has to open a file to discover is a rule the agent will not apply. References carry rationale, worked examples, and—most importantly—the *exceptions*.

### 4.2 Frontmatter

```yaml
---
name: readable-code
description: >
  Write, comment, and review code so the next reader understands it in the least
  time. Applies on any code-writing, editing, refactoring, or code-review task,
  and specifically when naming things, writing or editing comments and
  docstrings, simplifying conditionals, or writing tests. Also use when asked to
  "make this readable", "clean up the comments", "review this for readability",
  "improve these names", or when removing AI-generated code tells such as
  step-by-step narration comments, banner comments, or empty names like data,
  result, and handler. Based on The Art of Readable Code (Boswell & Foucher).
license: MIT
metadata:
  version: "1.0.0"
  source: "The Art of Readable Code, Boswell & Foucher, O'Reilly 2011"
  homepage: "https://github.com/josh-wong/taorc"
---
```

Design notes on `description`—this is the highest-leverage 1,000 characters in the project:

- It leads with the *outcome*, so the model can judge relevance to any task.
- It names concrete triggers ("clean up the comments", "improve these names") for explicit asks.
- It names the AI tells, so the skill fires on de-slopping requests.
- It names activities (naming, commenting, conditionals, tests) so it fires *implicitly* during ordinary code writing—the hard case, and metric M4.

`compatibility` is deliberately omitted: the skill needs nothing but a text runtime. The linter is optional and self-describing.

### 4.3 Modes

| Mode | Inferred from | Behavior |
|---|---|---|
| `write` | Default – any code-writing task | Apply the catalog while generating. No unrelated cleanup. Self-check before presenting. |
| `review` | "review", "audit", "check", `/taorc-review`, a diff or PR in context | Findings only, no edits. Emit the §7 finding format. Never modify files. |
| `refactor` | "clean up X", "make X readable", "improve the names in X" | Behavior-preserving edits to the named target only. Report what was changed and what was deliberately left. |

Mode is inferred, never asked. If genuinely ambiguous, default to `write` for new code and `review` for existing code.

### 4.4 Operating loop

```text
1. READ LOCAL CONTEXT      Before writing: the file's existing naming vocabulary,
                           its comment density, the formatter/linter config
                           (.prettierrc, pyproject.toml, .editorconfig), the test
                           style. Local convention outranks this catalog (X2).

2. WRITE                   Apply the catalog. Naming and comments are decisions,
                           not decoration—make them while writing, not after.

3. SELF-CHECK              Run the checklist. This step is not optional and is
                           where most of the measured gain comes from.

4. VERIFY (if the linter is available)
                           Resolve the skill root the same way the managed block
                           does—first existing of `.claude/skills/readable-code/`,
                           `.agents/skills/readable-code/`,
                           `.github/skills/readable-code/`, `skills/readable-code/`
                           —then run `python <root>/scripts/taorc_lint.py --changed`.
                           If none exists, skip this step; do not search further.
                           Fix findings. Re-run. Repeat until clean or until a
                           finding is a justified false positive—say which.

5. REPORT                  State what you deliberately did NOT change and why.
                           This is the guardrail that keeps diffs narrow (X1).
```

This loop is for `write` and `refactor`. Review mode does not run it — steps 2 and 4 would modify files, which §4.3 forbids — and follows `references/review-checklist.md` instead.

Step 5 is load-bearing. Giving the agent a sanctioned way to *say* "I noticed `utils.py` is a junk drawer and left it alone" removes the pressure to fix it.

### 4.5 The self-check

Ten questions, ordered by how often agents fail them:

1. Does any comment restate what the line below it does? Delete it. (C1)
2. Does any comment narrate my own plan—"Step 1", "First, we"? Delete it. (C2, X7)
3. Would a new reader know the unit of every number I named? (N7)
4. Is any name an empty word—`data`, `result`, `handler`, `process`? (N1)
5. Is any non-obvious decision left unexplained? Add the *why*. (C7)
6. Can any nested block become a guard clause? (F4)
7. Is any boolean expression more than three terms? (E1)
8. Does any function do more than one thing my one-sentence description can cover? (S4)
9. Do my test names say the scenario and the expected result? (T3)
10. Did I change anything the task did not require? (X1)

### 4.6 Reference loading

Each pointer states its trigger. Generic "see references/" is ignored by agents.

```text
Read references/comments.md      before writing or editing any comment or docstring.
Read references/naming.md        when naming a public API, when a name is
                                 contested in review, or for any layout or
                                 alignment question (the A rules live here).
Read references/control-flow.md  when a function exceeds two levels of nesting or
                                 a condition exceeds three terms.
Read references/structure.md     before extracting a function or splitting a file.
Read references/tests.md         when writing or reviewing tests.
Read references/ai-code-tells.md when asked to de-slop, humanize, or clean up
                                 AI-generated code.
Read references/language-map.md  when the language is Go, Rust, Java, or C#.
Read references/review-checklist.md  at the start of every review-mode task.
Read references/chapter-map.md   only when the user asks where a rule comes
                                 from. It is an attribution artifact for humans,
                                 not working material — never load it to decide
                                 how to write code.
```

## 5. `references/ai-code-tells.md`

The single most differentiating file in the repo, and entirely original work. Structure: one row per tell, each mapped to a rule ID, so a de-slopping request resolves into catalog rules rather than vibes.

| Tell | Rule | Lint | Fix |
|---|---|---|---|
| Comment restates the next line | `C1` | ✓ | Delete |
| `// Step 1:` / `// First, we...` plan narration | `X7` | ✓ | Delete |
| `# ===== HELPERS =====` banner | `X8` | ✓ | Delete; if the file needs sections, it needs splitting |
| Emoji in comments, log lines, or output | `X8` | ✓ | Delete |
| Docstring restates the signature, adds nothing | `C14` | | Delete or replace with why/constraints |
| `# In a real implementation, you would...` | `C4` | ✓ | Delete or convert to a real `TODO(owner):` |
| Commented-out code left behind | `S7` | ✓ | Delete; git remembers |
| `data`, `result`, `output`, `info`, `item` | `N1` | ✓ | Name the thing |
| `handler`, `processor`, `manager`, `helper` | `N9` | | Name the action |
| `utils.py` / `helpers.ts` accumulating unrelated functions | `S2` | | Name the domain concept |
| Bare `timeout`, `size`, `limit` | `N3` | ✓ | Add the unit or bound |
| Single-use helper abstracted "for reusability" | `S6` | | Inline it |
| Try/except wrapped around code that cannot throw | `S7` | | Delete |
| Reimplemented `groupby` / `Counter` / `zip` | `S8` | | Use the library |
| Intermediate variable that exists only to be returned | `V1` | | Return directly |
| `if x == True:` / `if len(x) > 0:` | `E4` | | `if x:` |
| Test named `test_1`, `test_basic`, `test_works` | `T3` | ✓ | Name the scenario and expectation |
| Hedging comment: "This should probably..." | `C13` | | Decide, or file a real TODO |

The **Lint** column marks the nine `taorc-lint` catches (the banner and emoji rows share one rule, `X8`); the rest need the agent's judgment.

Note that four of the most recognizable tells — plan narration, banners, emoji, and unrequested cleanup — land on `X` rules rather than book-derived ones. The book had no reason to warn against habits that only a generative model has.

## 6. Distribution

### 6.1 Generation

`templates/agent-block.md` is the single source for the managed block that every non-skill adapter embeds. `scripts/build.py` reads `VERSION` + the template + `catalog/rules.yaml` and writes:

| Output | Wrapper |
|---|---|
| `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` | block, inserted or replaced in place |
| `.cursor/rules/readable-code.mdc` | `description` + `alwaysApply: true` frontmatter, then block |
| `.github/copilot-instructions.md` | block |
| `.github/instructions/readable-code.instructions.md` | `applyTo: "**/*"` frontmatter, then block |
| `.clinerules/readable-code.md`, `.windsurf/rules/readable-code.md` | block |
| — | `prompts/*.md` are **not** generated; see below |
| `.claude-plugin/*`, `.codex-plugin/*`, `gemini-extension.json` | version field sync only |

**The prompts are hand-written.** Condensing 85 rules into 800 tokens is an editorial judgment about which rules survive, not a mechanical transform, and §1's policy says prose that must read well is authored. `build.py` does not touch `prompts/`; CI still enforces their token budgets (check 4) and that every ID they cite exists (check 2). Treating them as generated would have meant inventing a selection algorithm nobody could tune.

Managed block markers:

```text
<!-- taorc:begin v1.0.0 -->
...
<!-- taorc:end -->
```

Insert if absent, replace between markers if present, never touch anything outside them. This makes install, update, and uninstall idempotent against files the user also edits by hand.

### 6.2 The managed block

Target ~700 tokens. It is a *pointer plus the non-negotiables*, not the full catalog—the full catalog lives in `SKILL.md`, and the block tells the agent where to find it:

```markdown
<!-- taorc:begin v1.0.0 -->
## Readable code (taorc)

Write code so the next reader understands it in the least time. Full rules:
first existing path wins—`.claude/skills/readable-code/SKILL.md`,
`.agents/skills/readable-code/SKILL.md`, `.github/skills/readable-code/SKILL.md`,
`skills/readable-code/SKILL.md`. Read it before non-trivial work.

### Always
- Name the thing, not its shape. No `data`, `result`, `handler`, `helper`. (N1, N2)
- Put the unit in the name: `timeoutSecs`, not `timeout`. (N7)
- Comment *why*, never *what*. If a comment restates the line below it, delete it. (C1)
- No plan narration ("Step 1:"), no banner comments, no emoji in code. (C2, C3, C4)
- Guard clauses over nesting. Handle the simple case first. (F2, F4)
- More than three terms in a condition: name the parts. (E1)
- One task per function. If describing it needs "and", split it. (S4)
- Test names say the scenario and the expected result. (T3)

### Never
- Widen the diff to satisfy a readability rule. Mention it instead. (X1)
- Override a project's existing vocabulary or conventions with these. (X2)
- Rename an exported symbol unless asked. (X3)
- Mix a readability change and a behavior change in one step. (X4)
- Argue with the formatter. It wins. (X5)
<!-- taorc:end -->
```

### 6.3 Install paths

| Path | Command |
|---|---|
| Agent Skills registry | `npx skills add josh-wong/taorc` |
| Claude Code plugin | `claude plugin marketplace add josh-wong/taorc` then `claude plugin install taorc@taorc` |
| claude.ai / Desktop | Upload `taorc-skill-v1.0.0.zip` from the GitHub release |
| Everything else | `curl -fsSL .../install.sh \| bash` – flags `--project` (default), `--global`, `--agents=<list>`, `--detect`, `--uninstall` |
| Any LLM | Paste `prompts/system-prompt.md` |

`--detect` refreshes only already-installed adapters, comparing the version in each managed block against `VERSION`.

### 6.4 Claude Code output style (Q6 → v1.0)

`output-styles/readable-code-review.md`:

```yaml
---
name: Readable Code Review
description: Reports readability findings as taorc rule citations with concrete fixes.
keep-coding-instructions: true
---
```

`keep-coding-instructions: true` is required—this changes how Claude *reports*, not whether it engineers. The body constrains review output to the §7 finding format and forbids prose preamble around findings.

Scope note: this is Claude-only and cosmetic. It ships because it is cheap, and it is explicitly not part of the eval matrix.

### 6.5 The `/taorc-review` command

Ships in v1.0. `commands/taorc-review.md` is a Claude Code plugin command that puts the skill into `review` mode against the current diff, or an explicit target if one is given:

```yaml
---
description: Review the current diff for readability against the taorc catalog.
argument-hint: "[file|directory|PR#]  (default: the current diff)"
---
```

The body is thin on purpose—it activates the skill, names the mode, and defers everything else to `SKILL.md` and `references/review-checklist.md`. Duplicating catalog content into the command would create a second place for the rules to drift.

It is Claude-Code-only packaging, not a capability. Review mode is reachable in every harness through natural language ("review this for readability"), which is how §4.3 infers it; the command is a shortcut, and nothing in the product depends on it.

### 6.6 Harness verification (M7)

Ten harnesses is not ten integrations. There are only **three delivery mechanisms**:

| Mechanism | Harnesses |
|---|---|
| Agent Skills runtime reads `SKILL.md` | Claude Code, Copilot, Cursor, Codex, Gemini CLI, opencode, ~30 more |
| Managed block in an instructions file | `AGENTS.md`, `CLAUDE.md`, `.mdc`, `.instructions.md`, `.clinerules` readers |
| Pasted system prompt | anything else |

The only per-harness variable is *where the file goes*, which CI check 9 asserts for all ten. What CI cannot assert is that the harness reads the file and behaves differently — that needs a human in each product.

So the release gate is **four manual smoke tests, one per delivery path plus the two highest-traffic products**: Claude Code (skills runtime), VS Code Copilot (skills + `.instructions.md`), Cursor (`.mdc`), and one `AGENTS.md` reader (Codex or opencode). Each runs the same two prompts — one implicit code-writing task, one explicit "review this for readability" — and records the harness version and date in `docs/harness-verification.md`.

"Took effect" needs a definition, because only some harnesses announce that a skill loaded. The observable test is behavioral, and works everywhere: the explicit prompt must produce findings in the §7 format with real rule IDs. A harness that outputs prose review with no IDs has not loaded the skill, whatever its UI claims.

**Why not claim ten.** Publishing "10 harnesses verified working" on the strength of file placement would be the same overclaim §10.5 forbids in the eval results. M7 therefore reads as two numbers: 10 with automated placement checks, 4 verified end-to-end. The README says exactly that.

## 7. Finding format

One format, used by review mode, refactor mode's change report, and `taorc-lint`. Shared format means the agent's fix-loop reads its own output and the linter's output identically.

```text
[N3] src/api/client.ts:42  Name has no unit
  const timeout = 30;
  → rename to `timeoutSecs` (or `timeoutMs` if milliseconds)
```

- `[ID]` first – greppable, and forces the agent to ground the finding in a real rule.
- Location second – `file:line` is clickable in most harnesses.
- Matched source third – proves the finding is real.
- `→ fix` last, imperative and concrete. Never "consider renaming".

`--format=json` emits `{id, slug, severity, file, line, col, matched, fix}` for CI and the eval scorer.

**Anti-hallucination**: `SKILL.md` states that findings must cite an ID present in its own catalog table, and that if no rule fits, the observation is reported as prose without an ID. This is the same failure SimpleEnglish documented for STE rule numbers—models confidently invent plausible IDs.

## 8. `taorc-lint`

### 8.1 Architecture

`skills/readable-code/scripts/taorc_lint.py` – single file, Python 3.10+, **stdlib only**, so an agent can run it with no install step. It lives inside the skill so it travels with every install method; see §14.1.

```text
taorc_lint.py
  ├─ shells out to `ast-grep scan --json` with scripts/sgconfig.yml (9 of 10 rules)
  ├─ implements C1 (comment-echoes-code) in Python over ast-grep's
  │  comment-node JSON                                              (1 of 10 rules)
  ├─ merges, sorts, formats (text | json)
  └─ exits 0 unless `--fail-on` is passed (see §8.6)
```

If `ast-grep` is not on PATH, it prints an install hint and exits 0—never blocks a build over a missing optional tool.

**Deliberate non-goal**: structural checks that mainstream linters already do well. `taorc-lint` does not implement nesting depth, function length, or cyclomatic complexity. Instead `lint/configs/` (repo-root, README-documented, never executed by the agent) ships tuned `ruff.toml` and `eslintrc.readability.json` snippets enabling `PLR0912`/`max-depth`, `PLR0915`/`max-lines-per-function`, `max-statements`, and `complexity`. Reimplementing them would be worse and would violate S8 in our own repo.

### 8.2 The v1 rules

All are high-precision by construction—each fires on a syntactic signature that is almost never legitimate.

| ID | Rule | Detection | Sev |
|---|---|---|---|
| `C1` | Comment echoes the code below it | See §8.2.1 | warning |
| `C4` | Placeholder comment | `in a real implementation\|for now\|simplified (version\|example)\|in production` | suggestion |
| `N1` | Empty-word identifier | Declaration name in `{data,result,output,temp,tmp,val,value,item,obj,info,helper,handler,manager,processor,util,utils}`, **excluding** loop variables, comprehension targets, and functions under 5 lines | warning |
| `N3` | Unit-free time or size name | Name matches `(delay\|timeout\|elapsed\|duration\|interval\|expiry\|ttl\|size\|length\|limit)$` with no unit suffix and a numeric literal initializer | warning |
| `N11` | Negated boolean name | Name matches `^(is\|has\|can)?_?(not\|no\|non\|dont\|cant\|disable)` on a boolean-valued declaration | suggestion |
| `S7` | Commented-out code | Comment body matches statement-shaped source for the language | warning |
| `T3` | Uninformative test name | Test function name matches `^test_?(\d+\|it\|works\|basic\|main\|case\d*)?$` | warning |
| `X7` | Plan narration comment | Comment matches `^\W*(step \d|first,|next,|then,|finally,|now (we\|let's))` | warning |
| `X8` | Banner comment or emoji | Comment matches `[=\-*_#]{5,}`, or a comment or string literal contains a Unicode emoji | warning |

Severities are deliberately conservative: two `suggestion`, seven `warning`, **zero `error`**. Nothing in v1 fails a build by default. A linter that blocks CI on a naming opinion gets uninstalled.

Each `Sev` above is the severity of that rule's catalog entry, not an independent choice — §3.1 requires the two to agree and CI asserts it. `X8` covers banners and emoji under one ID because they share a rationale and a fix; the ast-grep rule matches either pattern.

#### 8.2.1 C1 in detail

C1 is the highest-value rule in the set and the only one that is not a pattern match, so it gets a specified algorithm rather than a description. Left vague, an implementer guesses a threshold and ships false positives, which per PRD R6.4 discredits the whole tool.

```text
1. Take the comment text and the next executable statement.
2. Tokenize both: lowercase, split camelCase and snake_case, strip punctuation.
3. From the comment's tokens drop language keywords and stopwords
   (the, a, an, this, that, to, of, and, or, then, we, it, is, are, in, on,
   for, with, through, each, all). Call what remains the CONTENT tokens.
4. If fewer than 2 content tokens, do not fire. "hack" and "why?" carry
   meaning this rule cannot judge.
5. Drop narration verbs (loop, iterate, increment, decrement, set, get,
   create, initialize, return, call, check, add, remove, update, build,
   make, do). If nothing remains, do not fire.
6. Suffix-stem both sides (s, es, ed, ing, er). Fire when >= 80% of the
   remaining comment tokens appear among the statement's identifier tokens.
```

**Step 5 is what makes the rule work at all.** The classic echo comment always leads with a verb the code never names — `increment`, `loop`, `set` — and that verb alone drags coverage below any useful threshold. Strip narration verbs and the same comment scores 100%; leave them in and C1 fires on almost nothing, which is the failure mode this spec exists to prevent.

Stemming (step 6) is required for the same reason: `counter` and `count` are the same word to a reader, and a rule that cannot see that misses the most common form of the tell.

| Comment | Next statement | Content → post-verb → stemmed | Score | |
|---|---|---|---|---|
| `# Loop through the users` | `for user in users:` | {loop, users} → {users} → {user} vs {user} | 100% | fires |
| `# increment the retry counter` | `retry_count += 1` | {increment, retry, counter} → {retry, counter} → {retry, count} vs {retry, count} | 100% | fires |
| `# retry after 3 failures — upstream rate-limits` | `retry_count += 1` | 8 content tokens, 1 matched | 13% | no fire |
| `# hack` | anything | 1 content token | — | no fire (step 4) |

The third row is the one that matters: a *why* comment sitting on the same line as a *what* comment must survive. Every negative fixture is built from that shape.

Both the 80% threshold and the two word lists are starting values, tuned against `lint/fixtures/negative/` until the false-positive rate clears PRD M5. Record whatever they end up as here — a threshold nobody can trace back to a fixture is a threshold that gets changed on a hunch.

### 8.3 Rule file shape

```yaml
# skills/readable-code/scripts/rules/typescript/x8-banner-comment.yml
id: taorc-x8-banner-comment
language: TypeScript
severity: warning
message: "[X8] Banner comment"
note: "→ delete it; a file that needs section dividers needs splitting"
rule:
  kind: comment
  regex: '[=\-*_#]{5,}'
```

`ast-grep`'s `id` carries the descriptive slug; `message` carries the citable `[X8]`. The scan output is parsed on `[ID]` prefix.

### 8.4 Fixtures

Every rule needs both:

- `lint/fixtures/positive/<lang>/<rule>.{py,ts}` – must fire, exact line asserted.
- `lint/fixtures/negative/<lang>/<rule>.{py,ts}` – must **not** fire. This is the important half. Each negative fixture encodes a legitimate use: a `tmp` in a three-line function, a comment that looks redundant but records a non-obvious constraint, a `size` in a project with a `Bytes` newtype, a genuinely descriptive `test_main`.

CI asserts exact finding sets on both. PRD metric M5 (≤5% false-positive rate) is measured against the negative suite.

### 8.5 Suppressions

Referenced in §3.3 and §13 but never defined, so: a suppression is a trailing or preceding comment naming the rule and a reason.

```python
data = json.loads(raw)  # taorc-ignore: N1 — matches the wire format's field name
```

```text
# taorc-ignore-next: C1 — the restatement is deliberate; see ADR-014
```

Rules:

- The rule ID is required. A bare `taorc-ignore` suppresses nothing.
- The reason is required. `taorc_lint.py` reports a suppression with no reason as its own finding — an unexplained suppression is how a rule quietly stops applying.
- `--show-suppressed` lists them; `--fail-on` never counts them.

The repo's own `examples/` use these, which doubles as the test that suppression works (§13).

### 8.6 CLI

```text
taorc_lint.py [paths...]
  --changed          lint files changed vs. the merge base (agent default)
  --format text|json
  --severity suggestion|warning|error   minimum reported
  --rules C1,N7      subset
  --show-suppressed  list suppressed findings and their reasons
  --fail-on warning  exit non-zero at or above (default: never fail)
```

## 9. Build and CI

`scripts/validate.py` is the single CI gate. It fails on:

1. **Schema** – `catalog/rules.yaml` violates `catalog/schema.json`.
2. **Referential integrity** – an ID cited in any `.md`, lint rule, or eval scorer that is not in the catalog; or a catalog rule missing from `SKILL.md`'s catalog table. *This is the check that holds the whole design together.*

   The second half is deliberately weaker than "cited somewhere": `SKILL.md` lists all 85, so appearing there is the floor. Requiring a citation in the managed block, the self-check, or `ai-code-tells.md` would drag every rule into those artifacts to satisfy CI—which is precisely how the block stops being a summary. Categories `A` and `P` legitimately live only in the catalog table and `naming.md`.
3. **Skill spec** – `skills-ref validate ./skills/readable-code` fails, or `name` ≠ directory name.
4. **Budgets** – `SKILL.md` > 5,000 tokens or > 500 lines (PRD R2.2); `templates/agent-block.md` > 700 tokens (§6.2); `system-prompt.md` > 800; `system-prompt-mini.md` > 150. Tokens measured with a real tokenizer, not word count.
5. **Adapter drift** – any generated file differs from what `build.py` would produce. (Run `build.py`, `git diff --exit-code`.)
6. **Version sync** – `VERSION` ≠ any manifest version or any managed-block marker version.
7. **Lint fixtures** – positive/negative suites do not produce their asserted finding sets.
8. **Installer behavior** – fresh install, re-run (idempotent), install into a file with pre-existing user content (block inserted, user content preserved), `--detect` update, `--uninstall` (block removed, user content intact). Run in a temp dir on Linux, macOS, and Windows runners.
9. **Placement matrix** – for each of the 10 R3.2 targets, install into a temp repo and assert the expected file exists at the documented path with the expected content and version marker. This is what makes the "10 harnesses" claim in M7 checkable; it verifies *placement*, not that the harness reads the file.
10. **Markdown lint** and link check.

Release workflow on tag: run `validate.py`, build `taorc-skill-v<version>.zip` for claude.ai upload, generate release notes from `CHANGELOG.md`, publish.

## 10. Evals

### 10.1 Design

10 scenarios × 2 conditions (baseline / skill) × 3 models = 60 generations per run.

Scenarios span the shapes where readability actually varies:

| # | Scenario | Probes |
|---|---|---|
| 1 | Implement a function from a spec | N, C |
| 2 | Fix a bug in existing code | X1 diff discipline |
| 3 | Add a feature to an existing file | X2 local convention |
| 4 | Write tests for a given module | T |
| 5 | Parse and transform a data file | N, V, S |
| 6 | Write an API request handler | F, E |
| 7 | Refactor a deeply nested function | F, E |
| 8 | Write a CLI script | S, C |
| 9 | Add error handling to existing code | F, C |
| 10 | De-slop an AI-written file (provided) | ai-code-tells |

Scenarios 2 and 3 exist to catch the failure mode, not to show the win. If the skill inflates those diffs, that is the finding.

### 10.2 Scoring

**Automated** (`score.py`, deterministic, free):

- `taorc-lint` findings per 100 LOC → PRD metric M1
- comment-to-code ratio, and share of comments that are *why*-comments
- mean and max nesting depth (via ruff/eslint)
- empty-word identifier count
- diff size on scenarios 2, 3, 9 → PRD metric M3

**Judged** (`judge.py`):

- Blind pairwise, order randomized, on one question only: *which of these would take a new reader less time to understand?* → M2
- Per-category rubric, 1–5, on N / C / F / S / T

Judge model must differ from the generating model to reduce self-preference bias. Every judgment stored raw in `results/<date>/raw/`.

### 10.3 Model matrix (Q7 → confirmed for v1)

| Model | Why |
|---|---|
| `claude-opus-5` | Primary target |
| A current OpenAI model via Codex CLI | Cross-vendor claim |
| Qwen or Llama, open weights | Substantiates "works with any LLM" and validates `system-prompt.md`, since these have no skill runtime |

Cost estimate: 60 generations of ~2k output tokens plus ~120 judge calls ≈ **$15–40 per full run**. Budget for 3–4 runs across v1 development. This is low enough that it should be run on every catalog change, not just at release.

### 10.4 Trigger suite (M4)

Activation cannot be tuned by running full agent sessions—each one costs a minute and a few cents, so a 100-prompt suite would be too slow to iterate against, which is how a `description` ends up shipped untested. Two tiers instead:

**Tier 1 — proxy classifier (`evals/triggers.json`, `evals/run_triggers.py`).** For each of the 100 prompts, one cheap classification call: given only the skill's `name` and `description`, is this skill relevant to this request? No agent run, no tools. A full pass costs cents and takes under a minute, so the `description` can be iterated dozens of times.

It runs on changes to `SKILL.md`'s frontmatter or `catalog/rules.yaml`, and on demand — not on every PR. It needs an API key, and a docs-only commit should not spend one or block on a provider outage.

At n=100 (60/40), 90% resolves to roughly ±7pp and the 10% negative target to 2.5pp granularity. The 30-prompt suite this replaces could not resolve either target: with 15 negatives, a single false fire scores 6.7%, so a ≤5% target was unmeasurable by construction.

**Tier 2 — end-to-end spot check.** 10 prompts (7 positive, 3 negative) run in real Claude Code, confirming that tier 1 predicts real activation. If they diverge, tier 1 is miscalibrated and the proxy prompt needs work—not the `description`.

**The negatives are the hard half.** The most dangerous is prose readability: *"make this README clearer"*, *"tighten this error message"*, *"review my docs for clarity"*. These share the skill's entire vocabulary and are exactly what it must not claim. They get 10 of the 40 negative slots. Code *explanation* ("what does this function do?") gets 5 more — reading is not writing, and the skill has nothing to add there.

### 10.5 Publication

`evals/results/<date>/RESULTS.md` – method, per-scenario tables, aggregate metrics against PRD targets, and raw outputs committed. Any metric that misses its target is published anyway with a note. Selective reporting is the thing that would make the benchmark worthless.

## 11. Content authoring workflow

Given Q3 (the book is available), the catalog is authored against the source rather than from summaries. Constraint from PRD R9: **no text from the book enters the repository.**

```text
1. DRAFT       Per chapter, draft rule entries in catalog/rules.yaml from the
               chapter's ideas. Original phrasing, original examples.

2. VERIFY      Read the chapter. Check three things:
                 a. Coverage  – did we miss a technique?
                 b. Precision – did we blur a distinction the book draws
                    sharply? (`first`/`last` vs `begin`/`end`; the taxonomy of
                    what deserves a comment; when a `tmp` is legitimate)
                 c. Fidelity  – are we asserting something the book does not?

3. REWRITE     Fix in our own words. Never transcribe to "get it right" and
               paraphrase later—that produces derivative phrasing.

4. EXAMPLES    Write a fresh before/after in a language the book does not use
               for that point. Different domain, different names, different
               language. Never adapt the book's example.

5. RECORD      catalog entry gets `chapter: N`. chapter-map.md gets the
               ID -> chapter row. That is the attribution.
```

`notes/` is gitignored, for working notes taken while reading. Nothing in it is ever released.

**Where this is most likely to go wrong**: Chapters 2, 3, 5, and 6 are the ones with genuinely non-obvious taxonomies—the ones a frontier model paraphrases into mush. Those four get the most careful verification pass. Chapters 11–13 are more discursive and translate into fewer, broader rules.

## 12. Milestones

| M | Deliverable | Gate |
|---|---|---|
| **MS0** | Repo skeleton, `catalog/schema.json`, `build.py`, `validate.py`, CI green on an empty catalog | Generation and validation work before content exists |
| **MS1** | Catalog drafted, chapters 1–6 (P, N, A, C – 44 rules; original estimate of 34 was revised upward during drafting), verified per §11 | Josh's verification pass |
| **MS2** | Catalog complete (85 rules), `chapter-map.md`, `precedence` in the catalog | Referential integrity green |
| **MS3** | `SKILL.md` + all 9 reference files | Token budget green; manual read-through |
| **MS4** | `taorc-lint` + fixtures + configs | M5 false-positive target met |
| **MS5** | Adapters + installers + manifests | Installer + placement-matrix tests green on 3 OSes; 4-harness manual pass recorded in `docs/harness-verification.md` |
| **MS6** | Eval harness + first full run | Baseline numbers exist |
| **MS7** | Iterate catalog and description against eval results | M1, M2, M3, M4 targets met |
| **MS8** | README, CONTRIBUTING, CHANGELOG, examples, output style, `/taorc-review` | – |
| **MS9** | Tag v1.0.0, publish, register with skills.sh | All PRD §7 metrics published |

MS7 is the milestone most likely to be skipped and least likely to be skippable. The first draft of a skill is not the product; the version tuned against its own eval results is. Budget real time there.

## 13. Risks specific to this design

| Risk | Mitigation |
|---|---|
| **The `description` under-triggers on implicit tasks** – the skill only fires when someone says "readable" | M4 gated on the 100-prompt tier-1 suite (§10.4), cheap enough to run on every `description` change; tier-2 spot check confirms the proxy tracks reality |
| **The catalog is too long for the agent to apply** – 85 rules exceeds working attention | The self-check (§4.5) is only 10 items, ordered by observed failure frequency. If evals show low application, cut the catalog to the 30 that move metrics, and move the rest to references |
| **Generated adapters drift silently** | CI check 5 (§9) makes drift a build failure, not a discovery |
| **`taorc-lint` fires on the repo's own examples** | Run it over `examples/` in CI; every intentional violation carries an inline suppression, which also proves suppression works |
| **Over-application despite guardrails** | M3 measured on 3 of 10 scenarios; the "report what you left alone" step (§4.4 step 5) gives the agent an outlet |
| **Book fidelity drifts as the catalog is edited post-MS2** | Any change to a rule's `instruction` requires re-checking against its `chapter` before merge; noted in CONTRIBUTING |

## 14. Implementation decisions

Not blocking MS0, but settled here so no milestone stalls on them.

### 14.1 Where `taorc-lint` lives – **inside the skill, in `scripts/`**

**Decision**: `skills/readable-code/scripts/taorc_lint.py` plus `scripts/rules/`. Fixtures and config snippets stay at repo root in `lint/`.

The deciding factor is distribution, not tidiness. `npx skills add`, the Claude Code plugin, and the claude.ai `.zip` all install **only the skill directory**. A linter at repo root would reach only the minority of users who clone the repo or run the curl installer—and §4.4 step 4 tells the agent to run it. An operating loop that references a tool most installs do not have is worse than no loop step at all.

The Agent Skills spec provides `scripts/` for exactly this case, so this is the blessed path rather than a workaround.

The split is along a clean line:

| Path | Travels with an install? | Contents |
|---|---|---|
| `skills/readable-code/scripts/` | Yes | `taorc_lint.py`, `sgconfig.yml`, `rules/` – everything needed at runtime |
| `lint/fixtures/` | No | Positive/negative suites; CI only |
| `lint/configs/` | No | `ruff.toml`, `eslintrc.readability.json` – copy-paste recommendations documented in the README, never executed by the agent |

Stdlib-only and graceful degradation when `ast-grep` is absent (§8.1) matter more under this decision, not less: the script now lands on machines that never opted into it.

### 14.2 `.github/skills/readable-code/` – **copy, not symlink**

**Decision**: `build.py` copies the skill directory; CI check 5 catches drift.

Git symlinks require `core.symlinks=true` on Windows, plus Developer Mode or elevation. Without them, the checkout silently materializes a **text file containing the path**. Copilot would then read that path string as the skill body and fail in a way that produces no error—the worst failure shape available. A copy costs a few KB and one CI check.

This applies to the repo's own dogfooding copy. End users get their copy placed by `install.sh` / `install.ps1`, which can pick per-platform behavior at install time.

### 14.3 Open-weights eval model – **Qwen3.6-27B, hosted with a pinned model ID**

**Decision**: hosted inference (Together / Fireworks / OpenRouter), pinned model ID, temperature and top_p recorded in `RESULTS.md`.

Two things follow from what this model is actually for. Its job in the matrix is to validate `prompts/system-prompt.md`—the no-skill-runtime path—not to benchmark the model.

**Why not local.** Quantization changes instruction-following materially; Q4_K_M and Q8 are different evaluands. Published numbers nobody can reproduce without your exact GGUF, quant, and sampler settings are not a benchmark. Hosted gives a pinned identity.

**Why a dense 27B rather than the top of the leaderboard.** Kimi K3 and DeepSeek V4-Pro-Max are frontier-adjacent. If a 2.8T model follows a pasted system prompt, that proves nothing about the constrained case the fallback prompt exists for. Qwen3.6-27B is a dense 27B that people genuinely do run on one GPU or a 32GB Mac—the actual audience for `system-prompt.md`.

**The real reproducibility lever is sampler settings**, not model choice. Pin and publish them.

Separately, run `system-prompt-mini.md` against a local Ollama build as an unpublished smoke test. Useful signal, not a metric.

### 14.4 `skills.sh` listing – **nothing to build; verify at release**

**Decision**: no release step. Confirmed against the skills.sh docs: the leaderboard is driven by anonymous install telemetry from the `skills` CLI, with no submission flow, no metadata file, and no layout requirement beyond a discoverable `SKILL.md`.

`skills/readable-code/SKILL.md` already sits on a path the CLI discovers natively (§2), so `npx skills add josh-wong/taorc` works with no additional configuration.

MS9 therefore carries one verification, not a task: run `npx skills add josh-wong/taorc` against the published tag from a clean machine, confirm it resolves and installs. Listing follows real installs on its own; treat it as an outcome rather than a step. If it has not appeared some weeks after release, that is a signal about adoption, not about packaging.
