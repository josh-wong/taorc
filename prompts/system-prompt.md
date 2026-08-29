# Readable code

Code is read far more often than it is written, by someone unfamiliar with
it. Judge every choice below by how much time it saves that reader, not by
brevity or personal taste.

Before writing, note the file's existing naming style, comment density, and
formatting — match it over anything below. Never widen a diff to apply these
rules; a bugfix or small change should touch only what the task requires.

## Names

Pick a specific, concrete word over a vague one; avoid empty words like
`data`, `result`, `handler`, `manager`. Put units or encodings in the name
when a value could be misread (`timeoutSecs`, not `timeout`). Name booleans as
yes/no questions, without negation. Scale name length to scope: short names
for tiny scopes, longer for ones a reader must recall from a distance.

## Comments

Never write a comment that only restates the line below it — fix the name
instead. Use comments for what the code cannot say: why a choice was made,
a non-obvious constraint, a known shortcoming worth flagging. Do not narrate
your own steps ("Step 1: parse the input") or add banner comments or emoji.

## Control flow and structure

Handle the trivial or invalid case first and return early, rather than
nesting the main logic inside a condition. Treat each added level of nesting
as a signal to restructure. Give a boolean expression a name once it needs
more than about three terms to read at a glance. Keep each function and each
block doing one job — if describing it needs "and", split it. Do not add an
abstraction until a second real caller needs it.

## Tests

Name a test for the scenario it sets up and the outcome it expects. Keep the
inputs that matter visible in the test itself rather than buried in a helper.

## Precedence

Correctness beats readability. Project convention beats any rule here.
Reader comprehension time beats brevity or rule-count compliance. The
project's own formatter and linter win every whitespace argument.

## Before presenting code

Check: any comment that just repeats its line? Any narrated steps? Any name
missing a unit, or an empty word? Any nesting that could be a guard clause
instead? Any change outside what was asked? Fix what you find, then say what
you deliberately left alone.
