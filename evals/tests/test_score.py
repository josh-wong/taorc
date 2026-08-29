#!/usr/bin/env python3
"""Tests for evals/score.py scoring helpers.

Covers reconstruct_edited_file, the M3 fix (#23): the diff-size metric must
measure the edit a completion represents, not whether the model echoed the
whole starter file or returned only the changed function.

Uses stdlib unittest to match the rest of this repo's tests (see
scripts/tests/test_installer.py) -- nothing here depends on a test framework
beyond the standard library.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

EVALS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EVALS_ROOT))

from score import diff_line_count, reconstruct_edited_file  # noqa: E402

CART_STARTER = '''\
"""Shopping cart."""


def add_line(cart, sku, qty, amt):
    cart.append({"sku": sku, "qty": qty, "amt": amt})
    return cart


def cart_total(cart):
    return sum(line["qty"] * line["amt"] for line in cart)
'''

REMOVE_LINE_FRAGMENT = '''\
def remove_line(cart, sku):
    for index, line in enumerate(cart):
        if line["sku"] == sku:
            del cart[index]
            return cart
    return cart
'''


class ReconstructEditedFileTest(unittest.TestCase):
    def test_fragment_adding_a_function_scores_only_the_addition(self):
        rebuilt = reconstruct_edited_file(CART_STARTER, REMOVE_LINE_FRAGMENT)

        self.assertIn("def add_line", rebuilt)
        self.assertIn("def cart_total", rebuilt)
        self.assertTrue(rebuilt.index("def cart_total") < rebuilt.index("def remove_line"))
        added_lines = diff_line_count(CART_STARTER, rebuilt)
        self.assertLessEqual(added_lines, len(REMOVE_LINE_FRAGMENT.splitlines()) + 2)

    def test_fragment_redefining_one_function_leaves_the_rest_untouched(self):
        changed_total = '''\
def cart_total(cart):
    return sum(line["qty"] * line["amt"] for line in cart if line["qty"] > 0)
'''
        rebuilt = reconstruct_edited_file(CART_STARTER, changed_total)

        self.assertIn('if line["qty"] > 0', rebuilt)
        self.assertEqual(rebuilt.count("def cart_total"), 1)
        self.assertEqual(diff_line_count(CART_STARTER, rebuilt), 2)

    def test_full_file_rewrite_is_scored_as_is(self):
        full_file = CART_STARTER + "\n\n" + REMOVE_LINE_FRAGMENT
        rebuilt = reconstruct_edited_file(CART_STARTER, full_file)

        self.assertEqual(rebuilt, full_file)

    def test_two_completions_making_the_same_edit_score_the_same(self):
        as_fragment = reconstruct_edited_file(CART_STARTER, REMOVE_LINE_FRAGMENT)
        as_full_file = reconstruct_edited_file(
            CART_STARTER, CART_STARTER + "\n\n" + REMOVE_LINE_FRAGMENT
        )

        self.assertEqual(
            diff_line_count(CART_STARTER, as_fragment),
            diff_line_count(CART_STARTER, as_full_file),
        )

    def test_unparseable_completion_falls_back_to_the_raw_text(self):
        broken = "def remove_line(cart, sku:\n    return cart"
        self.assertEqual(reconstruct_edited_file(CART_STARTER, broken), broken)


if __name__ == "__main__":
    unittest.main()
