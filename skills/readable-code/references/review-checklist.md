# Review checklist

Load this file at the start of every review-mode task.

Review mode produces findings and nothing else. Do not edit files, do not stage
changes, and do not offer a rewritten version of the file unless asked. A review
that quietly fixes things gives the author no chance to disagree, and it hides
the reasoning that made the change worth making.

## Scan order

Work in this order. It runs cheapest-first and it front-loads the findings that
turn out to matter most, so a review that gets cut short still delivered its
best material.

1. **Names.** Read every identifier the diff introduces or changes. Ask what a
   reader who has not seen this file would think each one holds. Empty words
   (`N1`), missing units (`N3`), role words (`N9`), negated booleans (`N11`),
   and range bounds (`N12`) are the highest-yield checks in any review.
2. **Comments.** Every comment: does it restate the line below it (`C1`), or
   compensate for a name that should be fixed instead (`C2`)? Then the inverse
   and more important question — where would a careful reader stop and ask
   "why?", and is that answered (`C6`)?
3. **Control flow.** Nesting deeper than two levels (`F6`), conditions with
   more than three terms (`E1`), negated conditions that would read better
   inverted (`E3`), loops steered by a flag (`V5`).
4. **Structure.** Does each function do one thing (`S3`)? Is there an
   abstraction with a single caller (`S6`), code that cannot affect the outcome
   (`S7`), or a hand-rolled version of something the standard library provides
   (`S8`)?
5. **Tests.** Do the names say the scenario and the expectation (`T3`)? Would a
   failure message identify the problem without a debugger (`T4`)?
6. **Whole-diff questions.** These have no single line to attach to: does the
   diff do one job (`X4`), is anything in it unrelated to the stated task
   (`X1`), and does it introduce vocabulary the rest of the file does not use
   (`X2`)?

## What not to report

The fastest way to make a readability review worthless is to make it long. Four
categories to leave out.

**Anything the formatter owns.** Indentation, line length, quote style, trailing
commas, import order. If the project runs a formatter, its configuration is the
answer and your opinion is noise (`X5`, and precedence entry 4).

**Preferences the project has already settled.** If the file consistently uses
a convention this catalog would not have chosen, the file wins (`X2`, precedence
entry 2). Say so once if it is genuinely harmful; otherwise match it and move
on.

**Findings with no fix.** "This function is confusing" is not a finding. If you
cannot state the concrete change, you have an impression, not a review.

**Rules satisfied at the cost of comprehension.** Precedence entry 3 is explicit
that reader comprehension time beats rule-count compliance. A finding that would
make the code harder to follow is a finding you should drop, even when a rule
technically supports it.

## Severity

Use `error`, `warning`, and `suggestion` — the same three the catalog's
`severity` field carries and the only three `taorc-lint` emits. Do not invent a
fourth level. A finding that fits none of these is one to reconsider, not
relabel.

| Severity   | Means                                            | Example                                        |
| ---------- | ------------------------------------------------ | ---------------------------------------------- |
| error      | Leads to broken work, not merely slow reading    | `X3` on an unrequested rename of a public API  |
| warning    | Costs real comprehension time, and could mislead | `C1` on a comment restating its line           |
| suggestion | Worth raising; the author may reasonably decline | `A4` on inconsistent ordering across two files |

Default to the severity the catalog already gives the rule rather than deciding
afresh each time, so two reviews of the same code rank their findings the same
way. `N3` is a `warning`; `A4` is a `suggestion`. Only the four `X` guardrails
carry `error`, which is the catalog saying that misapplying a readability rule
does more damage than the readability problem it was aimed at.

Go above a rule's catalog severity only when the specific instance earns it,
and say why in the finding. A bare `timeout` where seconds and milliseconds are
both plausible is worth more than a generic `N3` warning, because that is where
readability and correctness stop being separate concerns.

## Finding format

One format, shared with refactor mode's change report and with `taorc-lint`,
so your findings and the linter's read the same way.

```text
[N3] src/api/client.ts:42  Name has no unit
  const timeout = 30;
  → rename to `timeoutSecs` (or `timeoutMs` if milliseconds)
```

The ID comes first because it is greppable and because it forces the finding to
be grounded in a real rule. Location second, so it is clickable. The matched
source third, which proves the finding is real rather than remembered. The fix
last, imperative and concrete — "rename to `timeoutSecs`", never "consider
renaming".

For a whole-diff finding with no single line, drop the location and say what the
finding covers.

```text
[X4] this diff  Mixes a rename with a behavior change
  `parseDate` was renamed to `parseIsoDate` in the same commit that changed
  its timezone handling.
  → split into two commits so the behavior change can be reviewed alone
```

## Citing rules

Cite only IDs that appear in `SKILL.md`'s catalog table. If you cannot find a
rule that fits, report the observation in plain prose with no ID (`X6`).

Inventing a plausible-looking ID is worse than having no ID at all. Every ID in
this catalog is permanent — review comments, lint suppressions, and eval results
are written against it — so an invented ID in the `N` range sends a reader
looking for a rule that will never exist, and an ID that *does* exist but means
something else sends them somewhere worse.

## Closing the review

End with what you did not flag, briefly. "The naming in `billing/` is
inconsistent with this module's, but that is pre-existing and out of scope for
this diff" tells the author you looked, tells them you had a reason to stop, and
records the observation without expanding their work.
