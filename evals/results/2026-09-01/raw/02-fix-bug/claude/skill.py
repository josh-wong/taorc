## Fix

`reserve()` added the reserved quantity instead of subtracting it, so every call grew the stock it was meant to draw down.

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

The diff is one character: `available + qty` → `available - qty` on line 17.

## What I deliberately did not change

- **`self.counts` and `qty`** — renaming is out of scope, and `counts` is the file's established vocabulary (`X2`, `X3`).
- **The missing docstrings on `reserve()` and `on_hand()`** — `reserve()`'s raise-on-insufficient-stock behavior is worth documenting for callers (`C14`), but adding it here would mix a readability change into a behavior fix (`X4`). Worth a follow-up.
- **`reserve()` accepts a negative `qty`**, which passes the `qty > available` guard and silently *increases* stock — the same symptom you reported, reachable by a different path. I left it alone because fixing it changes behavior beyond the bug you described. If callers can pass unvalidated quantities, this is worth a separate ticket.
- **No test added.** If you want one, `test_reserve_reduces_on_hand` and `test_repeated_reserve_does_not_increase_on_hand` would pin this down (`T3`).

I did not run `taorc_lint.py` — I don't have filesystem access in this exchange to check whether it exists under one of the skill roots. If it's installed, `python <root>/scripts/taorc_lint.py --changed` on this file should come back clean; the fix introduces no new names, comments, or branches.