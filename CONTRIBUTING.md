# Contributing to taorc

Thanks for helping. This guide covers the change people most often want to make, adding or changing a rule, and then the mechanics that apply to every pull request.

Two constraints override everything else here. Rule IDs are permanent once shipped. And no text from *The Art of Readable Code* may enter the repository in any form. Both are explained below, and a pull request that breaks either one cannot be merged, however good the rest of it is.

## Proposing a rule

Open an issue with the standard template before writing any code or YAML. Say what the rule asks a writer to do, show one original before/after pair, and say which chapter of the book the idea comes from. If it doesn't come from the book, explain why it belongs in the `X` guardrails, the only category that is entirely this project's own. The discussion on the issue decides whether the rule clears the bar. The pull request then only has to get the details right.

### The bar for a new rule

A rule must meet all three of these tests. Most proposals that fail do so on the first.

- **Non-obvious to a frontier model:** a current model, asked to write clean code with no skill loaded, does not already do this reliably. "Use descriptive names" fails this test, because every model already believes it. "Name an inclusive range's bounds `first` and `last`" passes, because models routinely get it wrong. The best evidence is a real completion, from an eval run or your own session, where a model broke the rule.
- **Checkable by a human reviewer:** two reviewers reading the same diff would agree on whether it breaks the rule, and the rule says what the fix is. "Prefer clarity" is not checkable. "A boolean name reads as a yes/no question" is.
- **Not a duplicate:** it is not already covered by an existing rule, a narrower case of one, or a restatement of one with different words. Search `catalog/rules.yaml` by idea, not by keyword. If your proposal sharpens an existing rule, propose an edit to that rule instead.

A rule that is true but rarely matters belongs in a reference file as guidance, not in the catalog. Every rule in the catalog costs every user context tokens on every code-writing task.

### Adding the rule

Once the issue is agreed, a new rule touches these files.

1. **`catalog/rules.yaml`:** add an entry with the next unused number in its category. Never reuse a number, even one whose rule was deprecated. Fill every field `catalog/schema.json` requires, and set `chapter:` to the book chapter the idea comes from (`0` for an `X` guardrail).
2. **`skills/readable-code/SKILL.md`:** add the rule to the catalog table. CI fails if a non-deprecated rule is missing from it. Keep `SKILL.md` within its 5,000-token and 500-line budget.
3. **The category's reference file** under `skills/readable-code/references/`: the rationale, an original example, and when *not* to apply the rule.
4. **`skills/readable-code/references/chapter-map.md`:** the ID-to-chapter row.
5. **`python scripts/build.py`:** regenerates the `.github/skills/` copy. Commit what it writes.

A rule that `taorc-lint` can check with high precision also needs ast-grep rule files for both languages and a positive and negative fixture for each. See `v1-design-doc.md` §8 before attempting one. A false positive in the linter costs more trust than a missed finding.

## Changing an existing rule

IDs never move. To withdraw a rule, set `deprecated: true` and `superseded_by:` to the rule that replaces it (if any), and leave the entry in place. Review comments, lint suppressions, and published eval results all cite IDs, and a renumbered or reused ID silently changes the meaning of every one of them.

Any change to a rule's `instruction` needs a fidelity re-check against its cited chapter before merge. Reread the chapter and confirm the new wording does not blur a distinction the book draws, or assert something the book does not. Say in the pull request that you did this.

A change to the skill's `description` frontmatter changes when the skill fires. Re-run the trigger suite (`evals/run_triggers.py`) and include the activation and false-fire rates in the pull request.

## Copyright

The book's ideas are not copyrightable, but its expression is. Everything committed here must be original prose and original code.

- Never copy, closely paraphrase, or "lightly edit" a sentence or code example from the book, in any file, commit message, issue, or pull request description.
- Write examples from scratch, in a different domain and ideally a different language from the one the book uses for the same point. Do not adapt the book's example.
- Cite a chapter number so readers can find the source. Do not summarize a chapter in enough detail to stand in for reading it.
- Keep reading notes in `notes/`, which is gitignored. Nothing in it may be committed.

If you are unsure whether something is too close, it is. Rewrite it from the idea, not from the text.

## Generated and hand-written files

`scripts/build.py` generates every file that must be byte-identical across harnesses: the managed blocks in `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursor/`, `.github/`, `.clinerules/`, and `.windsurf/`, the version field in each manifest, and the `.github/skills/readable-code/` copy. Edit the source (`templates/agent-block.md`, `VERSION`, or `skills/readable-code/`) and rerun the build. Never edit generated output by hand. CI rebuilds and fails on any difference.

Everything that must read well is hand-written and never generated: `SKILL.md`, the reference files, `prompts/`, the examples, and these docs.

## Development setup

taorc's scripts need Python 3.10 or later. The linter that ships inside the skill uses only the standard library. The build and validation scripts need a few packages.

```bash
pip install -r requirements-dev.txt
python scripts/build.py
python scripts/validate.py
python scripts/tests/test_installer.py -v
python evals/tests/test_score.py -v
python evals/tests/test_judge.py -v
```

`validate.py` is the same gate CI runs. It checks the catalog schema, that every cited rule ID exists, token budgets, version sync, the lint fixtures, and more. Run it before opening a pull request. CI also runs ruff over all Python and markdownlint over all Markdown.

## Pull requests

- Branch from `main` as `feature/<description>` or `fix/<description>`.
- Write commit messages and pull request titles that start with an uppercase verb, such as "Add N17 for …" or "Fix C1 false positive on …". The project does not use Conventional Commits.
- Fill out every section of `.github/pull_request_template.md`, keeping every checklist item, and mark the ones that do not apply.
- Keep a readability change and a behavior change in separate pull requests. The project holds itself to its own `X4`.
- If an AI agent wrote or co-wrote a commit, add a `Co-Authored-By:` line naming the agent and model.

## Releasing

Maintainers only. Releases follow semantic versioning, where a rule ID counts as public interface (see `CHANGELOG.md`).

1. In `CHANGELOG.md`, move the `[Unreleased]` entries under a new `## [X.Y.Z] - YYYY-MM-DD` heading dated the day you will tag, leave an empty `[Unreleased]` section above it, and update the link references at the bottom of the file. Copy the previous entry as the template: `###` section headings with the same emoji (Features, Improvements, Bug fixes, Documentation, Success metrics when there are eval results, Known limitations, Downloads), `*Nothing to list – …*` for an empty section, and a Downloads link to `taorc-skill-vX.Y.Z.zip`, the name the release workflow gives the asset.
2. Set the new version in `VERSION` and in `metadata.version` in `skills/readable-code/SKILL.md`, then run `python scripts/build.py`.
3. Merge to `main`, then push a `vX.Y.Z` tag right away: from the merge on, the installers on `main` download that tag by default and fail until it exists. The release workflow validates the tree, checks that the tag matches `VERSION`, builds the skill `.zip`, and publishes a GitHub release with that version's `CHANGELOG.md` section as its notes.
4. From a clean machine, confirm `npx skills add josh-wong/taorc` resolves and installs.
