## `starter/pricing.py`

```python
"""Order pricing: line totals in cents, sales tax, and the member discount."""

# States where the seller collects local sales tax. Food is exempt there;
# everywhere else a flat rate applies to every category.
LOCAL_TAX_STATES = frozenset({"CA", "WA"})

UNTAXED_RATE = 1.00       # Food in a local-tax state.
LOCAL_TAX_RATE = 1.08     # Non-food in a local-tax state.
DEFAULT_TAX_RATE = 1.05   # Everything else, anywhere else.

MEMBER_DISCOUNT_THRESHOLD_CENTS = 5000
MEMBER_DISCOUNT_CENTS = 500


def _tax_rate_for(state, category):
    """Rate multiplier for one line item."""
    if state not in LOCAL_TAX_STATES:
        return DEFAULT_TAX_RATE
    if category == "food":
        return UNTAXED_RATE
    return LOCAL_TAX_RATE


def compute_price(order):
    """Return the order total in cents, or 0 if the order has no items."""
    if order is None or not order.get("items"):
        return 0

    state = order.get("state")
    is_member = order.get("member")

    total_cents = 0
    for item in order["items"]:
        if item.get("qty", 0) <= 0 or item.get("unit_price_cents", 0) <= 0:
            continue

        line_cents = item["qty"] * item["unit_price_cents"]
        rate = _tax_rate_for(state, item.get("category"))
        if rate == UNTAXED_RATE:
            # Added without int(), matching the original. Truncation is not a
            # no-op for a non-integer qty or unit price.
            total_cents += line_cents
        else:
            total_cents += int(line_cents * rate)

        # NOTE: the discount is applied per qualifying item, not once per
        # order, so a long order can subtract it repeatedly. Preserved from
        # the original — changing it changes totals.
        if is_member and total_cents > MEMBER_DISCOUNT_THRESHOLD_CENTS:
            total_cents -= MEMBER_DISCOUNT_CENTS

    return total_cents
```

## What changed

```text
[F5] pricing.py:1  Five levels of nesting around the real work
  if order is not None: / if order.get("items"): / for ... / if qty > 0: / if price > 0:
  → early return for the empty-order cases, `continue` guard for skipped items;
    the loop body is now at one level

[S1] pricing.py:8-16  Tax selection duplicated across four branches
  the CA/WA check appeared once per category, with 1.05 repeated in both
  → extracted `_tax_rate_for(state, category)`; the four-branch tree collapses
    to two rules

[C5] pricing.py:12-19  Unexplained literals 1.05, 1.08, 5000, 500
  → named constants with a comment on what each rate covers

[N3] pricing.py:5  `total` had no unit despite holding cents
  → `total_cents`; `line_cents` names the per-item subtotal (E1)

[C4] pricing.py:20  Per-item member discount looks like a bug but is behavior
  → NOTE marker so the next reader knows it was deliberate, not overlooked
```

Equivalence notes, since the constraint was exact behavior:

- `order is None or not order.get("items")` keeps the original's `AttributeError` on a truthy non-dict. `not order` would have swallowed it.
- The guard uses `or` in the original's short-circuit order, so a bad `qty` still raises before `unit_price_cents` is read.
- `state` and `member` are hoisted out of the loop; `order` is never mutated, so the values are identical each iteration.
- The untaxed branch still skips `int()`. `int(n * 1.0) == n` for ints under 2^53, but not for floats or very large ints, so folding it into the multiply path would have been a real change.

## What I left alone

- **The per-item member discount.** Almost certainly meant to be applied once per order. Fixing it changes totals, which is out of scope here (`X4`). It's flagged, not fixed.
- **`compute_price`'s name and signature**, and its dict-shaped `order` / `item` inputs, as instructed.
- **Silent skipping of zero-qty and zero-price items.** No caller can distinguish "skipped" from "priced at zero"; that's an interface question, not a readability one.
- **`unit_price_cents`, `qty`, `category`, `state`, `member` key names.** They're the external contract (`X3`).
- **Formatting beyond what the edits touched** — no formatter or linter config was in context, so I matched the file's existing style (`X5`).

I looked for `scripts/taorc_lint.py` under the standard skill roots; no such file is reachable from here, so step 4 was skipped rather than substituted with a different tool.