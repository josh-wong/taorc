---
name: readable-code
description: >
  Write, comment, and review code so the next reader understands it in the least
  time. Applies on any code-writing, editing, refactoring, or code-review task,
  and specifically when naming things, writing or editing comments and
  docstrings, simplifying conditionals, or writing tests. Also use when asked to
  "make this readable", "clean up the comments", "review this for readability",
  "improve these names", "humanize this code", "make it look like a person wrote
  it", or when removing AI-generated code tells such as step-by-step narration
  comments, banner comments, boilerplate that reads as machine-written, or empty
  names like data, result, and handler. Based on The Art of Readable Code
  (Boswell & Foucher).
license: MIT
metadata:
  version: "0.1.0"
  source: "The Art of Readable Code, Boswell & Foucher, O'Reilly 2011"
  homepage: "https://github.com/josh-wong/taorc"
---

# Readable code

Code is read far more often than it is written, and the reader is usually a
stranger — including you, months later. So the measure that matters is how long
someone unfamiliar with this code needs to understand it well enough to change
it safely. Shorter is not the goal; faster to understand is.

That measure binds you more tightly than it binds a human author. You produce
code quickly, in volume, with no memory of writing it and no stake in
maintaining it. Every habit that makes generated code recognizable — narrating
your own plan in comments, naming things `data` and `result`, wrapping a single
call in a helper "for reusability" — costs a future reader time. Treat naming
and commenting as decisions you make while writing, not as a pass you do
afterward.

The correction runs both ways, and overshooting costs the same reader the same
time. Deleting the docstring that told a caller what comes back on empty input,
or naming a subexpression that already read clearly, is not a cleaner file. It
is a different kind of noise.

## When this applies

Infer the mode from the task. Never ask which one to use.

| Mode       | Inferred from                                                        | Behavior                                                                                   |
| ---------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `write`    | Default — any code-writing task                                      | Apply the catalog while generating. No unrelated cleanup. Self-check before presenting.    |
| `review`   | "review", "audit", "check", `/taorc-review`, a diff or PR in context | Findings only. Emit the finding format below. Never modify files.                          |
| `refactor` | "clean up X", "make X readable", "improve the names in X"            | Behavior-preserving edits to the named target only. Report what changed and what you left. |

If the mode is genuinely ambiguous, default to `write` for new code and
`review` for code that already exists.

## Operating loop

Follow these five steps in `write` and `refactor` mode. Review mode skips them
— steps 2 and 4 modify files — and follows `references/review-checklist.md`.

```text
1. READ LOCAL CONTEXT   Before writing: the file's existing naming vocabulary,
                        its comment density, the formatter and linter config
                        (.prettierrc, pyproject.toml, .editorconfig), the test
                        style. Local convention outranks this catalog (X2).

2. WRITE                Apply the catalog. Naming and comments are decisions,
                        not decoration — make them while writing, not after.

3. SELF-CHECK           Run the checklist below. Not optional; this is where
                        most of the gain comes from.

4. VERIFY               Look for scripts/taorc_lint.py under each of
                        .claude/skills/readable-code/,
                        .agents/skills/readable-code/,
                        .github/skills/readable-code/, skills/readable-code/,
                        and run the first one that EXISTS AS A FILE:
                        python <root>/scripts/taorc_lint.py --changed.
                        A directory alone is not enough — it can exist without
                        the linter in it. If no such file exists, skip this
                        step; do not search further and do not install it.
                        Fix findings, re-run, repeat until clean — or until a
                        finding is a justified false positive. Say which.

5. REPORT               State what you deliberately did NOT change, and why.
                        This is what keeps diffs narrow (X1).
```

Step 5 is load-bearing. Saying "I noticed `utils.py` has become a junk drawer
and left it alone" is the sanctioned way to notice a problem without widening
your diff to fix it.

## Rule catalog

Every rule below has a permanent ID. Cite IDs from this table and no others;
if no rule fits an observation, report it as prose with no ID (`X6`).

