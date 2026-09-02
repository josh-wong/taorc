## The bug

`reserve()` computes the correct guard (`qty > available` → error), but then writes back `available + qty` instead of `available - qty`. So a reservation *adds* stock rather than removing it, which is why repeated calls make `on_hand()` climb.

## The fix

```python
# starter/inventory.py
"""Track stock levels for a small warehouse."""


class Inventory:
    def __init__(self):
        self.counts = {}

    def receive(self, sku, qty):
        self.counts[sku] = self.counts.get(sku, 0) + qty

    def reserve(self, sku, qty):
        available = self.counts.get(sku, 0)
        if qty > available:
            raise ValueError(f"cannot reserve {qty} of {sku}, only {available} available")
        self.counts[sku] = available - qty

    def on_hand(self, sku):
        return self.counts.get(sku, 0)
```

The only change is the single character on the assignment line in `reserve()`: `available + qty` → `available - qty`.

## Quick sanity check

```
inv.receive("widget", 10)   -> counts["widget"] == 10
inv.reserve("widget", 3)    -> counts["widget"] == 7
inv.reserve("widget", 3)    -> counts["widget"] == 4
inv.reserve("widget", 5)    -> ValueError: cannot reserve 5 of widget, only 4 available
```

`on_hand()` now decreases monotonically across reservations, and the guard still prevents over-reserving (it was already comparing against the right value — it just wasn't being honored by the write-back).

I left everything else alone: no renames, no restructuring, no changes to `receive()`, `on_hand()`, or the error message.