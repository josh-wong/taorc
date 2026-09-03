```python
def compute_price(order):
    if order is None:
        return 0

    if not order.get("items"):
        return 0

    totalCents = 0

    for item in order["items"]:
        itemQty = item.get("qty", 0)
        itemUnitPriceCents = item.get("unit_price_cents", 0)

        if itemQty <= 0 or itemUnitPriceCents <= 0:
            continue

        isFoodItem = item.get("category") == "food"
        isWestCoastState = order.get("state") in ("CA", "WA")

        if isFoodItem:
            if isWestCoastState:
                lineTotalCents = itemQty * itemUnitPriceCents
            else:
                lineTotalCents = int(itemQty * itemUnitPriceCents * 1.05)
        else:
            if isWestCoastState:
                lineTotalCents = int(itemQty * itemUnitPriceCents * 1.08)
            else:
                lineTotalCents = int(itemQty * itemUnitPriceCents * 1.05)

        totalCents += lineTotalCents

        if order.get("member") and totalCents > 5000:
            totalCents -= 500

    return totalCents
```