Principles that the rest of the catalog serves.

| ID   | Rule                                                                       |
| ---- | -------------------------------------------------------------------------- |
| `P1` | Optimize every decision for how fast an unfamiliar reader can follow it    |
| `P2` | Fewer lines is usually good, but it is not the same goal as readability    |
| `P3` | Treat a readability-versus-other-goals conflict as a signal to look harder |

Names carry most of the meaning a reader gets for free.

| ID    | Rule                                                                          |
| ----- | ----------------------------------------------------------------------------- |
| `N1`  | Prefer a specific word over a vague one when a precise word exists            |
| `N2`  | Reserve placeholders like `tmp` and `retval` for genuinely short-lived values |
| `N3`  | Put units, formats, or encodings in the name when the value could be misread  |
| `N4`  | Mark values that are dangerous or need special handling in the name           |
| `N5`  | Scale name length to the size of the scope the name lives in                  |
| `N6`  | Avoid an abbreviation a new teammate would not recognize                      |
| `N7`  | Use the codebase's naming format consistently to convey meaning               |
| `N8`  | Remove words that add no information, but keep the meaning precise            |
| `N9`  | Prefer a concrete name that describes what an entity actually does            |
| `N10` | Name booleans so they read as a yes-or-no question                            |
| `N11` | Avoid negation in boolean names                                               |
| `N12` | Use `first`/`last` for an inclusive range, `begin`/`end` for a half-open one  |
| `N13` | Prefix a hard limit with `max` or `min` rather than using a bare noun         |
| `N14` | Avoid a name whose common meaning could be read two different ways            |
| `N15` | Match users' expectations for conventional method names                       |
| `N16` | Actively look for ways a name could be misunderstood                          |

Aesthetics are about skimmability, not taste. The project's formatter wins any
whitespace argument (`X5`).

| ID   | Rule                                                                           |
| ---- | ------------------------------------------------------------------------------ |
| `A1` | Give structurally similar code the same visual shape, then make it compact     |
| `A2` | Use a helper method when repeated detail prevents a consistent layout          |
| `A3` | Align repeated similar lines into columns when it improves skimming            |
| `A4` | Give unordered items a deliberate order, then repeat it everywhere they appear |
| `A5` | Organize declarations into logical blocks                                      |
| `A6` | Break large blocks into logical paragraphs                                     |
| `A7` | Prefer consistency over the personally preferred style                         |

A comment's job is to carry what the code cannot.

| ID    | Rule                                                                         |
| ----- | ---------------------------------------------------------------------------- |
| `C1`  | Do not write a comment that only restates what the code already says         |
| `C2`  | Fix a bad name instead of writing a comment to compensate for it             |
| `C3`  | Use comments to record insight the code by itself cannot convey              |
| `C4`  | Mark known shortcuts and unfinished work with a searchable marker            |
| `C5`  | Explain a constant's value when the number itself doesn't explain the choice |
| `C6`  | Comment where a careful reader would stop and ask why                        |
| `C7`  | Advertise a likely pitfall before a caller discovers it the hard way         |
| `C8`  | Give a complex file or class a short comment stating its overall purpose     |
| `C9`  | Summarize a multi-step block with one comment instead of narrating each line |
| `C10` | Write a rough comment early, then make it precise                            |
| `C11` | Keep comments compact and information-dense                                  |
| `C12` | Avoid a pronoun a reader would have to work to resolve                       |
| `C13` | Polish comments into direct, precise sentences                               |
| `C14` | Describe a function's behavior precisely, including its corner cases         |
| `C15` | Show a corner case with a worked input and output rather than describing it  |
| `C16` | State the intent behind the code, not just an account of its mechanics       |
| `C17` | Label a mysterious function argument inline at the call site                 |
| `C18` | Reach for an established term of art instead of describing it from scratch   |

