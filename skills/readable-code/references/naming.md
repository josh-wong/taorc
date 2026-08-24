# Naming and layout

Load this file when naming a public API, when a name is contested in review, or
for any layout or alignment question. The `A` rules live here too.

A name is the only documentation that appears at every call site. A comment
explaining what `timeout` means lives in one place; the name `timeoutSecs`
travels to all of them. That is why naming outranks commenting when the two
compete — and why `C2` says to fix the name rather than write a comment that
compensates for it.

## The test that settles most arguments

Before settling on a name, try to misread it (`N16`). Pretend you know nothing
about your intent and list every meaning a stranger could reasonably attach.
When two candidates are on the table, run both through this test and keep the
one that survives.

This is the whole of `N14`: some ordinary words split cleanly into two readings
once attached to code.

```python
def clean(records): ...        # discards the bad ones, or repairs them in place?
def discard_invalid(records): ...
```

`filter` has the same problem in the other direction — does it keep what matches
or remove it? If a name has a plausible opposite reading, it needs replacing,
not a clarifying comment.

## Say what it is, not what shape it is

`N1` and `N9` are the two highest-yield rules in this file, and generated code
fails both constantly.

`N1` is about vague words where a precise one exists. `get` covers everything
from a field read to a network call; `data` describes a container, not its
contents.

```go
func (c *Cache) Get(key string) (string, error)        // reads? fetches? loads?
func (c *Cache) FetchOrLoad(key string) (string, error)
```

`N9` is about abstract names that describe a role rather than an action —
`handler`, `manager`, `processor`, `helper`. The fix is to name what the code
specifically checks, builds, or affects.

```go
func (q *Queue) IsReady() bool        // ready for what?
func (q *Queue) HasPendingWrites() bool
```

When one name is being stretched to carry two unrelated purposes, that is not a
naming problem — it is `S3` showing up as a naming problem. Split the thing in
two and name each half.

## Values a caller can get wrong

These are the rules where readability stops being separate from correctness. A
misread unit is a bug, not a style complaint, which is why a review should raise
them as errors rather than notes.

**`N3` — units, formats, encodings.** If a value carries a unit a caller could
get wrong, the unit belongs in the identifier, not in a type comment they will
never see at the call site.

```go
pollInterval := 5      // seconds? milliseconds?
pollIntervalMs := 5
```

The same applies to encodings: `html` versus `escapedHtml`, `utc` versus
`localTime`. If two plausible readings produce different behavior, name which
one it is.

**`N4` — values that are dangerous in their default form.** Unescaped strings,
plaintext secrets, unvalidated input. Putting the risk in the name makes it
travel with every reference.

```python
path = request.args["path"]
unsanitized_path = request.args["path"]
```

**`N13` — limits.** A bare noun leaves a reader guessing whether it is the cap
or the current count.

```python
UPLOAD_LIMIT = 25       # megabytes? files? and is it inclusive?
MAX_UPLOAD_MB = 25
```

**`N12` — range bounds.** Use `first`/`last` for a range that includes both
ends, `begin`/`end` for one that excludes the endpoint. There is no ordinary
English word for "the position just past the final element", which is why
`begin`/`end` became the idiom for it. Do not mix the two conventions in one
codebase, and do not use `start`/`stop`, which signals neither.

## Booleans

`N10` asks that a boolean read as a yes-or-no question — `is`, `has`, `can`,
`should`. The point is that a reader at the call site can tell whether `true`
means proceed or stop without opening the definition.

```java
boolean paginate;          // a command? a state? a request?
boolean shouldPaginate;
```

`N11` asks that the question be phrased positively. A negated name is fine in
isolation and awful in combination, because every call site pays the cost.

```csharp
bool skipCache = false;    // then: if (!skipCache) — a double negative
bool useCache = true;      // then: if (useCache)
```

## Length, abbreviation, and convention

