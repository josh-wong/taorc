# AI code tells

Load this file when asked to de-slop, humanize, or clean up AI-generated code.

The habits below are what make generated code recognizable. Most are not errors
— the code runs, the tests pass — so a compiler and a test suite will never
flag them. They cost a reader time, which is why they belong to this catalog
rather than to a linter's error list.

Every row resolves to a rule ID. That matters: "this looks AI-written" is not
something a reviewer can act on, and it is not something you can defend. "`N1`:
`data` names the variable's shape, not its contents" is.

## The tells

The **Lint** column marks tells `taorc-lint` catches mechanically. The rest need
your judgment, which is why this file exists.

| Tell                                                  | Rule  | Lint | Fix                                                  |
| ----------------------------------------------------- | ----- | ---- | ---------------------------------------------------- |
| Comment restates the next line                        | `C1`  | ✓    | Delete                                               |
| `// Step 1:` / `// First, we...` plan narration       | `X7`  | ✓    | Delete                                               |
| `# ===== HELPERS =====` banner                        | `X8`  | ✓    | Delete; a file needing sections needs splitting      |
| Emoji in comments, log lines, or output               | `X8`  | ✓    | Delete                                               |
| Docstring restates the signature and adds nothing     | `C14` |      | Delete, or replace with the why and the corner cases |
| `# In a real implementation, you would...`            | `C4`  | ✓    | Delete, or convert to a real `TODO(owner):`          |
| Commented-out code left behind                        | `S7`  | ✓    | Delete; version control remembers it                 |
| `data`, `result`, `output`, `info`, `item`            | `N1`  | ✓    | Name the thing                                       |
| `handler`, `processor`, `manager`, `helper`           | `N9`  |      | Name the action                                      |
| `utils.py` / `helpers.ts` accumulating unrelated code | `S2`  |      | Name the domain concept                              |
| Bare `timeout`, `size`, `limit`                       | `N3`  | ✓    | Add the unit or the bound                            |
| Single-use helper abstracted "for reusability"        | `S6`  |      | Inline it                                            |
| Try/except wrapped around code that cannot throw      | `S7`  |      | Delete                                               |
| Reimplemented `groupby` / `Counter` / `zip`           | `S8`  |      | Use the library                                      |
| Intermediate variable that exists only to be returned | `V1`  |      | Return directly                                      |
| `if x == True:` / `if len(x) > 0:`                    | `E4`  |      | `if x:`                                              |
| Test named `test_1`, `test_basic`, `test_works`       | `T3`  | ✓    | Name the scenario and the expectation                |
| Hedging comment: "This should probably..."            | `C13` |      | Decide, or file a real `TODO`                        |

Two rows need a caveat the Fix column has no room for. `E4`'s `if x:` is safe
only where the value is a real boolean or a built-in container — a NumPy array
raises on it, and a possible `None` needs handling on its own terms. `S7`'s
"delete" applies to code the surrounding lines prove is unreachable, not to a
handler that is impossible only under an assumption. `control-flow.md` and
`structure.md` carry both in full; check them before applying either row to
anything you did not write.

The Lint column marks eight of `taorc-lint`'s nine rules; the banner and emoji
rows share `X8`, which is why nine check marks cover eight rules. The ninth,
`N11` (negated boolean name), has no row here at all: it is an ordinary naming
defect rather than a generative habit, so it earns a lint rule without earning
a place in this file.

Three of the most recognizable tells — plan narration, banner comments, and
emoji — land on `X` rules rather than book-derived ones. They are habits only a
generative model has, so the book had no reason to warn against them.

## The ones that need judgment

### Plan narration is not commentary

Narration comments record the order you generated the code in. The reader does
not care about that order; they care what the code does now.

```python
# Step 1: Validate the input
if not payload.get("account_id"):
    raise ValueError("account_id is required")

# Step 2: Look up the account
account = accounts.get(payload["account_id"])

# Step 3: Apply the credit
account.balance += payload["amount"]
```

Every comment restates its line. Delete all three (`X7`, `C1`). What a reader
would actually want to know — that credits are applied without a pending state
because the ledger reconciles nightly — is nowhere in the code.

### A helper with one caller is not reuse

The giveaway is a name that restates the expression it wraps.

```typescript
function isValidEmail(value: string): boolean {
  return EMAIL_PATTERN.test(value);
}

function registerUser(form: SignupForm) {
  if (!isValidEmail(form.email)) throw new ValidationError("email");
  // ...
}
```

The helper adds a name, an indirection, and a second place to look, in exchange
for nothing — the caller reads no better than `EMAIL_PATTERN.test(form.email)`
would. Inline it (`S6`).

The exception matters: this is about the *second caller*, not about line count.
A one-line function with three callers earns its name. A one-line function that
gives a genuinely non-obvious expression a name earns it too, even with one
caller — that is `E1` doing its job, and it is why this row cannot be linted.

### An empty name is a name for the container

`data`, `result`, `payload`, `item`, and `value` all describe the shape of the
box rather than what is in it. The fix is not a longer name; it is a name that
says what the value *is*.

```python
data = fetch(url)                 # -> subscriptions
result = [d for d in data if ...] # -> expiring_soon
```

Where the value genuinely has no better name than its role — a loop variable in
a three-line comprehension, a swap slot — `N2` explicitly permits it. The test
is how long the value lives, not what it is called.

### The wrapped call that cannot fail

Defensive code pattern-matches as careful, so it survives review by looking
responsible. Ask what would actually raise.

```python
try:
    total = sum(line.amount for line in invoice.lines)
except Exception:
    total = 0
```

`sum` over a list of numbers does not raise. The handler is there because
defensive code pattern-matches as careful, not because anything can fail. It
converts a future genuine error — `line.amount` turning out to be `None` after
a schema change — into a silent zero. Delete it (`S7`).

## Do not overcorrect

De-slopping is a readability task, so it is bound by the same guardrails as any
other. Two failure modes are worth naming.

**Do not strip comments that carry the why.** The tell is a comment that
restates the code, not a comment that exists. A comment explaining why a
retry count is 3 rather than 5 is exactly what `C6` asks for; deleting it
because it sits above the constant makes the code worse.

**Do not rewrite what you were not asked to touch.** A de-slopping request on
one module is not authorization to rename exported symbols (`X3`), reflow
whitespace the formatter owns (`X5`), or widen the diff to catch tells in a file
nobody asked about (`X1`). Report those instead — the change report is where
"the tests in `test_legacy.py` have the same problem" belongs.