Sixteen of these eighteen rules ask you to write or sharpen a comment. Only
`C1` deletes one, and only `C2` trades one for a better name. A file you left
with fewer comments than you found has not automatically improved.

Control flow should read in the order the reader thinks.

| ID   | Rule                                                                            |
| ---- | ------------------------------------------------------------------------------- |
| `F1` | Put the value being examined on the left and what it is measured against right  |
| `F2` | Put the positive, the simpler, or the more interesting case first               |
| `F3` | Use a conditional expression only when it is quicker to understand than if/else |
| `F4` | Avoid a loop whose condition is only visible after its body                     |
| `F5` | Handle the trivial and invalid cases up front and return immediately            |
| `F6` | Keep nesting shallow, and treat one more level as a signal to restructure       |
| `F7` | Use constructs that break linear execution order sparingly                      |

Break big expressions into pieces a reader can hold in mind.

| ID   | Rule                                                                          |
| ---- | ----------------------------------------------------------------------------- |
| `E1` | Name a subexpression with a variable that says what it is                     |
| `E2` | Give a recurring condition a short name even when it needs no explanation     |
| `E3` | Rewrite a negated group into whichever form states the idea more directly     |
| `E4` | State a condition directly instead of comparing against a boolean or a length |
| `E5` | Break a large expression into named steps rather than one clever line         |
| `E6` | Do not use short-circuit operators to make one line do two jobs               |

A name earns its line by saying more than the expression it replaced. When it
does not, `V1` takes it back out — `E1` and `V1` are the two halves of one
judgment, not rules that disagree.

Every live variable is something the reader has to track.

| ID   | Rule                                                                  |
| ---- | --------------------------------------------------------------------- |
| `V1` | Remove a variable that only carries a value from one line to the next |
| `V2` | Narrow each variable's scope to the smallest region that needs it     |
| `V3` | Declare a variable immediately before its first use                   |
| `V4` | Prefer values assigned once over variables that change                |
| `V5` | Exit a loop directly instead of steering it with a flag variable      |

Structure is about what belongs together and what does not.

| ID   | Rule                                                                                |
| ---- | ----------------------------------------------------------------------------------- |
| `S1` | Extract a self-contained subproblem into a function describable on its own          |
| `S2` | Keep general-purpose code apart from project logic; name its home for what it holds |
| `S3` | Make a block do one task at a time                                                  |
| `S4` | Describe what the code must do in plain language, then make the code follow it      |
| `S5` | Question the requirement before writing code to satisfy it                          |
| `S6` | Do not add an abstraction until a second caller needs it                            |
| `S7` | Delete code that cannot change the outcome                                          |
| `S8` | Know the standard library well enough to reach for it before rewriting it           |
| `S9` | Wrap an awkward interface in the one you wish it had                                |

A test is read most carefully at its least convenient moment.

| ID   | Rule                                                                            |
| ---- | ------------------------------------------------------------------------------- |
| `T1` | Make the values a test is actually about visible at a glance                    |
| `T2` | Choose the simplest input that still exercises the behavior under test          |
| `T3` | Name a test for the situation it sets up and the outcome it expects             |
| `T4` | Make a failing assertion say what went wrong without a debugger                 |
| `T5` | Keep each test about one behavior                                               |
| `T6` | Treat hard-to-test code as a design signal, without distorting design for tests |

None of these rules is about how much a suite covers. `T2` asks for the simplest input
that exercises a behavior, not for fewer behaviors, and `X1` bounds which code you
touch, not how many outcomes your tests pin down. When the task is to write tests, the
distinct outcomes are the task — dropping one to keep the file short is not brevity, it
is the task left undone.

Guardrails govern how you apply everything above. They outrank the rest when
they conflict, because a correct rule applied too broadly still costs a
reviewer time.

