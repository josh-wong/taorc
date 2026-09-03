# AI assistant configuration

This file contains configuration and guidelines for AI assistants when working on this repository. It follows the [AGENTS.md](https://agents.md) convention and is read directly by GitHub Copilot; Claude Code reads it via the `@AGENTS.md` import in `CLAUDE.md`.

## Important notes

**GIT SAFETY:** NEVER force push to any branch. Force pushes can:

- Overwrite remote history and cause data loss.
- Accidentally commit files that should be in .gitignore.
- Invalidate pull requests and break collaboration.

Always use `git push` without `--force` or `--force-with-lease`. If you need to undo work, use `git revert` instead of `git push --force` or `git push --force-with-lease`.

## Documentation references

For detailed information about this project, refer to the following internal documentation. Delete any row that doesn't apply and add rows for docs this project actually has.

- **Repository overview:** See `README.md` for a general project description.
- **Product or design docs:** `v1-product-requirements-doc.md` (the PRD — problem, requirements, success metrics, decisions) and `v1-design-doc.md` (the design doc — repo layout, catalog schema, distribution mechanism, CI gates, milestones). Read the design doc before touching `catalog/`, `scripts/build.py`, `scripts/validate.py`, or any generated adapter file.

- **Controlled vocabularies:** `catalog/rules.yaml` is the single source of truth for every rule ID (`N7`, `C4`, `X2`, etc. — see `v1-design-doc.md` §3). IDs are **permanent once shipped and never reused**: a withdrawn rule gets `deprecated: true` and a `superseded_by` field, never a renumbering. Any ID cited in `SKILL.md`, a reference file, the linter, or an eval scorer must already exist in the catalog — CI fails otherwise.

- **Any other related docs:** Refer to any other docs in the `docs/` folder for additional architecture context, if present. `docs/harness-verification.md` records the manual per-harness smoke tests (see PRD metric M7).

## Repository overview

taorc is a portable agent skill that teaches AI coding agents to write, comment, and review code according to *The Art of Readable Code* (Boswell & Foucher, O'Reilly 2011). It ships as an [Agent Skills](https://agentskills.io/specification) package, plus generated adapters for around ten other agent harnesses, plus a plain system-prompt fallback for any LLM with no skill runtime at all.

### Key components

- `catalog/rules.yaml` — the machine-readable registry of every rule ID; the join key referenced by everything else.
- `skills/readable-code/` — the hand-written skill (`SKILL.md` + `references/`), plus the bundled `taorc-lint` checker under `scripts/` so it travels with every install method.
- Generated adapters — managed blocks and manifests for `AGENTS.md`/`CLAUDE.md`/`GEMINI.md` readers, Cursor, GitHub Copilot, Cline, Windsurf, and others, built by `scripts/build.py` from `templates/agent-block.md` and the catalog.
- `prompts/system-prompt.md` and `system-prompt-mini.md` — hand-written, token-budgeted fallback prompts for harnesses with no skill runtime.
- `evals/` — the cross-model benchmark harness (trigger suite, scenario suite, automated + LLM-judge scoring) that measures the PRD's success metrics.

### Architecture patterns

- **The rule ID is the join key.** It appears in the catalog, the skill prose, linter output, eval scores, and review findings. An ID cited anywhere that isn't defined in `catalog/rules.yaml` is a bug, not a style nit.
- **Generation policy.** Generate only what must be byte-identical across adapters (managed blocks, version fields, manifest metadata) via `scripts/build.py`. Hand-write everything that must read well — `SKILL.md`, `references/`, `prompts/*.md` are never generated. Never add a code path that auto-generates skill prose or the fallback prompts.
- **Rule IDs never move.** Deprecate with `deprecated: true` and `superseded_by`; never renumber or reuse an ID — every review comment, eval result, and lint suppression ever written cites one.
- **Catalog precedence, in order:** correctness beats readability; project convention beats catalog preference; reader comprehension time beats brevity or rule-count compliance; the project's own formatter wins every whitespace argument; when two catalog rules conflict, prefer the one that reduces time-to-understand for an unfamiliar reader.
- **No text from the book, ever.** See "Legal and copyright considerations" below — this is the constraint most likely to be violated by accident.

## Development workflow

Follow these guidelines to maintain code quality and project consistency.

### Issue creation guidelines

When creating a GitHub issue, provide clear descriptions of bugs or feature requests including steps to reproduce, expected vs. actual behavior, environment details, and relevant logs.

For features, describe the user need and reference the relevant PRD requirement ID (e.g. `R6.1`, `R2.3`) or catalog rule ID (e.g. `N7`) when the request maps to one. Propose a solution.

Never omit a section; write "N/A" explicitly when one doesn't apply.

### Model and effort selection

Before starting work on an issue, check the issue description for **Model** and **Review Effort** annotations. If specified, switch to the recommended model and effort level before asking the AI to begin work. Examples:

- "Model: Sonnet | Review Effort: medium" → Switch Claude Code to Sonnet, then start the task
- "Model: Opus | Review Effort: high" → Switch to Opus for deeper reasoning

This ensures the AI has appropriate reasoning capacity and cost efficiency for the task scope.

### Commit practices

- Write clear, descriptive commit messages that start with an uppercase verb (for example, "Add breed picker", "Fix age staleness calculation", "Update README").
- Do not use Conventional Commits format (`docs(02): ...`, `feat: ...`). Verb-first is the only style used in this repository.
- Reference issue numbers when commits relate to a specific issue.
- Avoid auto-committing large or non-trivial changes; always give the reviewer the opportunity to inspect changes before committing.
- **AI co-authorship:** When an AI agent (Claude, GitHub Copilot, Qwen, Ollama, etc.) authors or co-authors a commit, include a co-author line with the agent name and model used. Format: `Co-Authored-By: [Agent Name] ([Model]) <noreply@[provider].com>`. Examples:
  - `Co-Authored-By: Claude Sonnet <noreply@anthropic.com>`
  - `Co-Authored-By: GitHub Copilot (GPT-5.6 Terra) <223556219+Copilot@users.noreply.github.com>`
  - `Co-Authored-By: Qwen 3.5 9B <noreply@qwen.local>`
  - `Co-Authored-By: Meta Llama3.2 3B <noreply@ollama.local>`

  This maintains clear attribution in git history and distinguishes AI-assisted work from human-only changes.

### Branch management

- Create feature branches from `main` using `feature/description` or `fix/description`.
- Keep branches focused on single features or bug fixes.

### Pull request creation guidelines

When creating a pull request, **read and follow the template in `.github/pull_request_template.md` exactly**. This is critical to ensure consistency.

PR titles follow the same verb-first convention as commit messages (for example, "Add breed picker", "Fix age staleness calculation") rather than Conventional Commits format, since GitHub uses the PR title as the default squash-merge commit message.

**Required process:**

1. Read the actual template file from `.github/pull_request_template.md` every time (do not rely on memory)
2. Include every section from the template in the PR body, in exact order
3. Include all checkboxes from every checklist section
4. Do not skip or omit sections

**For each checklist item:**

- Check `[x]` if completed
- Leave `[ ]` if not applicable or incomplete
- If truly not applicable, write "not applicable – [brief reason]" after the checkbox instead (e.g., "not applicable – docs only")
- Never omit checkbox items; always show the full checklist for visibility

**General guidelines:**

- Never abbreviate or paraphrase template sections
- Always include the full checklist with all items visible
- Fill out every section in the template

### Code standards

Follow idiomatic conventions for Python 3.10+ (stdlib-only for anything shipped inside `skills/readable-code/scripts/` — no install step should be required to run `taorc_lint.py`) and for the YAML/Markdown that make up the catalog and skill content. Since the product's own thesis is code readability, hold this repo's own scripts, examples, and docs to the catalog's own bar — dogfooding failures here undercut the project's credibility more than they would in an unrelated repo.

## Legal and copyright considerations

This project's entire product is built directly against a copyrighted book (*The Art of Readable Code*, Boswell & Foucher, O'Reilly 2011), which makes this the single hard constraint an AI assistant is most likely to violate by accident — not an aside.

- No text from the book may ever be committed, in any file: not in `catalog/rules.yaml`, not in `references/`, not in `examples/`, not in `prompts/`, and not in a commit message or PR description. Rule statements, rationale, and every code example must be original prose and original code.
- Ideas, methods, and rule taxonomies are not copyrightable — their expression is. Capture the book's ideas in original words and cite the chapter number so a reader can go to the source; never summarize a chapter in enough detail to substitute for reading it.
- Every example in `examples/before-after.md` must be original: written for this repo, never adapted from the book's own example, and ideally in a different language or domain than the point the book uses it to illustrate.
- Working notes taken while reading the book belong in `notes/`, which is gitignored and must never enter a commit or release artifact.
- Ship the disclaimer (unofficial, not affiliated with or endorsed by O'Reilly Media or the authors) and the recommendation to buy the book in `README.md` — do not remove either.
- The project name `taorc` is deliberately not the book's title, to reduce trademark surface; keep the skill `description` describing function, not leaning on the title.

## Formatting rules

This section outlines the essential formatting standards, primarily for documentation.

### Structure and spacing

Add empty newlines after all headings. Add empty newlines before all lists. Never stack headings - always include descriptive text between them that explains what follows. Add an empty newline at the end of the document. All files must end with a newline character.

Sections must not contain only an admonition, code block, image, table, or tab - always include descriptive text after the heading. Always add an empty newline after the opening of an admonition and before the closing of an admonition. Don't add empty newlines after steps in numbered lists.

### Headings and capitalization

Never end headings with colons. Never end a sentence with a colon if what follows next is a heading. Don't use `Introduction` or `Overview` headings since it should be obvious that the body text immediately below the heading 1/title describes what the doc is about.

Use sentence-style capitalization for all headings and bold-style headings (only capitalize the first word and proper nouns).

### Lists and formatting

Avoid excessive use of bulleted lists and numbered lists. For bulleted items with colons, use `:**` not `**:` (for example, `**Item:**`). Align all rows in Markdown tables for readability in source code.
<!-- taorc:begin v0.1.0 -->
## Readable code (taorc)

Write code so the next reader understands it in the least time. Full rules:
first existing path wins—`.claude/skills/readable-code/SKILL.md`,
`.agents/skills/readable-code/SKILL.md`, `.github/skills/readable-code/SKILL.md`,
`skills/readable-code/SKILL.md`. Read it before non-trivial work.

### Always

- Name the thing, not its shape. No `data`, `result`, `handler`, `helper`. (N1, N9)
- Put the unit in the name: `timeoutSecs`, not `timeout`. (N3)
- Comment *why*, never *what*. If a comment restates the line below it, delete it. (C1)
- No plan narration ("Step 1:"), no banner comments, no emoji in code. (X7, X8)
- Handle the trivial or invalid case first and return immediately. (F2, F5)
- Treat one more level of nesting as a signal to restructure. (F6)
- Name a subexpression when a condition runs past three terms. (E1)
- Inline a name used once that says no more than the expression it replaced. (V1)
- For a function you add, say what it returns on empty or boundary input and when it raises. (C14)
- One task per block. If describing it needs "and", split it. (S3)
- Test names say the scenario and the expected result. (T3)
- A suite you were asked to write covers every distinct outcome, not only the cases the task listed. (X1)

### Never

- Widen the diff to satisfy a readability rule. Mention it instead. (X1)
- Override a project's existing vocabulary or conventions with these. (X2)
- Rename a public or exported symbol, a parameter name included, unless asked. (X3)
- Mix a readability change and a behavior change in one step. (X4)
- Argue with the formatter. It wins. (X5)
<!-- taorc:end -->
