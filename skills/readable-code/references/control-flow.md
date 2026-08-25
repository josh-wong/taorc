# Control flow, expressions, and variables

Load this file when a function exceeds two levels of nesting or a condition
exceeds three terms.

These three categories share one measure: how much a reader has to hold in their
head to know what a line does. Nesting adds conditions to remember, a compound
expression adds terms to track, and a live variable adds a value that might have
changed. All three are inventory, and the rules below are ways of reducing it.

## Order things the way a reader reads them

**`F1` — comparison order.** Write a comparison the way you would say it aloud:
the quantity in question first, what it is measured against second.

```java
if (MAX_RETRIES > attempt) { ... }
if (attempt < MAX_RETRIES) { ... }
```

**`F2` — the interesting case first.** Where either branch could come first,
lead with the affirmative form, with the shorter branch when one is much
shorter, and with the case the reader came here to find.

```javascript
if (!user.isActive) {
  showReactivationPrompt();
} else {
  loadDashboard();
}

if (user.isActive) {
  loadDashboard();
} else {
  showReactivationPrompt();
}
```

These preferences can conflict — the affirmative branch is sometimes the long
one. When they do, precedence entry 3 decides: pick whichever ordering a
stranger understands faster.

**`F4` — no loop whose condition hides below its body.** A `do`/`while` states
what governs the loop underneath the code it governs, so the reader works
through the body once without knowing what controls it. A `continue` inside one
jumps somewhere most readers guess wrong.

## Flatten instead of nesting

**`F5` — guard clauses.** Handle empty input, invalid arguments, and other
special cases at the top and return immediately. Everything after them then
deals only with the ordinary case, and stops being indented under a condition.

**`F6` — shallow nesting.** Every level is another condition the reader must
hold to know whether a line runs at all. Deep nesting is usually residue: each
change wrapped working code in one more block. Treat the urge to add a level as
a prompt to restructure.

```python
for record in records:
    if record.is_valid:
        if record.owner is not None:
            if not record.archived:
                publish(record)

for record in records:
    if not record.is_valid:
        continue
    if record.owner is None:
        continue
    if record.archived:
        continue
    publish(record)
```

The second version has the same logic and one level of indentation. Note that it
also reads as a list of reasons to skip a record, which is what the code
actually means.

**`F7` — sparingly, anything that breaks linear order.** Threads, signal
handlers, deferred callbacks, exceptions thrown across module boundaries,
dynamic dispatch. Each means the next line to run is not the next line on
screen. Each is worth its cost where it solves a real problem; none is worth it
as a default.

## Break expressions into pieces

**`E1` — the explaining variable.** When part of an expression takes a moment to
identify, give it a name. The line you add names the concept once for every
future reader.

```javascript
if (orders[orders.length - 1].placedAt < cutoff) archive(orders);

const mostRecentOrder = orders[orders.length - 1];
if (mostRecentOrder.placedAt < cutoff) archive(orders);
```

**`E2` — the summary variable.** Different rule, similar shape. Here the
condition is not obscure; it is just long, and the reader has to reassemble it
at every appearance.

```csharp
bool canEditDocument = request.UserId == document.OwnerId
                    || request.Roles.Contains("admin");
```

**`E5` — named steps over one clever line.** When an expression outgrows what a
reader can hold, split it into named intermediates — or look for a formulation
that is smaller by construction rather than smaller by compression.

```javascript
const fee = order.expedited ? order.total * 0.02 + 15 : order.total * 0.02;

const handlingFee = order.total * 0.02;
const expeditingFee = order.expedited ? 15 : 0;
const fee = handlingFee + expeditingFee;
```

**`E3` — negation.** A condition that negates a whole group is often clearer
distributed across its parts, and occasionally the reverse. Write both and keep
the one that can be evaluated without doing algebra first.

```python
if not (record.is_synced and record.checksum_matches):
if not record.is_synced or not record.checksum_matches:
```

**`E4` — state conditions directly.** Test a boolean by using it; test a
collection with the language's own emptiness idiom.

```python
if config.verbose == True and len(warnings) > 0:
if config.verbose and warnings:
```

This one has a real exception, and it is a correctness exception, so precedence
entry 1 governs. It has two halves, and the example above performs both
rewrites, so both matter.

