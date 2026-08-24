# Comments

Load this file before writing or editing any comment or docstring.

There is one question behind every rule here: what does a reader need that the
code cannot tell them? A comment that answers it is worth more than the line it
occupies. A comment that restates the code costs the reader time twice — once
reading it, and again when it drifts out of date and they have to work out which
of the two is now lying.

Generated code fails in both directions at once: too many comments that restate
the code, and almost none that record why anything was done. Fixing only the
first half leaves the code worse than when you started.

## Comments to delete

**`C1` — restating the code.** If the comment adds nothing to the identifier and
syntax already in front of the reader, delete it. This includes comments written
to satisfy a habit that every function needs one.

```java
// Getter for the count field
public int getCount() { return count; }
```

**`C2` — compensating for a bad name.** When a comment exists mainly to explain
what an unclear name means, fix the name. The name travels to every call site;
the comment stays where it was written.

```python
# Stops watching the file. This does not delete the file on disk.
def unwatch(path): ...

def stop_watching(path): ...
```

**`X7` — narrating your own plan.** "Step 1", "First, we", "Now we". These
record the order you generated the code in, which is not something the reader
needs. See `references/ai-code-tells.md`.

**`X8` — banners and emoji.** `# ===== HELPERS =====` is not a section header;
it is a sign the file wants splitting. Note the boundary with `A5`, which does
ask for grouping labels — an ordinary `# Internal helpers` is a grouping
comment, not a banner.

## Comments that earn their place

**`C6` — where a reader would stop and ask why.** Reread your code as a stranger
and find the line where someone would pause and wonder why you did not do the
obvious thing. That exact line is where a comment belongs. This is the single
most valuable rule in this file and the one generated code most consistently
misses.

**`C5` — the value of a constant.** A threshold, timeout, or limit needs one
line on why *that* value, unless the name already makes it obvious.

```go
// The upstream gateway rate-limits after 5 requests in 10s; 4 keeps
// one retry in reserve for a genuine transient failure.
const maxRetries = 4
```

Note what the comment does not say. It does not say "the maximum number of
retries" — the name says that. It says the thing a reader could not recover
from the code at any price.

**`C3` — insight that cannot be recovered.** Why a surprising design won over
the obvious one. An honest note that a section is messy and how it should
eventually be cleaned up. A reader can reconstruct what the code does by reading
it; they cannot reconstruct what you rejected.

**`C16` — intent, not mechanics.** Write what the code is trying to accomplish
rather than an account of its steps. This has a second benefit: if the code does
not actually do what the comment says it means to, the mismatch becomes visible
to the next reader instead of staying invisible forever.

## Comments that protect the caller

**`C7` — advertise the pitfall.** If a function has a slow or blocking side
effect, an unusual failure mode, or a cost its name does not suggest, say so at
the definition. A caller who trusts the name should not get burned for it.

```python
def resize_image(path, width):
    """Downloads the source image from remote storage first if it isn't cached."""
```

**`C14` — describe behavior precisely, including corner cases.** A docstring
that restates the signature in sentence form answers none of the questions a
caller actually has. Empty input, duplicates, boundaries — say what happens.

```rust
// Returns the number of words in this string.
fn word_count(s: &str) -> usize { ... }

// Counts whitespace-delimited tokens; runs of whitespace count once,
// and leading or trailing whitespace is ignored.
fn word_count(s: &str) -> usize { ... }
```

**`C15` — show the corner case.** When the behavior is awkward to describe in
prose, a worked input and its output settles it faster than three sentences
trying to enumerate the cases.

## Orientation

**`C8` — file and class purpose.** A few sentences at the top of anything whose
role is not obvious from skimming its parts, saying what it accomplishes and how
it relates to its neighbors.

**`C9` — summarize a block, do not narrate lines.** When a run of statements
accomplishes one coherent step, put one comment above the block. This is the
constructive form of the same instinct that produces plan narration: the
impulse to explain the sequence is right, the line-by-line execution is wrong.

## Making a comment good

**`C10` — rough first, then precise.** If a good comment feels like work, write
the rough version exactly as you think it, then go back and replace the vague
words with what you actually meant. Writing it later means reconstructing a
decision you have already forgotten.

**`C11` and `C13` — compact and direct.** Making a comment more precise and
making it shorter are usually the same edit. Every word should carry
information a reader needs.

**`C12` — no unresolvable pronouns.** If more than one antecedent is plausible,
name the thing.

```python
# Copy the file into the archive, but check if it's already compressed.
# Copy the file into the archive, but check if the file is already compressed.
```

**`C17` — label mysterious arguments inline.** For a bare literal whose meaning
is not obvious at the call site, name the parameter it fills, before the value.

```csharp
ScheduleJob(3, true);
ScheduleJob(/* priority = */ 3, /* recurring = */ true);
```

Reserve this for genuinely opaque arguments. Applied to every call it becomes
noise, and in a language with named arguments the language already solves it.

**`C18` — use the term of art.** If a pattern has an established name —
memoization, debouncing, idempotent — use it instead of describing the mechanism
from scratch. Invent project jargon only where no accepted term exists.

## Markers

`C4` asks that deliberate gaps carry a searchable marker — `TODO`, `FIXME`,
`HACK`, `XXX` — plus enough context to act on later. Prose describing a gap
without a marker is invisible to the person looking for gaps.

```python
def parse_timestamp(raw):
    return raw  # TODO

def parse_timestamp(raw):
    # TODO(#482): raw is a Unix epoch today; switch to ISO 8601 once
    # the ingest service migrates, then drop this passthrough.
    return raw
```

A bare `TODO` records that someone once felt uneasy. The second version records
what is wrong, what the fix is, and what unblocks it.

This is also the correct destination for the placeholder comment that generated
code leaves behind. `# In a real implementation, you would...` is either
describing work that must happen — in which case it becomes a real marker with
an owner — or it is describing nothing, in which case delete it.

## When not to comment

**Do not add comments to a diff that did not need them.** `X1` governs. Adding
five explanatory comments to code you were asked to make one change in makes the
diff harder to review, whatever the comments say.

**Do not comment to hit a density target.** There is no correct number of
comments per function. `C1` and `C6` pull in opposite directions on purpose, and
a file that satisfies both will have few comments, each load-bearing.

**Match the file's existing density.** `X2` and precedence entry 2 apply here as
much as to naming. A codebase that comments sparsely is making a choice; a
single heavily commented function dropped into it reads as noise.
