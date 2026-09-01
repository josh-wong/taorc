#!/usr/bin/env python3
"""Tests for evals/judge.py's judge-input preparation.

Covers code_as_left_on_disk, the M2 fix from MS7 (#9): a judge must compare
the file each completion leaves behind, not the fragment or full file the
model happened to print. Without it, following X1 on an edit task makes a
completion look shorter than its rival for reasons that have nothing to do
with readability.

Uses stdlib unittest to match the rest of this repo's tests (see
evals/tests/test_score.py).
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

EVALS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EVALS_ROOT))

from judge import code_as_left_on_disk  # noqa: E402

CART_STARTER = '''\
"""Shopping cart."""


def add_line(cart, sku, qty, amt):
    cart.append({"sku": sku, "qty": qty, "amt": amt})
    return cart


def cart_total(cart):
    return sum(line["qty"] * line["amt"] for line in cart)
'''

FRAGMENT_COMPLETION = '''\
Here is the new function.

```python
def remove_line(cart, sku):
    for index, line in enumerate(cart):
        if line["sku"] == sku:
            del cart[index]
            break
    return cart
```

I left `add_line` and `cart_total` alone.
'''


class CodeAsLeftOnDiskTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.scratch_dir = Path(scratch.name)

    def completion_file(self, text: str) -> Path:
        path = self.scratch_dir / "completion.py"
        path.write_text(text, encoding="utf-8")
        return path

    def test_fragment_completion_is_judged_as_the_whole_edited_file(self):
        completion = self.completion_file(FRAGMENT_COMPLETION)

        judged = code_as_left_on_disk(completion, ".py", CART_STARTER)

        self.assertIn("def add_line", judged)
        self.assertIn("def cart_total", judged)
        self.assertIn("def remove_line", judged)

    def test_full_file_completion_is_judged_unchanged(self):
        rewritten = CART_STARTER.replace("amt", "unit_price_cents")

        judged = code_as_left_on_disk(self.completion_file(rewritten), ".py", CART_STARTER)

        self.assertEqual(judged, rewritten)

    def test_scenario_with_no_starter_is_judged_as_written(self):
        from_scratch = "def quote_shipping_cost(weight_kg):\n    return int(50 * weight_kg)\n"

        judged = code_as_left_on_disk(self.completion_file(from_scratch), ".py", None)

        self.assertEqual(judged, from_scratch)


if __name__ == "__main__":
    unittest.main()