| ID   | Rule                                                                            |
| ---- | ------------------------------------------------------------------------------- |
| `X1` | Do not widen a diff to satisfy a readability rule                               |
| `X2` | Match the file's existing vocabulary and conventions over this catalog          |
| `X3` | Never rename a public or exported symbol unless asked                           |
| `X4` | Keep readability changes and behavior changes in separate steps                 |
| `X5` | Leave whitespace, line length, and casing to the project's formatter and linter |
| `X6` | Cite only rule IDs that exist in this catalog; report anything else as prose    |
| `X7` | Do not narrate your own plan or process in code comments                        |
| `X8` | Do not add banner comments, section dividers, or emoji to code                  |

`X1` bounds which code you touch, not how you structure the code you were asked
to change. In `refactor` mode the named target is the task: collapsing its
helpers back into one function to keep the diff short is not `X1` being
respected, it is the task left undone.

## Precedence

When two rules point in different directions, resolve in this order. Earlier
entries win.

1. Correctness beats readability. A clearer version that changes behavior is not an improvement.
2. Project convention beats catalog preference.
3. Reader comprehension time beats brevity, cleverness, and rule-count compliance.
4. The project's formatter and linter configuration wins every whitespace argument.
5. When two catalog rules conflict, prefer the one that reduces time-to-understand for a reader unfamiliar with the code.

## Self-check

Run this before presenting any code. The questions are ordered by how often
they catch something.

1. Does any comment restate the line below it, or narrate your plan — "Step 1", "First, we"? Delete it. (`C1`, `X7`)
2. Is any name an empty word — `data`, `result` — or a role word — `handler`, `manager`? (`N1`, `N9`)
3. Would a new reader know the unit of every number you named? (`N3`)
4. For each function you added, can a caller tell what it returns on empty or boundary input and when it raises? Do not document one the task did not change. (`C14`, `X1`)
5. Is any non-obvious decision left unexplained? Add the *why*. (`C6`)
6. Did you introduce a name used once that says no more than the expression it replaced? Inline it. (`V1`)
7. Can a nested block become a guard clause, or a long condition a named one? (`F5`, `F6`, `E1`)
8. Does any function do more than one thing a one-sentence description covers? (`S3`)
9. Do your test names say the scenario and the expected result? If you wrote the suite, does each distinct outcome of the code under test have a case; if you were asked to add one test, did you add only that and note the rest? (`T3`, `X1`)
10. Did you change anything the task did not require — a signature, a behavior, a file? (`X1`, `X3`, `X4`)

## Reference map

Load a reference file when its trigger fires, not by default.

```text
references/comments.md         before writing or editing any comment or docstring.
references/naming.md           when naming a public API, when a name is contested
                               in review, or for any layout or alignment question
                               (the A rules live here).
references/control-flow.md     when a function exceeds two levels of nesting or a
                               condition exceeds three terms.
references/structure.md        before extracting a function or splitting a file.
references/tests.md            when writing or reviewing tests.
references/ai-code-tells.md    when asked to de-slop, humanize, or clean up
                               AI-generated code.
references/language-map.md     when the language is Go, Rust, Java, or C#.
references/review-checklist.md at the start of every review-mode task.
references/chapter-map.md      only when the user asks where a rule comes from. It
                               is attribution for humans, not working material —
                               never load it to decide how to write code.
```

## Finding format

Use this format in review mode, in refactor mode's change report, and when
reading `taorc-lint` output. One format means your own findings and the
linter's read the same way.

```text
[N3] src/api/client.ts:42  Name has no unit
  const timeout = 30;
  → rename to `timeoutSecs` (or `timeoutMs` if milliseconds)
```

The ID comes first because it is greppable and forces the finding to be
grounded in a real rule. Location second, so it is clickable. The matched
source third, which proves the finding is real. The fix last, imperative and
concrete — never "consider renaming".

Cite only IDs that appear in the catalog table above. If you cannot find a rule
that fits, say what you observed in plain prose and give it no ID. Inventing a
plausible-looking ID is worse than having none, because every ID in this
catalog is a permanent identifier that review comments and lint suppressions
are written against.
