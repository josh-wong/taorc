Here’s a refactored version that keeps `compute_price`’s behavior identical, but flattens the nesting and centralizes the tax-rate logic:

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
        qty = item.get("qty", 0)
        unit_price = item.get("unit_price_cents", 0)

        if qty <= 0 or unit_price <= 0:
            continue

        is_food = item.get("category") == "food"

        if is_food:
            if state in ("CA", "WA"):
                line_total = qty * unit_price
            else:
                line_total = int(qty * unit_price * 1.05)
        else:
            if state in ("CA", "WA"):
                line_total = int(qty * unit_price * 1.08)
            else:
                line_total = int(qty * unit_price * 1.05)

        total += line_total

        if is_member and total > 5000:
            total -= 500

    return total
```