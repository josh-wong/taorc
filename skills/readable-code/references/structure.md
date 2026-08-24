# Structure

Load this file before extracting a function or splitting a file.

Every rule here is about where a boundary belongs. Drawn well, a boundary lets a
reader understand one piece without holding the other in mind. Drawn badly — or
drawn where none was needed — it adds a layer to step through on the way to what
actually happens.

Generated code errs in one direction almost exclusively: too many boundaries,
introduced too early. `S6` is the rule that pushes back, and it is the one worth
reading first.

## Do less

**`S5` — question the requirement.** The fastest code to read is code that was
never written. Before implementing a feature as stated, check whether a narrower
version meets the real need, whether an existing path already covers most of it,
and whether the general case is actually required or merely imagined.

**`S6` — no abstraction until a second caller needs it.** A helper, interface,
or configuration option introduced for one call site adds a layer the reader
must step through, in exchange for flexibility nothing uses.

```typescript
interface Formatter { format(v: number): string; }

class CurrencyFormatter implements Formatter {
  format(v: number) { return `$${v.toFixed(2)}`; }
}

const formatter: Formatter = new CurrencyFormatter();
row.textContent = formatter.format(total);
```

```typescript
row.textContent = `$${total.toFixed(2)}`;
```

The second version is the whole feature. Write it inline; extract when a second
caller appears. Note that this is about the second *caller*, not about size — a
one-line function with three callers has earned its name.

**`S7` — delete code that cannot change the outcome.** Error handling for
conditions the surrounding code makes impossible, branches nothing can reach,
options no caller sets, and code left commented out. All of it reads as though
it guards a real risk, so a reader spends time working out which risk.

```python
def total_cents(prices: list[int]) -> int:
    try:
        return sum(prices)
    except ZeroDivisionError:
        return 0
```

`sum` over integers does not divide. The handler makes a reader look for the
division.

This rule has the sharpest exception in the catalog, and it is a correctness
exception. "Nothing calls it" is a claim about the whole world, and a repository
shows you part of it. Apply it freely to symbols private to their module; for
anything exported, *propose* the deletion rather than making it — the same
reasoning `X3` gives for renames. Commented-out code is the one part of this
rule that is always safe to act on.

## Separate what does not belong together

**`S1` — extract a self-contained subproblem.** When part of a block solves a
problem that is not the block's stated purpose — parsing a format, computing a
distance, normalizing a key — move it out. The test is whether you can describe
the extracted function without mentioning its caller.

```go
func RenderProfile(u User) string {
    initials := ""
    for _, part := range strings.Fields(u.FullName) {
        initials += strings.ToUpper(part[:1])
    }
    // ... rendering ...
}

func initials(fullName string) string { ... }
```

"Builds initials from a full name" mentions no caller, so the boundary is real.
Compare a hypothetical `renderProfileStep2`, which cannot be described without
its caller and therefore is not a subproblem — it is a slice of one.

**`S3` — one task at a time.** List what a long block actually does, then give
each item its own function or at least its own paragraph. Interleaved work —
validating while accumulating, parsing while rendering — makes the reader track
both at once.

```ruby
def import(rows)
  errors = []
  total = 0
  rows.each do |row|
    if row["amount"].nil?
      errors << "missing amount on #{row['id']}"
    else
      total += row["amount"]
    end
  end
  [errors, total]
end
```

Two tasks, one loop, and a return value that is a tuple because the function
could not decide what it was for. Split into `validation_errors` and
`total_amount` and each reads on its own.

**`S2` — general-purpose code apart from project logic.** Code that would make
sense in another project belongs somewhere separate from code that only makes
sense in this one. Name that home for what lives in it.

```python
# utils.py
def slugify(text): ...
def retry_with_backoff(fn): ...
def format_currency(cents, locale): ...
def load_customer_tier(customer_id): ...
```

`utils` names the fact that someone had nowhere to put things. `text_slugs.py`,
`retries.py`, and `money.py` name what is inside; `load_customer_tier` was never
general-purpose and belongs with the customer code.

## Reach for what exists

**`S8` — know the standard library.** Grouping, counting, deduplicating,
pairing, sorting by key, set arithmetic — already implemented, tested, and named
in every mainstream standard library. A hand-rolled version is more code to
read, and its bugs are yours.

```python
counts = {}
for tag in tags:
    if tag in counts:
        counts[tag] += 1
    else:
        counts[tag] = 1

counts = Counter(tags)
```

Check the difference before swapping, because a library type is rarely an exact
drop-in. Here, `Counter` returns zero for a key never seen where the plain dict
raises `KeyError` — so any caller relying on that raise changes behavior. Where
the two differ in a way the surrounding code depends on, keep the explicit
version. Correctness first (`X4`, precedence entry 1).

**`S9` — wrap an awkward interface.** When an API demands setup, returns a shape
you have to convert, or takes parameters irrelevant to your use, write the small
wrapper presenting the interface your code actually wants, and call that.

This is the one place in this file where adding a layer is the recommendation,
which makes the boundary with `S6` worth stating: `S9` wraps something that is
already awkward at more than one call site. A wrapper around a single clean call
is just `S6` again.

## Say it in words first

**`S4` — describe, then implement.** State what the code must do in ordinary
language before or while writing it. The description usually comes out shorter
and better organized than the first code you would have written, and when it
comes out tangled, that is information: the design is tangled, and no amount of
careful naming will hide it.

This pairs with `C16`. If the plain-language description and the code disagree
later, someone notices.

## When not to apply these

**Extraction widens diffs.** Moving code to a new function or file touches
imports, call sites, and sometimes tests. `X1` and `X4` both apply: a structural
change belongs in its own commit, where a reviewer can confirm the behavior
survived.

**The project's existing seams win.** If a codebase organizes by layer and you
would have organized by feature, follow it (`X2`, precedence entry 2). A single
module reorganized to a different philosophy is harder to navigate than one that
is consistently organized the way you would not have chosen.

**Do not delete exported code on your own initiative.** Restated because it is
the most consequential line in this file: `S7` plus an exported symbol equals a
proposal, not an edit.
