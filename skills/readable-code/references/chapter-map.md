# Chapter map

Every rule in this catalog traces back to a chapter of *The Art of Readable Code* by Dustin Boswell and Trevor Foucher (O'Reilly, 2011), except the `X` guardrails, which are original to this project. This file is the attribution record and the pointer back to the source.

The chapter descriptions below are deliberately thin — just enough to find the right chapter. They are not summaries, and they are not a substitute for the book. If a rule here is useful to you, the chapter it came from is worth reading in full; the reasoning, the counterexamples, and the judgment calls did not survive the compression into one-line rules.

taorc is unofficial and is not affiliated with or endorsed by O'Reilly Media or the authors. Please buy the book.

## Chapter 1

What readability is for, and the standard the rest of the book argues from.

| Rule | What it says                                                                              |
| ---- | ----------------------------------------------------------------------------------------- |
| `P1` | Minimize the time it would take someone else to understand the code                       |
| `P2` | Fewer lines is usually good, but it is not the same goal as readability                   |
| `P3` | Treat an apparent conflict between readability and other goals as a signal to look harder |

## Chapter 2

Choosing names that carry information.

| Rule | What it says                                                                   |
| ---- | ------------------------------------------------------------------------------ |
| `N1` | Prefer a specific word over a vague one when a precise word exists             |
| `N2` | Reserve placeholder names like tmp and retval for genuinely short-lived values |
| `N3` | Put units, formats, or encodings in the name when the value could be misread   |
| `N4` | Mark values that are dangerous or need special handling in the name            |
| `N5` | Scale name length to the size of the scope the name lives in                   |
| `N6` | Avoid an abbreviation a new teammate would not recognize                       |
| `N7` | Use the codebase's naming format consistently to convey meaning                |
| `N8` | Remove words that add no information, but keep the meaning precise             |
| `N9` | Prefer a concrete name that describes what an entity actually does             |

## Chapter 3

Choosing names that cannot be read the wrong way.

| Rule  | What it says                                                                 |
| ----- | ---------------------------------------------------------------------------- |
| `N10` | Name booleans so they read as a yes-or-no question                           |
| `N11` | Avoid negation in boolean names                                              |
| `N12` | Use first and last for an inclusive range, begin and end for a half-open one |
| `N13` | Prefix a hard limit with max or min rather than a bare noun                  |
| `N14` | Avoid a name whose common meaning could be read two different ways           |
| `N15` | Match users' expectations for conventional method names                      |
| `N16` | Actively look for ways a name could be misunderstood                         |

## Chapter 4

Visual layout, grouping, and consistent formatting.

| Rule | What it says                                                               |
| ---- | -------------------------------------------------------------------------- |
| `A1` | Give structurally similar code the same visual shape, then make it compact |
| `A2` | Use a helper method when repeated detail prevents a consistent layout      |
| `A3` | Align repeated similar lines into columns when it improves skimming        |
| `A4` | Pick a meaningful order and use it consistently                            |
| `A5` | Organize declarations into logical blocks                                  |
| `A6` | Break large blocks into logical paragraphs                                 |
| `A7` | Prefer consistency over the personally preferred style                     |

## Chapter 5

Deciding what is worth a comment.

| Rule  | What it says                                                                      |
| ----- | --------------------------------------------------------------------------------- |
| `C1`  | Do not write a comment that only restates what the code already says              |
| `C2`  | Fix a bad name instead of writing a comment to compensate for it                  |
| `C3`  | Use comments to record insight the code by itself cannot convey                   |
| `C4`  | Mark known shortcuts and unfinished work with a searchable marker                 |
| `C5`  | Explain a constant's value when the number itself doesn't explain the choice      |
| `C6`  | Comment where a careful reader would stop and ask why                             |
| `C7`  | Advertise a likely pitfall before a caller discovers it the hard way              |
| `C8`  | Give a complex file or class a short comment stating its overall purpose          |
| `C9`  | Summarize a multi-step block with a single comment instead of narrating each line |
| `C10` | Write a rough comment early, then make it precise                                 |

## Chapter 6

Making a comment precise and compact.

| Rule  | What it says                                                               |
| ----- | -------------------------------------------------------------------------- |
| `C11` | Keep comments compact and information-dense                                |
| `C12` | Avoid a pronoun a reader would have to work to resolve                     |
| `C13` | Polish comments into direct, precise sentences                             |
| `C14` | Describe a function's behavior precisely, including its corner cases       |
| `C15` | Use a carefully chosen input/output example to clarify corner cases        |
| `C16` | State the intent behind the code, not just an account of its mechanics     |
| `C17` | Label a mysterious function argument inline at the call site               |
| `C18` | Reach for an established term of art instead of describing it from scratch |

## Chapter 7

Loops, conditionals, and the order a reader follows them in.

| Rule | What it says                                                                                               |
| ---- | ---------------------------------------------------------------------------------------------------------- |
| `F1` | Put the value being examined on the left of a comparison and the value it is measured against on the right |
| `F2` | Put the positive, the simpler, or the more interesting case first                                          |
| `F3` | Reach for a conditional expression only when it is genuinely quicker to understand than an if/else         |
| `F4` | Avoid a loop whose condition is only visible after its body                                                |
| `F5` | Handle the trivial and invalid cases up front and return immediately                                       |
| `F6` | Keep nesting shallow, and treat one more level as a signal to restructure                                  |
| `F7` | Use constructs that break linear execution order sparingly                                                 |

## Chapter 8

Cutting large expressions down to readable pieces.

| Rule | What it says                                                                              |
| ---- | ----------------------------------------------------------------------------------------- |
| `E1` | Name a subexpression with a variable that says what it is                                 |
| `E2` | Give a recurring condition a short name even when it needs no explanation                 |
| `E3` | Rewrite a negated group into whichever equivalent form states the idea more directly      |
| `E4` | State a condition directly instead of comparing it against a boolean or a length          |
| `E5` | Break a large expression into named steps rather than compressing it into one clever line |

## Chapter 9

Variable lifetime, scope, and reassignment.

| Rule | What it says                                                          |
| ---- | --------------------------------------------------------------------- |
| `V1` | Remove a variable that only carries a value from one line to the next |
| `V2` | Narrow each variable's scope to the smallest region that needs it     |
| `V3` | Declare a variable immediately before its first use                   |
| `V4` | Prefer values assigned once over variables that change                |
| `V5` | Exit a loop directly instead of steering it with a flag variable      |

## Chapter 10

Pulling unrelated subproblems out of a function.

| Rule | What it says                                                                            |
| ---- | --------------------------------------------------------------------------------------- |
| `S1` | Extract a self-contained subproblem into a function describable without its caller      |
| `S2` | Keep general-purpose code apart from project logic, and name its home for what it holds |

## Chapter 11

Doing one task at a time.

| Rule | What it says                       |
| ---- | ---------------------------------- |
| `S3` | Make a block do one task at a time |

## Chapter 12

Describing logic in plain language before coding it.

| Rule | What it says                                                                                 |
| ---- | -------------------------------------------------------------------------------------------- |
| `S4` | Describe what the code must do in plain language, then make the code follow that description |

## Chapter 13

Writing and keeping less code.

| Rule | What it says                                                              |
| ---- | ------------------------------------------------------------------------- |
| `S5` | Question the requirement before writing code to satisfy it                |
| `S6` | Do not add an abstraction until a second caller needs it                  |
| `S7` | Delete code that cannot change the outcome                                |
| `S8` | Know the standard library well enough to reach for it before rewriting it |

## Chapter 14

Tests that stay readable, and what they say about the design.

| Rule | What it says                                                                             |
| ---- | ---------------------------------------------------------------------------------------- |
| `T1` | Make the values a test is actually about visible at a glance                             |
| `T2` | Choose the simplest input that still exercises the behavior under test                   |
| `T3` | Name a test for the situation it sets up and the outcome it expects                      |
| `T4` | Make a failing assertion say what went wrong without a debugger                          |
| `T5` | Keep each test about one behavior                                                        |
| `T6` | Treat hard-to-test code as a design signal, without distorting the design to serve tests |

## Original content (no chapter)

The `X` category has no book source. These rules govern how an *agent* applies the rest of the catalog — restraint about diff size, deference to a project's existing conventions, and separating a cleanup from a behavior change. The book was written for humans editing their own code and had no reason to address any of it.

| Rule | What it says                                                                           |
| ---- | -------------------------------------------------------------------------------------- |
| `X1` | Do not widen a diff to satisfy a readability rule                                      |
| `X2` | Match the file's existing vocabulary and conventions over this catalog's preference    |
| `X3` | Never rename a public or exported symbol unless asked                                  |
| `X4` | Keep readability changes and behavior changes in separate steps                        |
| `X5` | Leave whitespace, line length, and casing to the project's formatter and linter        |
| `X6` | Cite only rule IDs that exist in this catalog, and report anything else as plain prose |
| `X7` | Do not narrate your own plan or process in code comments                               |
| `X8` | Do not add banner comments, section dividers, or emoji to code                         |

## Coverage note

Chapters 1 through 6 produced 44 rules against an original estimate of 34, and chapters 7 through 14 produced 31 against an estimate of 31. The catalog's totals in `v1-design-doc.md` §3.2 and the PRD's 65-75 target were both sized before drafting; the shipped total is 83. Rule IDs are permanent regardless (`v1-design-doc.md` §3.3), so this is recorded rather than corrected.
