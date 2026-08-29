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

    def test_single_definition_starter_still_splices_a_bare_fragment(self):
        """Scenario 09: the starter defines one function, so any completion
        redefines every name -- the reconstruction must still keep the
        starter's imports rather than score the fragment raw."""
        starter = '''\
import json
from pathlib import Path


def load_config(path):
    return json.loads(Path(path).read_text())
'''
        fragment_dropping_imports = '''\
def load_config(path):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        raise SystemExit(f"no config at {path}")
'''
        rebuilt = reconstruct_edited_file(starter, fragment_dropping_imports)

        self.assertIn("import json", rebuilt)
        self.assertIn("from pathlib import Path", rebuilt)
        # The edit is the try/except, not the two dropped import lines.
        self.assertLessEqual(diff_line_count(starter, rebuilt), 5)

    def test_single_definition_full_file_rewrite_is_scored_as_is(self):
        starter = "import json\n\n\ndef load_config(path):\n    return json.load(open(path))\n"
        full_file = "import json\nimport os\n\n\ndef load_config(path):\n    return json.load(open(os.path.expanduser(path)))\n"
        self.assertEqual(reconstruct_edited_file(starter, full_file), full_file)


if __name__ == "__main__":
    unittest.main()
