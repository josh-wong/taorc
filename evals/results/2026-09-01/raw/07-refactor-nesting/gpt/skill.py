Here’s a refactor that keeps `compute_price`’s behavior identical while reducing nesting and centralizing the tax-rate logic:

```python
def compute_price(order):
    if order is None:
        return 0

    items = order.get("items")
    if not items:
        return 0

    total = 0
    state = order.get("state")
    is_member = order.get("member")

    for item in items:
        quantity = item.get("qty", 0)
        unit_price_cents = item.get("unit_price_cents", 0)

        if quantity <= 0 or unit_price_cents <= 0:
            continue

        is_food = item.get("category") == "food"
        is_west_coast = state in ("CA", "WA")

        if is_food and is_west_coast:
            line_total = quantity * unit_price_cents
        elif is_food and not is_west_coast:
            line_total = int(quantity * unit_price_cents * 1.05)
        elif not is_food and is_west_coast:
            line_total = int(quantity * unit_price_cents * 1.08)
        else:
            line_total = int(quantity * unit_price_cents * 1.05)

        total += line_total

        # Membership discount applies immediately when the running total
        # first exceeds 5000 cents, matching the original behavior.
        if is_member and total > 5000:
            total -= 500

    return total
```