# Tests

Load this file when writing or reviewing tests.

A test is read at the worst possible moment: something is broken, someone is
under pressure, and the person reading has probably never seen this file. That
is the audience these rules are written for. Test code that is merely correct
but opaque fails them exactly when it matters.

## The name is read without the code

`T3` matters more than any other rule here, because a test name is usually read
in a failure report with none of the test body on screen. It has to identify the
broken behavior on its own.

```python
def test_parse_2(): ...
def test_parse_rejects_timestamp_without_timezone(): ...
```

Name the unit under test, the condition, and the expected result. A name built
from a number, or from `basic` / `works` / `simple`, identifies nothing — it
tells the reader only that someone wrote a second test.

This is also the most common tell in generated test suites, which is why it is
one of the rules `taorc-lint` checks mechanically.

## Show only what the test is about

`T1` asks that the test body contain the input under test and the expectation
about it, and as little else as possible. Push construction, fixtures, and
repeated setup behind helpers.

```python
def test_expired_session_rejected():
    user = User(id=1, name="Ada", email="ada@example.com", verified=True)
    session = Session(user=user, token="abc", created_at=NOW - 7200, ttl=3600)
    assert authorize(session, NOW) is False

def test_expired_session_rejected():
    session = a_session(age_seconds=7200, ttl=3600)
    assert authorize(session, FROZEN_NOW) is False
```

The second version says what the test is about — age against TTL. In the first,
those two numbers are buried among five fields that have nothing to do with
expiry, and a reader has to check each one before concluding it is irrelevant.

`T2` is the same idea applied to the values themselves. Prefer the smallest,
plainest input that still triggers the case.

```javascript
expect(median([84.21, 12.09, 55.5, 91.34, 7.02])).toBeCloseTo(55.5);
expect(median([1, 2, 3])).toBe(2);
```

Realistic-looking data implies the details matter, and sends the reader looking
for significance in numbers chosen at random. Use elaborate input only when the
case under test genuinely needs it.

## Make the failure self-explanatory

`T4` asks that a failing assertion say what went wrong without a debugger. Use
the assertion that reports both values rather than one that collapses the
comparison into a single boolean.

```python
self.assertTrue(actual_total == expected_total)   # AssertionError: False is not true
self.assertEqual(actual_total, expected_total)    # AssertionError: 1499 != 1500
```

The first tells you a test failed. The second tells you by how much, which is
often the whole diagnosis. Where a comparison is domain-specific, a custom
assertion that prints the difference in domain terms is worth writing once.

## One reason to fail

`T5` asks that each test cover one behavior. A test asserting several unrelated
things stops at the first failure and hides the rest, and no name can describe
everything it covers.

```python
def test_cart():
    cart = Cart()
    cart.add(ITEM, qty=2)
    assert cart.subtotal == 200
    cart.apply_coupon("HALF")
    assert cart.subtotal == 100
    cart.remove(ITEM)
    assert cart.is_empty
```

When the second assertion fails, the third never runs, so you learn about the
coupon bug and not about the removal bug. Split into three tests sharing a setup
helper and each has one reason to fail and a name that states it.

This is not a rule against multiple assertions. Several assertions about one
behavior — a parsed record's three fields — are one test. Several assertions
about three behaviors are three tests.

## Hard to test is a design signal

`T6` is the rule that points outward. Code needing elaborate setup usually has
real problems — hidden global state, too many responsibilities, dependencies it
constructs instead of receiving — and those are the same problems that make it
hard to read. Fix the design.

The rule's second half is the part that keeps it honest: stop short of
distorting the design to serve the tests. Testability is evidence about a
design, not the goal of one. An interface that exists only so a mock can be
injected, with one production implementation, is `S6` reappearing in the test
suite.

Where a project has an established testing architecture, follow it (`X2`,
precedence entry 2) rather than re-litigating its seams inside an unrelated
change.

## When not to apply these

**Do not rewrite a test suite you were asked to add one test to.** `X1`. Add the
test, note what you saw, and let the author decide.

**Match the suite's existing conventions.** If the project names tests
`it_rejects_...` or uses a given/when/then structure, follow it. A single test
in a different style is harder to scan than one that matches its neighbors, even
if the house style is not the one this file would have chosen.

**A test that reads badly but pins down real behavior is still valuable.**
Precedence entry 1 applies to tests too: do not "clean up" a test into one that
no longer covers the case it was written for. If you cannot tell what case it
covers, that is a finding to report, not a license to rewrite it.