Dropping the comparison against a boolean literal is safe only where the value
genuinely holds a boolean. For any other truthy value — `1`, a non-empty
string, an object — `x == True` and `x` differ.

Testing a collection by using it is safe for built-in containers and not for
types that redefine truthiness. A NumPy array raises on `if x:` where
`len(x) > 0` succeeds, so the rewrite turns working code into
`ValueError: The truth value of an array with more than one element is
ambiguous`. A value that might be `None` needs that case handled on its own
terms rather than folded into a truthiness test.

When the type is not evident from the code in front of you, leave the
comparison alone. This rule is a readability preference; a wrong rewrite is a
crash.

**`E6` — no side effects in boolean operators.** Boolean operators compute
booleans. Using one to run code that happens to sit on its right-hand side saves
a line and costs the reader the assumption that a condition is only a condition.

```javascript
user && user.isAdmin && grantAccess(user);

if (user && user.isAdmin) {
  grantAccess(user);
}
```

The exception is choosing a *value*: `x = y || fallback` is idiomatic in many
languages and reads as one idea. The rule targets operators used to run code,
not to pick between values.

**`F3` — ternaries.** A conditional expression earns its place for a simple
either/or between two values. Once it carries nested conditions, side effects,
or long branches, the lines it saves cost more reading time than they save.

```javascript
const label = n === 0 ? "none" : n === 1 ? "one" : n < 10 ? "a few" : "many";

function describeCount(n) {
  if (n === 0) return "none";
  if (n === 1) return "one";
  if (n < 10) return "a few";
  return "many";
}
```

Note that this rule points the opposite way from what several general-purpose
linters enforce. A linter that rewrites every two-branch assignment into a
ternary is optimizing line count, which `P2` explicitly separates from
readability. Where a project's linter and this rule disagree, precedence entry 2
gives the project's configuration the win.

## Fewer live variables

**`V1` — remove a pass-through temporary.** A variable assigned once, used once
on the next line, and named no better than the expression it holds gives the
reader a name to track in exchange for nothing.

```python
def latest_backup(paths):
    result = sorted(paths, key=os.path.getmtime)[-1]
    return result

def latest_backup(paths):
    return sorted(paths, key=os.path.getmtime)[-1]
```

Keep the variable when the name genuinely explains something the expression does
not — that is `E1`, and the two rules meet here. The test is whether the name
adds information. `result` never does.

**`V2` — narrow the scope.** Move variables inward: a global to a member, a
member to a local, a local to the block that uses it. The cost of a widely
scoped variable is not the variable; it is that every line in its scope becomes
a line where the value might have changed.

**`V3` — declare at first use.** Collecting declarations at the top of a
function was once a language requirement. Now it only separates a name from the
code that gives it meaning.

**`V4` — prefer write-once values.** A variable reassigned in several places
forces the reader to find every assignment before they can say what it holds at
a given line. Use the language's immutable binding by default; treat needing
reassignment as a prompt to check whether a different formulation avoids it.

```javascript
let endpoint = BASE_URL;
if (useStaging) endpoint = STAGING_URL;
if (region) endpoint = `${endpoint}/${region}`;

const host = useStaging ? STAGING_URL : BASE_URL;
const endpoint = region ? `${host}/${region}` : host;
```

**`V5` — exit directly instead of steering with a flag.** A boolean whose only
job is telling a loop when to stop duplicates control flow the language already
has, and delays the exit until the condition is next checked.

```python
found = False
match = None
for row in rows:
    if not found and row.id == target:
        match = row
        found = True
return match

for row in rows:
    if row.id == target:
        return row
return None
```

## When not to apply these

**Correctness first.** `E4` and `E3` both rewrite conditions, and a rewrite that
is not equivalent is a bug wearing a readability rule as a disguise. Precedence
entry 1 is not a tiebreaker here; it is the whole answer.

**The project's linter may disagree.** `F3` in particular. Match the project
(`X2`, precedence entry 2) and say so once rather than fighting its
configuration file by hand.

**Do not restructure control flow in a diff about something else.** Converting a
nested block to guard clauses is a good change and a large one. `X1` and `X4`
both say it belongs in its own commit, where a reviewer can see that the logic
survived intact.
