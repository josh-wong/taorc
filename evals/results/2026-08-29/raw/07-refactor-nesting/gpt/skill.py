Here’s a refactor that keeps `compute_price`’s behavior identical while reducing nesting and centralizing the tax-rate logic:

```python
def compute_price(order):
    if order is None:
        return 0

    items = order.get("items")
    if not items:
        return 0

    totalCents = 0
    isMember = order.get("member")
    state = order.get("state")

    for item in items:
        quantity = item.get("qty", 0)
        unitPriceCents = item.get("unit_price_cents", 0)

        if quantity <= 0 or unitPriceCents <= 0:
            continue

        isFood = item.get("category") == "food"
        isWestCoast = state in ("CA", "WA")

        if isFood and isWestCoast:
            lineTotalCents = quantity * unitPriceCents
        elif isFood and not isWestCoast:
            lineTotalCents = int(quantity * unitPriceCents * 1.05)
        elif not isFood and isWestCoast:
            lineTotalCents = int(quantity * unitPriceCents * 1.08)
        else:
            lineTotalCents = int(quantity * unitPriceCents * 1.05)

        totalCents += lineTotalCents

        if isMember and totalCents > 5000:
            totalCents -= 500

    return totalCents
```