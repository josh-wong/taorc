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
        full_file = (
            "import json\nimport os\n\n\ndef load_config(path):\n"
            "    return json.load(open(os.path.expanduser(path)))\n"
        )
        self.assertEqual(reconstruct_edited_file(starter, full_file), full_file)

    def test_fragment_dropping_a_helper_between_rewrites_records_the_deletion(self):
        starter = '''\
"""Cart."""


def add_line(cart, sku, qty, amt):
    cart.append({"sku": sku, "qty": qty, "amt": amt})
    return cart


def line_total(line):
    return line["qty"] * line["amt"]


def cart_total(cart):
    return sum(line_total(line) for line in cart)
'''
        inlines_the_helper = '''\
def add_line(cart, sku, qty, amt):
    cart.append({"sku": sku, "qty": qty, "amt": amt})
    return cart


def cart_total(cart):
    return sum(line["qty"] * line["amt"] for line in cart)
'''
        rebuilt = reconstruct_edited_file(starter, inlines_the_helper)

        self.assertNotIn("def line_total", rebuilt)
        self.assertIn("def add_line", rebuilt)

    def test_fragment_omitting_a_trailing_definition_keeps_it(self):
        fragment = "def add_line(cart, sku, qty, amt):\n    return cart\n"
        rebuilt = reconstruct_edited_file(CART_STARTER, fragment)

        self.assertIn("def cart_total", rebuilt)

    def test_single_definition_fragment_that_adds_its_own_import_is_still_spliced(self):
        """Scenario 09 variant: the completion redefines the one function AND
        carries a prologue line of its own (a new import), without echoing the
        starter's imports. It is a fragment, not a rewrite -- diffing it raw
        would count every un-echoed starter import as a deletion (#26)."""
        starter = (
            "import json\nfrom pathlib import Path\n\n\n"
            "def load_config(path):\n    return json.loads(Path(path).read_text())\n"
        )
        fragment_adding_an_import = (
            "import logging\n\n\n"
            "def load_config(path):\n"
            "    try:\n"
            "        return json.loads(Path(path).read_text())\n"
            "    except FileNotFoundError:\n"
            "        logging.warning('missing config')\n"
            "        return {}\n"
        )
        rebuilt = reconstruct_edited_file(starter, fragment_adding_an_import)

        self.assertIn("import json", rebuilt)
        self.assertIn("from pathlib import Path", rebuilt)
        self.assertLessEqual(diff_line_count(starter, rebuilt), 6)

    def test_full_file_rewrite_that_drops_the_module_docstring_keeps_the_deletion(self):
        """A whole-file completion redefines every name and echoes the two
        functions verbatim but omits the module docstring. That deletion is
        the model's, so it must reach M3 rather than be spliced back."""
        rewrite_without_docstring = '''\
def add_line(cart, sku, qty, amt):
    cart.append({"sku": sku, "qty": qty, "amt": amt})
    return cart


def cart_total(cart):
    return sum(line["qty"] * line["amt"] for line in cart)
'''
        rebuilt = reconstruct_edited_file(CART_STARTER, rewrite_without_docstring)

        self.assertNotIn("Shopping cart", rebuilt)

    def test_fragment_of_one_class_method_is_spliced_into_the_class(self):
        """Scenario 02: the starter is a single class with no top-level
        function. A completion that returns only the corrected method, dedented
        to column 0, must land inside the class -- not be appended as a stray
        module-level function that leaves the bug in place."""
        starter = '''\
"""Inventory."""


class Inventory:
    def __init__(self):
        self.items = {}

    def reserve(self, sku, qty):
        self.items[sku] = self.items.get(sku, 0) - qty
        return self.items[sku] > 0
'''
        corrected_method = '''\
def reserve(self, sku, qty):
    if self.items.get(sku, 0) < qty:
        return False
    self.items[sku] -= qty
    return True
'''
        rebuilt = reconstruct_edited_file(starter, corrected_method)

        self.assertIn("    def reserve(self, sku, qty):", rebuilt)
        self.assertNotIn("\ndef reserve", rebuilt)
        self.assertEqual(rebuilt.count("def reserve"), 1)
        self.assertIn("        if self.items.get(sku, 0) < qty:", rebuilt)
        # The edit is the method body, not the whole class.
        self.assertLessEqual(diff_line_count(starter, rebuilt), 8)

    def test_full_file_rewrite_that_renames_a_trailing_definition_is_scored_as_is(self):
        """Scenario 03: the completion returns the whole file but renames the
        last function. It no longer redefines every starter name, yet it
        carries the starter's whole prologue -- so it is a rewrite, and the old
        name must not be spliced back alongside the new one."""
        rewrite_renaming_total = '''\
"""Shopping cart."""


def add_line(cart, sku, qty, amt):
    cart.append({"sku": sku, "qty": qty, "amt": amt})
    return cart


def total_cents(cart):
    return sum(line["qty"] * line["amt"] for line in cart)
'''
        rebuilt = reconstruct_edited_file(CART_STARTER, rewrite_renaming_total)

        self.assertEqual(rebuilt, rewrite_renaming_total)
        self.assertNotIn("def cart_total", rebuilt)

    def test_inlined_helper_named_only_in_a_comment_is_still_recorded_as_removed(self):
        """A fragment that inlines a helper and mentions it in a comment has
        still deleted it -- a substring match in the comment must not keep the
        dead function spliced back in."""
        starter = '''\
"""Cart."""


def add_line(cart, sku, qty, amt):
    cart.append({"sku": sku, "qty": qty, "amt": amt})
    return cart


def line_total(line):
    return line["qty"] * line["amt"]


def cart_total(cart):
    return sum(line_total(line) for line in cart)
'''
        inlines_with_a_comment = '''\
def add_line(cart, sku, qty, amt):
    cart.append({"sku": sku, "qty": qty, "amt": amt})
    return cart


def cart_total(cart):
    # inlined line_total for readability
    return sum(line["qty"] * line["amt"] for line in cart)
'''
        rebuilt = reconstruct_edited_file(starter, inlines_with_a_comment)

        self.assertNotIn("def line_total", rebuilt)

    def test_whole_file_rewrite_of_every_function_that_drops_the_docstring_keeps_the_deletion(self):
        """The completion rewrites the body of every starter function -- so no
        definition is echoed verbatim -- and omits the module docstring. It is
        still a whole-file answer, and the dropped docstring must reach M3."""
        rewrite_editing_every_function = '''\
def add_line(cart, sku, qty, amt):
    cart.append({"sku": sku, "qty": qty, "amt": amt, "note": ""})
    return cart


def cart_total(cart):
    return sum(line["qty"] * line["amt"] for line in cart if line["qty"] > 0)
'''
        rebuilt = reconstruct_edited_file(CART_STARTER, rewrite_editing_every_function)

        self.assertEqual(rebuilt, rewrite_editing_every_function)
        self.assertNotIn("Shopping cart", rebuilt)


if __name__ == "__main__":
    unittest.main()
