#!/usr/bin/env python3
"""Tests for evals/score.py scoring helpers.

Covers reconstruct_edited_file, the M3 fix (#23): the diff-size metric must
measure the edit a completion represents, not whether the model echoed the
whole starter file or returned only the changed function.

Also covers findings_introduced, the M1 fix (#31, #34): a lint finding a
completion inherited unchanged from the scenario's starter is not charged to
the completion, but a fresh one on a line matching a starter finding the
completion deleted still is.

Uses stdlib unittest to match the rest of this repo's tests (see
scripts/tests/test_installer.py) -- nothing here depends on a test framework
beyond the standard library.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

EVALS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EVALS_ROOT))

from score import (  # noqa: E402
    SCORER_VERSION,
    committed_scorer_version,
    diff_line_count,
    extract_code,
    findings_introduced,
    reconstruct_edited_file,
)

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

    def test_helper_still_called_by_an_untouched_function_is_kept_not_deleted(self):
        """A fragment inlines a helper into one function but a different,
        untouched function still calls it. The helper sits inside the rewritten
        region and the fragment never names it, yet deleting it would break the
        surviving caller and inflate M3 for a deletion the model never made."""
        starter = '''\
"""Cart."""


def add_line(cart, sku, qty, amt):
    cart.append({"sku": sku, "qty": qty, "amt": amt})
    return cart


def line_total(line):
    return line["qty"] * line["amt"]


def cart_total(cart):
    return sum(line_total(line) for line in cart)


def receipt(cart):
    return [line_total(line) for line in cart]
'''
        inlines_into_cart_total_only = '''\
def add_line(cart, sku, qty, amt):
    cart.append({"sku": sku, "qty": qty, "amt": amt})
    return cart


def cart_total(cart):
    return sum(line["qty"] * line["amt"] for line in cart)
'''
        rebuilt = reconstruct_edited_file(starter, inlines_into_cart_total_only)

        self.assertIn("def line_total", rebuilt)
        self.assertIn("def receipt", rebuilt)

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


def _finding(rule_id: str, matched: str) -> dict:
    return {"id": rule_id, "matched": matched}


class FindingsIntroducedTest(unittest.TestCase):
    """findings_introduced drops the lint findings a completion carried over
    unchanged from the scenario's starter, so M1 measures the edit and stops
    rewarding an X2/X3 breach that renames a starter symbol to clear a finding
    (#31)."""

    def test_finding_inherited_unchanged_is_excluded(self):
        starter = [_finding("N1", "def process_data(data):")]
        completion = [_finding("N1", "def process_data(data):")]

        self.assertEqual(findings_introduced(completion, starter), [])

    def test_finding_on_a_name_the_completion_introduced_is_counted(self):
        starter = [_finding("N1", "def process_data(data):")]
        renamed_and_added_a_helper = [
            _finding("N1", "def process_data(data):"),
            _finding("N1", "def _tmp(payload):"),
        ]

        introduced = findings_introduced(renamed_and_added_a_helper, starter)

        self.assertEqual([f["matched"] for f in introduced], ["def _tmp(payload):"])

    def test_finding_reintroduced_into_a_rewritten_starter_function_is_counted(self):
        """The starter flags `result = {}` once. A completion that rewrites that
        function and writes `result = {}` again in it has reintroduced the name;
        multiset matching clears one inherited copy and counts the rest."""
        starter = [_finding("N1", "result = {}")]
        rewrote_the_function_and_kept_the_name = [
            _finding("N1", "result = {}"),
            _finding("N1", "result = {}"),
        ]

        introduced = findings_introduced(rewrote_the_function_and_kept_the_name, starter)

        self.assertEqual(introduced, [_finding("N1", "result = {}")])

    def test_new_violation_on_a_line_matching_a_deleted_starter_finding_is_counted(self):
        """The starter flags `data = []` inside a function the completion
        deletes outright; the completion writes an unrelated new function that
        also contains `data = []`. The deleted line is not retained, so the new
        finding is charged to the completion (#34)."""
        starter_source = (
            '"""Old module."""\n\n\n'
            "def summarise_orders(orders):\n"
            "    data = []\n"
            "    for order in orders:\n"
            "        data.append(order.total)\n"
            "    return sum(data) / len(data)\n"
        )
        completion_source = (
            '"""Old module."""\n\n\n'
            "def average_shipping_cost(shipments):\n"
            "    data = []\n"
            "    for shipment in shipments:\n"
            "        data.append(shipment.cost)\n"
            "    return sum(data) / len(data)\n"
        )
        starter = [{"id": "N1", "matched": "data = []", "line": 5}]
        completion = [{"id": "N1", "matched": "data = []", "line": 5}]

        introduced = findings_introduced(
            completion, starter, starter_source, completion_source
        )

        self.assertEqual(introduced, completion)

    def test_finding_on_a_retained_line_is_still_excluded_with_sources(self):
        """The completion leaves `process_data` untouched and edits a different
        function, so the inherited N1 on its signature is not charged."""
        starter_source = (
            "def process_data(data):\n"
            "    cleaned = [row for row in data if row]\n"
            "    return cleaned\n\n\n"
            "def report(rows):\n"
            "    print(len(rows))\n"
        )
        completion_source = (
            "def process_data(data):\n"
            "    cleaned = [row for row in data if row]\n"
            "    return cleaned\n\n\n"
            "def report(rows):\n"
            "    print(f'{len(rows)} rows')\n"
        )
        starter = [{"id": "N1", "matched": "def process_data(data):", "line": 1}]
        completion = [{"id": "N1", "matched": "def process_data(data):", "line": 1}]

        introduced = findings_introduced(
            completion, starter, starter_source, completion_source
        )

        self.assertEqual(introduced, [])

    def test_finding_on_a_line_kept_between_edited_neighbours_is_excluded(self):
        """The completion rewrites the lines above and below `tax = base *
        0.0825` but keeps that line byte-for-byte. difflib aligns it as a lone
        one-line block; because the enclosing `def` survived, the inherited
        finding on it is not charged (#31)."""
        starter_source = (
            "def monthly_charge(base):\n"
            "    setup = base * 0.05\n"
            "    tax = base * 0.0825\n"
            "    credit = base * 0.10\n"
            "    return base + tax\n"
        )
        completion_source = (
            "def monthly_charge(base):\n"
            "    setup = onboarding_fee(base)\n"
            "    tax = base * 0.0825\n"
            "    credit = loyalty_credit(base)\n"
            "    return round(base + tax, 2)\n"
        )
        starter = [{"id": "N1", "matched": "tax = base * 0.0825", "line": 3}]
        completion = [{"id": "N1", "matched": "tax = base * 0.0825", "line": 3}]

        introduced = findings_introduced(
            completion, starter, starter_source, completion_source
        )

        self.assertEqual(introduced, [])

    def test_same_line_but_a_different_rule_is_counted(self):
        starter = [_finding("N1", "value = payload.get(field)")]
        completion = [_finding("C1", "value = payload.get(field)")]

        self.assertEqual(findings_introduced(completion, starter), completion)

    def test_no_starter_scenario_keeps_every_finding(self):
        completion = [
            _finding("N1", "def handle(data):"),
            _finding("X7", "# Step 1: parse the request"),
        ]

        self.assertEqual(findings_introduced(completion, None), completion)
        self.assertEqual(findings_introduced(completion, []), completion)

    def test_a_returned_list_is_a_copy_not_the_input(self):
        completion = [_finding("N1", "def handle(data):")]

        self.assertIsNot(findings_introduced(completion, None), completion)


class CommittedScorerVersionTest(unittest.TestCase):
    def test_missing_file_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(committed_scorer_version(Path(tmp) / "scores.json"))

    def test_file_without_the_field_reads_as_version_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scores.json"
            path.write_text(json.dumps({"scores": {}}), encoding="utf-8")
            self.assertEqual(committed_scorer_version(path), 1)

    def test_stamped_file_reads_its_own_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scores.json"
            path.write_text(json.dumps({"scorer_version": 2, "scores": {}}), encoding="utf-8")
            self.assertEqual(committed_scorer_version(path), 2)


class ScorerFreezeTest(unittest.TestCase):
    """score.py stamps scores.json with SCORER_VERSION and refuses to overwrite
    a run scored under an earlier one without --rescore, so a metric
    redefinition (issue #31) never silently rewrites a published run."""

    def _run_dir(self, tmp: str) -> Path:
        run_dir = Path(tmp) / "run"
        cell = run_dir / "raw" / "10-de-slop" / "claude"
        cell.mkdir(parents=True)
        (cell / "baseline.py").write_text(
            "def process_data(data):\n    return {k: data[k] for k in data}\n",
            encoding="utf-8",
        )
        return run_dir

    def _score(self, run_dir: Path, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(EVALS_ROOT / "score.py"), "--run", str(run_dir), *extra],
            capture_output=True,
            text=True,
            check=True,
        )

    def test_a_fresh_run_is_stamped_with_the_current_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._run_dir(tmp)
            self._score(run_dir)
            document = json.loads((run_dir / "scores.json").read_text(encoding="utf-8"))
            self.assertEqual(document["scorer_version"], SCORER_VERSION)

    def test_a_run_scored_under_an_earlier_version_is_left_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._run_dir(tmp)
            scores_path = run_dir / "scores.json"
            frozen = json.dumps({"scorer_version": 1, "scores": {"published": "as run"}})
            scores_path.write_text(frozen, encoding="utf-8")

            completed = self._score(run_dir)

            self.assertEqual(scores_path.read_text(encoding="utf-8"), frozen)
            self.assertIn("stand as run", completed.stderr)

    def test_rescore_overwrites_an_earlier_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._run_dir(tmp)
            scores_path = run_dir / "scores.json"
            scores_path.write_text(
                json.dumps({"scorer_version": 1, "scores": {}}), encoding="utf-8"
            )

            self._score(run_dir, "--rescore")

            document = json.loads(scores_path.read_text(encoding="utf-8"))
            self.assertEqual(document["scorer_version"], SCORER_VERSION)
            self.assertIn("10-de-slop", document["scores"])