`N5` scales name length to scope. A name visible across many files earns a
descriptive one; a value that dies two lines later does not. A five-word name on
a two-line value is as much a defect as a single letter on a value threaded
through a module.

`N8` removes words that add nothing while keeping the meaning precise. Drop what
the type or context already implies — `perform_cleanup` says nothing `cleanup`
does not — but keep a word that prevents ambiguity. This rule is frequently
over-applied; it is not a mandate to shorten.

`N6` rejects abbreviations a new teammate would not recognize. Widely understood
shortenings (`eval`, `doc`, `str`, `id`) are fine. A project-invented one
usually is not: `UsrSvc` saves six characters and costs every newcomer a
lookup.

`N2` permits `tmp`, `retval`, and a bare loop index precisely where the whole
life of the value is a line or two — a swap slot, a running accumulator. In a
nested loop, though, echo the collection being indexed, because that is where
the mistake actually happens.

```java
for (int i = 0; i < rows.length; i++)
    for (int j = 0; j < cols.length; j++)
        if (grid[i][j] == target) matches.add(rows[j]);

for (int ri = 0; ri < rows.length; ri++)
    for (int ci = 0; ci < cols.length; ci++)
        if (grid[ri][ci] == target) matches.add(rows[ci]);
```

Both blocks contain the same bug: `rows` is indexed with a column index. The
second block is not the fix — it is the same defect made visible. `rows[j]`
looks like every other line of loop code, while `rows[ci]` reads as wrong on
sight, because the index name says which axis it belongs to. The correction is
`rows[ri]`, and the naming is what makes anyone notice it needs correcting.

`N7` follows the project's conventions for capitalization and separators, so the
form of a name tells a reader what kind of thing it is. `N15` respects the
meaning conventional names already carry: do not give an expensive computation a
`get`-style name that convention marks as a cheap accessor. Either rename it to
signal the real cost, or make it cheap.

## When not to apply these

**A name the project already uses everywhere wins.** `X2` and precedence entry 2
both say so. If a codebase consistently says `ctx`, `cfg`, and `repo`, matching
it is more readable than importing this catalog's preferences into one file.

**Never rename an exported symbol on your own initiative.** `X3` is absolute
about this. A caller you cannot see is still a caller, and a rename that
improves one file can break every consumer of the package. Propose it instead.

**Do not rename to satisfy a rule when the diff was about something else.** `X1`
governs. Note it in the report and leave it.

## Layout

The `A` rules are about skimmability, not taste, and they stop wherever the
project's formatter starts (`X5`, precedence entry 4). If a formatter owns the
decision, it is not yours.

**`A1` and `A2` — consistent shape.** Structurally similar code should have a
similar outline, so a reader compares blocks instead of re-parsing each one.
Rearrange line breaks first; when the repeated parts differ too much in length
for that to work, extract a helper so the varying values sit next to each other.

```java
assertEquals(200, response.getStatusCode());
assertEquals("application/json", response.getHeader("Content-Type"), "wrong content type: " + response.getBody());

assertStatus(response, 200);
assertHeader(response, "Content-Type", "application/json");
```

**`A3` — column alignment.** Align a block of near-identical lines so the eye
tracks down a column rather than re-reading each line. Drop the alignment when
it becomes ongoing upkeep instead of a one-time formatting choice — a table that
must be re-aligned on every edit costs more than it returns.

**`A4` — deliberate order.** When nothing forces an order, choose one that means
something (an external order, most-to-least important, alphabetical) and repeat
it everywhere those items appear together. A parameter list that reads
`zip, state, city, street` in one function and `street, city, state, zip` in the
next guarantees a transposed argument eventually.

**`A5` and `A6` — grouping.** Break a class into labeled groups and a long
function into paragraphs separated by blank lines. Note that `A5`'s section
labels are ordinary grouping comments, not banners: `X8` forbids
`# ===== HELPERS =====`, not `# Internal helpers`.

**`A7` — consistency over preference.** Where two styles are equally readable,
the project's existing style wins, including when you would have chosen the
other one.
