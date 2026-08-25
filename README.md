# taorc

taorc is a portable AI agent skill that teaches coding agents to write, comment, and review code according to the principles of *The Art of Readable Code* (Boswell & Foucher, O'Reilly, 2011).

Agents optimize for producing something that satisfies a request and passes review at a glance. This skill optimizes for the thing the book argues actually matters: minimizing the time it takes another person to understand the code. It targets the specific readability tells that show up in LLM-authored code — narration comments, empty-word names like `data` and `handler`, unit-free numbers, deep nesting, and the rest — rather than restating generic clean-code advice.

## Status

This repository is in early development. The [product requirements doc](v1-product-requirements-doc.md) and [design doc](v1-design-doc.md) are approved and describe the full v1 scope: an 85-rule catalog, a hand-written skill package, generated adapters for around ten agent harnesses, a stdlib-only linter (`taorc-lint`), and a published cross-model eval suite. The catalog, the skill package, and the linter are complete; the generated adapters, the installers, and the eval suite have not shipped yet, so there is still no packaged install from this repo today. Once the adapters and installers exist, this section will be replaced with install instructions and benchmark results.

## Why this and not a general clean-code skill

Several skills already cover general clean-code advice (see the prior-art survey in the PRD, §3). taorc is narrower and more specific on purpose:

| | General clean-code skills | taorc |
| --- | --- | --- |
| Source | Ad hoc, or a different book (e.g. *Clean Code*) | *The Art of Readable Code*, cited by chapter |
| Unit of advice | Structural — "this module has mixed responsibilities" | Local — "this name is ambiguous," "this comment restates the code" |
| Scope of change | Often a refactor | Usually a rename, a deleted comment, an extracted variable |
| Objective evidence | Rarely measured | Published before/after benchmark, cross-model |

They're complements, not substitutes — a design-level skill and a naming/comments/control-flow-level skill compose well together.

## Linting

`skills/readable-code/scripts/taorc_lint.py` is a stdlib-only Python script that checks code against the nine catalog rules a pattern match can catch with high precision — see `v1-design-doc.md` §8 for the full rule table and the C1 scoring algorithm. It ships inside the skill directory, so it travels with every install method and needs no separate install step of its own beyond [ast-grep](https://ast-grep.github.io/), which it shells out to. Without ast-grep on `PATH`, it prints an install hint and exits `0` rather than failing a build over a missing optional tool.

```console
$ python skills/readable-code/scripts/taorc_lint.py --changed
[N3] src/api/client.ts:42  Name has no unit
  const timeout = 30;
  → add a unit or format suffix (for example _ms, _secs, _bytes) to the name
```

Covers Python and TypeScript/JavaScript only for v1. Structural checks — nesting depth, function length, boolean/branch complexity — are out of scope on purpose (a mainstream linter already does them well); `lint/configs/ruff.toml` and `lint/configs/eslintrc.readability.json` are recommended, ready-to-merge snippets that enable those checks in your own project's linter. Neither file is installed or executed by this repo or by any agent following the skill — copy the rules you want into your own config.

## Non-goals

- Not a formatter — defers to Prettier/Black/gofmt/rustfmt on whitespace, line breaks, and casing.
- Not a correctness, security, or performance reviewer.
- Not an architecture or design-pattern skill.
- No proxy, daemon, runtime, or hosted service — files on disk only.
- No telemetry, no phone-home.

See the [PRD](v1-product-requirements-doc.md) §4 for the full goals and non-goals.

## Legal and copyright

This project is **unofficial** and not affiliated with or endorsed by O'Reilly Media or the authors. No text from *The Art of Readable Code* appears anywhere in this repository — every rule statement, rationale, and code example is original, chapter-cited so readers can go to the source rather than summarized or reproduced. If this project is useful to you, consider buying the book: *The Art of Readable Code*, Dustin Boswell and Trevor Foucher, O'Reilly Media, 2011, ISBN 978-0-596-80229-5.

## License

MIT — see [`LICENSE`](LICENSE).
