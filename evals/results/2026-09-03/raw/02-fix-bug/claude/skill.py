## The fix

`reserve()` adds the reserved quantity back into stock instead of taking it out.

```python
# starter/inventory.py
     def reserve(self, sku, qty):
         available = self.counts.get(sku, 0)
         if qty > available:
             raise ValueError(f"cannot reserve {qty} of {sku}, only {available} available")
-        self.counts[sku] = available + qty
+        self.counts[sku] = available - qty
```

That is the entire change — one operator. The guard above it was already correct, which is why the bug shows up as growth rather than as a negative balance: every call passes validation, then adds.

Quick sanity check of the corrected behavior:

```python
inv = Inventory()
inv.receive("widget", 10)
inv.reserve("widget", 3)   # on_hand -> 7
inv.reserve("widget", 3)   # on_hand -> 4
inv.reserve("widget", 5)   # ValueError: cannot reserve 5 of widget, only 4 available
```

## What I deliberately left alone

- **No comment on the fixed line.** `available - qty` says what it does; a comment there would only restate it (`C1`).
- **No docstring added to `reserve()`.** It would be genuinely useful to a caller to state the `ValueError` contract (`C14`), but this task was a one-line behavior fix and a docstring is a separate, non-behavioral change (`X1`, `X4`). Worth doing on its own if you want it.
- **`counts`, `sku`, `qty`, `available` all kept.** They match each other and the file's existing vocabulary (`X2`), and `Inventory` plus its methods are public surface (`X3`).
- **`if qty > available` left as written.** It reads naturally next to the error message that follows it; flipping it would be churn, not clarity.

One thing I noticed and did not touch: the class has no way to release a reservation, so `reserve()` is effectively a permanent decrement rather than a hold. That may be intentional for a small warehouse, but if reservations are supposed to be undoable, that is a design gap rather than a bug in this method.