class ExtractCodeTest(unittest.TestCase):
    """extract_code picks which fenced block of a raw completion is scored.
    A skill-condition answer is often a short ```python block followed by a
    longer ```text findings list, so "longest block wins" scores the prose."""

    def test_matching_language_block_wins_over_a_longer_text_block(self):
        completion = (
            "Here is the cleaned-up function:\n\n"
            "```python\ndef total(cart):\n    return sum(item.price for item in cart)\n```\n\n"
            "Findings:\n\n```text\n"
            + "- renamed c to cart for clarity\n" * 20
            + "```\n"
        )
        self.assertIn("def total(cart):", extract_code(completion, ".py"))

    def test_answer_in_an_untagged_fence_wins_over_a_short_tagged_prose_block(self):
        completion = (
            "Summary:\n\n```text\nrenamed one variable\n```\n\n"
            "Full answer:\n\n```\n"
            "def total(cart):\n    return sum(item.price for item in cart if item.qty > 0)\n"
            "```\n"
        )
        self.assertIn("item.qty > 0", extract_code(completion, ".py"))

    def test_matching_language_block_wins_even_when_shorter_than_an_untagged_block(self):
        completion = (
            "```python\nx = 1\n```\n\n```\n" + "unrelated log output\n" * 10 + "```\n"
        )
        self.assertEqual(extract_code(completion, ".py").strip(), "x = 1")

    def test_version_tagged_python_fence_is_treated_as_the_code(self):
        completion = (
            "Summary:\n\n```\n" + "a note about the change\n" * 5 + "```\n\n"
            "```python3\ndef total(cart):\n    return sum(i.price for i in cart)\n```\n"
        )
        self.assertIn("def total(cart):", extract_code(completion, ".py"))

    def test_bare_code_with_no_fence_scores_the_whole_response(self):
        completion = "def total(cart):\n    return sum(item.price for item in cart)\n"
        self.assertEqual(extract_code(completion, ".py"), completion)

    def test_unusual_code_tag_wins_over_a_longer_prose_block(self):
        completion = (
            "Notes:\n\n```text\n" + "a line of explanation\n" * 20 + "```\n\n"
            "```python-repl\ndef total(cart):\n    return sum(i.price for i in cart)\n```\n"
        )
        self.assertIn("def total(cart):", extract_code(completion, ".py"))

    def test_when_every_block_is_prose_the_longest_one_wins(self):
        completion = (
            "```text\nshort note\n```\n\n```console\n" + "a longer log line\n" * 5 + "```\n"
        )
        self.assertIn("a longer log line", extract_code(completion, ".py"))


if __name__ == "__main__":
    unittest.main()
