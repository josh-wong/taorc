## Fix

One line. `reserve()` added the reserved quantity instead of subtracting it.

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

The diff is `available + qty` → `available - qty`.

The guard clause above it was already correct and is what keeps the count from going negative, so nothing else needed to change: after the guard, `qty <= available`, so `available - qty >= 0`.

## What I deliberately did not change

- **`counts` and `qty`.** `counts` is on the vague side for a dict keyed by SKU, and `qty` is an abbreviation. Both are used consistently across all four methods, so they're the file's established vocabulary (`X2`), and renaming them would widen a bug-fix diff (`X1`).
- **`Inventory.reserve()`'s signature and the `ValueError`.** Public surface; not mine to touch unasked (`X3`).
- **No comment explaining the fix.** The corrected line says what it does, and a `# subtract, not add` note would only restate it (`C1`).
- **No test added.** You asked for the bug fix only. If you do want one, the regression this class needs is roughly `receive("widget", 10)`, `reserve("widget", 3)`, assert `on_hand("widget") == 7` — say the word and I'll add it as a separate step (`X4`).

I did not run `scripts/taorc_lint.py`; I have no filesystem access in this conversation to check whether it exists here.