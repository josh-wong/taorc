## `starter/pricing.py`

```python
"""Order pricing. Every money value here is integer cents."""

# Sales-tax multipliers (1 + rate), applied to a line's pre-tax cents.
TAX_MULTIPLIER_DEFAULT = 1.05
TAX_MULTIPLIER_FOOD_EXEMPT_STATE = 1.08

# States that exempt food from sales tax. Non-food sold there is taxed at the
# higher local rate instead of the default one.
FOOD_EXEMPT_STATES = ("CA", "WA")

MEMBER_DISCOUNT_CENTS = 500
MEMBER_DISCOUNT_MIN_TOTAL_CENTS = 5000


def _is_billable(item):
    """An item bills only if both its quantity and unit price are positive."""
    return item.get("qty", 0) > 0 and item.get("unit_price_cents", 0) > 0


def _line_total_cents(item, state):
    """Return one line's cents including sales tax for `state`.

    Food in a food-exempt state is untaxed. Anything else in such a state pays
    the local rate; every other state pays the default rate regardless of
    category. Tax is truncated, not rounded: 3 x 199 at 1.05 gives 626, not 627.
    """
    pre_tax_cents = item["qty"] * item["unit_price_cents"]
    if state not in FOOD_EXEMPT_STATES:
        return int(pre_tax_cents * TAX_MULTIPLIER_DEFAULT)
    if item.get("category") == "food":
        return pre_tax_cents
    return int(pre_tax_cents * TAX_MULTIPLIER_FOOD_EXEMPT_STATE)


def compute_price(order):
    """Return the order total in cents.

    Returns 0 for `None`, for an order with no `items` key, and for one whose
    items list is empty. Items with a non-positive quantity or unit price are
    skipped and contribute nothing.
    """
    if order is None:
        return 0
    items = order.get("items")
    if not items:
        return 0

    state = order.get("state")
    is_member = order.get("member")
    total_cents = 0
    for item in items:
        if not _is_billable(item):
            continue
        total_cents += _line_total_cents(item, state)
        # The discount is applied per billable line, so one order can earn it
        # several times. Preserved exactly as found, because changing it would
        # change totals.
        # TODO(pricing): confirm this is intended; it reads like a bug.
        if is_member and total_cents > MEMBER_DISCOUNT_MIN_TOTAL_CENTS:
            total_cents -= MEMBER_DISCOUNT_CENTS
    return total_cents
```

## What changed

```text
[F5] starter/pricing.py:1  Success path buried under two levels of if/else
  → the None and empty-items cases now return 0 up front; nesting drops from 5
    levels to 2

[F5] starter/pricing.py  Item validity checked by nesting instead of skipping
  → `if not _is_billable(item): continue`

[S1] starter/pricing.py  Tax selection was a self-contained subproblem
  → extracted `_line_total_cents`; the four-branch tree collapses to three
    returns, since outside CA/WA both categories were already taxed at 1.05

[C5] starter/pricing.py  Bare 1.05, 1.08, 5000, 500 and the ("CA", "WA") tuple
  → named constants; the comment records that 1.05/1.08 are 1 + rate, not rates

[N3] starter/pricing.py  `total` did not carry its unit
  → `total_cents`, matching `unit_price_cents`

[C14] starter/pricing.py  No stated behavior for None, missing items, or
      zero-quantity lines
  → docstring on `compute_price` covers all three; `_line_total_cents` documents
    the truncation with a worked example
```

## Behavior I was careful to preserve

- **Per-line member discount.** It stays inside the loop, evaluated against the running total after each billable line. Hoisting it out would be the obvious "fix" and would change totals on multi-item orders.
- **The untaxed path returns `pre_tax_cents` unmultiplied.** The original wrote `total += item["qty"] * item["unit_price_cents"]` with no `int()` there, unlike every other branch. For integer inputs that is identical, but a float `qty` would keep the total a float. I kept the branch free of `int()` rather than folding it into a 1.00 multiplier.
- **`_is_billable` uses `and` over two positive tests**, not a negated `<= 0` pair. Same results for ordinary numbers, and it also matches the original on `float("nan")`, which passes neither `> 0` nor `<= 0`.
- **Truncation direction.** `int()` throughout, not `round()`.

`state` and `member` are now read once before the loop. `order` is never mutated in the loop, so this cannot change a result.

## What I did not change

- The name and signature of `compute_price`, as instructed.
- The pricing rules themselves, including the per-line discount flagged above and the fact that a missing `category` is billed as non-food.
- No input validation, type hints, or error handling added — none of that was in the original, and adding it would be a behavior change belonging in a separate step.

Two follow-ups I noticed and deliberately left alone: there are no tests in `starter/`, and this refactor is exactly the kind that wants characterization tests first — one covering a CA member order with several items would pin down the repeated discount. If your checkout has `scripts/taorc_lint.py` under a skills directory, run `python <root>/scripts/taorc_lint.py --changed` against this file; I verified the checklist by hand.