## `starter/pricing.py` (refactored)

```python
"""Order pricing.

Tax rules (per line item):
  * Food in a food-exempt state (CA, WA) -> no tax
  * Anything else in CA / WA             -> 8%
  * Everything else                      -> 5%

Members get a flat discount whenever the running total crosses the
threshold (see the note in ``compute_price``).
"""

FOOD_EXEMPT_STATES = ("CA", "WA")

IN_STATE_TAX_MULTIPLIER = 1.08     # CA / WA, non-food
DEFAULT_TAX_MULTIPLIER = 1.05      # everywhere else

MEMBER_DISCOUNT_THRESHOLD_CENTS = 5000
MEMBER_DISCOUNT_CENTS = 500


def _tax_multiplier(category, state):
    """Multiplier applied to a line's subtotal, or None when it is untaxed."""
    if state in FOOD_EXEMPT_STATES:
        if category == "food":
            return None
        return IN_STATE_TAX_MULTIPLIER
    return DEFAULT_TAX_MULTIPLIER


def _is_billable(item):
    return item.get("qty", 0) > 0 and item.get("unit_price_cents", 0) > 0


def _line_total_cents(item, state):
    subtotal = item["qty"] * item["unit_price_cents"]
    multiplier = _tax_multiplier(item.get("category"), state)
    if multiplier is None:
        # Untaxed lines are passed through as-is (no rounding step).
        return subtotal
    return int(subtotal * multiplier)


def compute_price(order):
    """Return the order total in cents (0 for an empty/missing order)."""
    if not order or not order.get("items"):
        return 0

    state = order.get("state")
    is_member = bool(order.get("member"))

    total = 0
    for item in order["items"]:
        if not _is_billable(item):
            continue

        total += _line_total_cents(item, state)

        # NOTE: preserved from the original implementation -- the member
        # discount is evaluated after *each* billable line, so it can be
        # applied more than once per order. Not an accident of refactoring.
        if is_member and total > MEMBER_DISCOUNT_THRESHOLD_CENTS:
            total -= MEMBER_DISCOUNT_CENTS

    return total
```

## What changed

- **Nesting flattened.** The two "nothing to price" cases became a single early `return 0`, and the per-item guards became a `continue` instead of two more levels of `if`. The loop body is now one screen-width statement deep.
- **Tax logic de-duplicated.** The four copies of the `state in ("CA", "WA")` branch collapsed into `_tax_multiplier`, which encodes the rule table once. Magic numbers (`1.05`, `1.08`, `5000`, `500`) are named constants.
- **Small helpers** (`_is_billable`, `_line_total_cents`) give names to the two concepts that were previously implicit in the condition/arithmetic.
- Signature, name, and return type are unchanged.

## Behavior preserved deliberately

Two quirks in the original looked like bugs but are behavior, so I kept them and flagged the riskier one in a comment:

1. **The member discount is applied inside the loop**, once per billable line, not once per order. An order with three lines that each keep the running total above 5000 gets 1500 off, not 500. Changing this would alter totals, so it stays.
2. **Food in CA/WA skips `int()`.** Every other branch wraps the arithmetic in `int(...)`; the exempt branch adds `qty * unit_price_cents` raw. With integer inputs the results are identical, but with float `qty` or prices the original returns a float for that path. `_line_total_cents` returns the subtotal unrounded in the untaxed case to match.

If either of those is actually a bug, it's a one-line fix from here — but it's a behavior change and belongs in a separate commit with its own test updates.