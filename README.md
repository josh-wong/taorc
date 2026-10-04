# taorc

taorc is an agent skill that makes AI coding agents write code a stranger can read quickly. It is built on the ideas in *The Art of Readable Code* (Boswell & Foucher, O'Reilly, 2011). It works in Claude Code, GitHub Copilot, Cursor, Codex, Gemini CLI, Cline, Windsurf, and any other LLM you can give a system prompt.

Coding agents optimize for code that does what was asked and looks finished at a glance. That leaves recognizable tells: comments that narrate the agent's plan, names like `data` and `handler`, numbers with no unit, helpers wrapped around a single call. taorc targets those tells specifically, and measures whether it removed them.

```python
# Before: what an agent tends to write
# Loop through the items and process each one
for item in data:
    result = handle(item, 30)

# After: with taorc loaded
for invoice in overdue_invoices:
    send_reminder(invoice, grace_period_days=30)
```

More pairs, including four where the right move is to change nothing, are in [`examples/before-after.md`](examples/before-after.md).

## What's in it

The skill is the product. Everything else exists to deliver it to more harnesses, or to check that it works.

- **An 85-rule catalog** ([`catalog/rules.yaml`](catalog/rules.yaml)) covering naming, comments, control flow, expressions, variables, structure, and tests. Each rule has a permanent ID such as `N3` or `C1`, and each cites the book chapter it draws on. The eight `X` guardrails are this project's own. They keep the agent from over-applying the rest: no unrequested renames of public symbols, no widening a bugfix into a cleanup, no arguing with the project's formatter.
- **The skill** ([`skills/readable-code/`](skills/readable-code/SKILL.md)), which infers one of three modes from the request. `write` applies the rules while generating new code. `review` reports findings with rule IDs and edits nothing. `refactor` makes behavior-preserving fixes to a named target only. A [reference file](skills/readable-code/references/ai-code-tells.md) maps the habits of LLM-written code to the rule that governs each.
- **A linter**, `taorc-lint`, bundled inside the skill so it travels with every install. It checks the nine rules a pattern match can catch with high precision. See [Linting](#linting).
- **A published benchmark** ([`evals/`](evals/)) comparing the same models with and without the skill, with every completion committed. See [Results](#results).

## Install

Pick the row that matches how your harness reads instructions or skills.

| Target                                                                             | Command                                                                                                                           |
| ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Agent Skills runtimes                                                              | `npx skills add josh-wong/taorc`                                                                                                  |
| Claude Code plugin                                                                 | `claude plugin marketplace add josh-wong/taorc` then `claude plugin install taorc@taorc`                                          |
| claude.ai or Claude Desktop                                                        | Upload `taorc-skill-v1.0.0.zip` from the [latest release](https://github.com/josh-wong/taorc/releases/latest)                     |
| Everything else (Copilot, Cursor, Codex, Cline, Windsurf, Gemini CLI, and similar) | `curl -fsSL https://raw.githubusercontent.com/josh-wong/taorc/main/scripts/install.sh \| bash` (`scripts/install.ps1` on Windows) |
| Any other LLM                                                                      | Paste [`prompts/system-prompt.md`](prompts/system-prompt.md) into the system prompt                                               |

The `curl | bash` and `install.ps1` installers default to `--project` scope (the current directory). They also accept `--global`, `--agents=<comma-list>` to install a subset of harnesses, `--detect` to refresh only adapters already installed, and `--uninstall` to remove everything taorc placed. See `scripts/install.sh --help` for the full reference. The installers only ever insert or replace text between `<!-- taorc:begin -->` and `<!-- taorc:end -->` markers, so the rest of an existing `AGENTS.md` or `CLAUDE.md` is never touched.

The installers download `main` by default. Each installer records the version it shipped with, and stops with an error rather than install a different version from `main` unless you set `TAORC_REF`. To pin an install to a release, fetch the installer from that release's tag and set `TAORC_REF` to the same tag. You need both: the URL decides which installer runs, and `TAORC_REF` decides which files it installs.

```bash
curl -fsSL https://raw.githubusercontent.com/josh-wong/taorc/v1.0.0/scripts/install.sh | TAORC_REF=v1.0.0 bash
```

On Windows, set `$env:TAORC_REF = "v1.0.0"` before running `install.ps1` taken from the same tag. `TAORC_REF` also accepts a branch name or a commit SHA.

Automated tests confirm that all ten supported harness targets get the right file at the right path. Four of them have also been verified by hand, by running the harness and confirming the skill changed its behavior: Claude Code, VS Code Copilot, Cursor, and Codex/opencode. The record, with versions and dates, is in [`docs/harness-verification.md`](docs/harness-verification.md).

## Using it

Most of the time you don't invoke it. With the skill installed, any code-writing task triggers it, and the agent writes, self-checks, and then tells you what it deliberately left alone. To ask for a review, say so in plain words, such as "review this file for readability". The agent replies with findings in a fixed format.

```text
[N3] src/api/client.ts:42  Name has no unit
  const timeout = 30;
  → rename to `timeoutSecs` (or `timeoutMs` if milliseconds)
```

The Claude Code plugin adds two conveniences on top:

- **`/taorc-review [file|directory|PR#]`** reviews the current uncommitted diff by default, or the path or pull request you name. Autocomplete lists it under the plugin's namespace as `/taorc:taorc-review`, and both names run it.
- **The "Readable Code Review" output style** keeps review responses to findings and a short closing note, with no preamble. Turn it on with `/output-style taorc:Readable Code Review`, or pick it under **Output style** in `/config`. It changes only how review findings are laid out, not how Claude writes code.

## Results

These are the PRD's success metrics. M1 to M4 come from the latest benchmark run, with Claude Opus 5 and GPT-5.1 each tested with and without the skill. The full method, per-scenario tables, raw completions, and caveats are in [`evals/results/2026-09-03/RESULTS.md`](evals/results/2026-09-03/RESULTS.md).

| Metric                                                     | Target                       | Result                                                                    |
| ---------------------------------------------------------- | ---------------------------- | ------------------------------------------------------------------------- |
| M1 — `taorc-lint` findings per 100 lines, vs. no skill     | ≥ 60% fewer                  | **75.5% fewer** pooled (Claude 78.2% fewer)                               |
| M2 — blind judge prefers the skill's version               | ≥ 70%                        | **68.4%** as run; 72.2% excluding one unparseable pair                    |
| M3 — diff growth on bugfix tasks, vs. no skill             | ≤ 10%                        | **GPT +3.0%**; Claude −11.6% after correcting a parse failure             |
| M4 — skill activates on code tasks / falsely on others     | ≥ 90% / ≤ 10%                | **100% / 0%** on a 100-prompt suite                                       |
| M5 — linter false positives on the fixture suite           | ≤ 5%                         | **0%**                                                                    |
| M6 — `SKILL.md` size                                       | ≤ 5,000 tokens               | **4,234 tokens**                                                          |
| M7 — harnesses covered                                     | ≥ 10 automated / ≥ 4 by hand | **10 / 4**                                                                |

Two caveats matter. M2 and M3 each miss their target as scored, and both misses trace to a single completion that came back as a unified diff, which the scorer cannot parse yet. The `RESULTS.md` shows the correction and the reasoning, and the as-scored numbers are published anyway. Also, M1's reduction on GPT is not measurable, because GPT's baseline produced only one lint finding in 314 lines. The open-weights slot that would validate the plain system prompt has not been run yet.

## Linting

`skills/readable-code/scripts/taorc_lint.py` is a stdlib-only Python script that checks code against the nine catalog rules a pattern match can catch with high precision (`C1`, `C4`, `N1`, `N3`, `N11`, `S7`, `T3`, `X7`, `X8`). It needs no install step beyond [ast-grep](https://ast-grep.github.io/), which it shells out to. Without ast-grep on `PATH`, it prints an install hint and exits `0` rather than failing a build over a missing optional tool.

```console
$ python skills/readable-code/scripts/taorc_lint.py --changed
[N3] src/api/client.ts:42  Name has no unit
  const timeout = 30;
  → add a unit or format suffix (for example _ms, _secs, _bytes) to the name
```

The linter covers Python and TypeScript/JavaScript only in v1. Structural checks such as nesting depth, function length, and branch complexity are out of scope on purpose, because mainstream linters already do them well. [`lint/configs/ruff.toml`](lint/configs/ruff.toml) and [`lint/configs/eslintrc.readability.json`](lint/configs/eslintrc.readability.json) are ready-to-merge snippets that turn those checks on in your own linter. Neither file is installed or run by taorc. Copy the rules you want.

## Use it alongside a clean-code skill

taorc is a complement to [`clean-code-skills`](https://github.com/btseee/clean-code-skills), not a replacement for it. Use both.

`clean-code-skills` works at the design level, drawing on *Clean Code*: responsibilities, function and class boundaries, error-handling strategy. taorc works one level down, on the line a reader is looking at right now: whether this name is ambiguous, whether this comment repeats the code, whether this condition needs a name. The two rarely give conflicting advice, because they are answering different questions.

|                    | `clean-code-skills`                           | taorc                                                      |
| ------------------ | --------------------------------------------- | ---------------------------------------------------------- |
| Source             | *Clean Code* (Martin, 2008)                   | *The Art of Readable Code* (Boswell & Foucher, 2011)       |
| Unit of advice     | "This module has mixed responsibilities"      | "This name is ambiguous"; "this comment restates the code" |
| Typical change     | A restructuring                               | A rename, a deleted comment, an extracted variable         |
| Evidence           | —                                             | A published cross-model benchmark and a bundled linter     |

## Scope limits

taorc is deliberately narrow. It is not:

- A formatter. It defers to Prettier, Black, gofmt, rustfmt, or whatever your project runs, on whitespace, line breaks, and casing.
- A correctness, security, or performance reviewer.
- An architecture or design-pattern skill. See the previous section.
- A service. There is no proxy, daemon, runtime, or hosted component, only files on disk. It sends no telemetry.

Known gaps in v1: the linter covers only Python and TypeScript/JavaScript, the language-specific guidance covers six languages (Python, TypeScript/JavaScript, Go, Rust, Java, C#), and the benchmark has not yet run against an open-weights model. The [PRD](v1-product-requirements-doc.md) §4 lists the full goals and non-goals, and [`CHANGELOG.md`](CHANGELOG.md) lists what shipped.

## Contributing

New rules are welcome if they clear a specific bar: a frontier model must not already follow the rule reliably, a human reviewer must be able to check it, and no existing rule may cover it. [`CONTRIBUTING.md`](CONTRIBUTING.md) explains the bar, the stable-ID policy, and the copyright rule every contribution has to follow.

## Legal and copyright

This project is **unofficial** and not affiliated with or endorsed by O'Reilly Media or the authors. No text from *The Art of Readable Code* appears anywhere in this repository. Every rule statement, rationale, and code example is original, and each rule cites the chapter it draws on so readers can go to the source rather than read a summary.

If this project is useful to you, please buy the book: [*The Art of Readable Code*](https://www.oreilly.com/library/view/the-art-of/9781449318482/), Dustin Boswell and Trevor Foucher, O'Reilly Media, 2011, ISBN 978-0-596-80229-5. It explains the reasoning behind these rules far better than a rule catalog can.

## License

MIT. See [`LICENSE`](LICENSE).
