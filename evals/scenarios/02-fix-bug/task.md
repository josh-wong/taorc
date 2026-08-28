`starter/inventory.py` has a bug: `Inventory.reserve()` is meant to remove
stock from what's available, but calling it repeatedly increases `on_hand()`
instead of decreasing it. Fix the bug.

Fix only the bug. Do not rename anything, restructure the class, or touch
code that isn't part of the fix.
