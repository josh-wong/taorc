#!/usr/bin/env python3
"""Tests for evals/judge.py's judge-input preparation.

Covers code_as_left_on_disk, the M2 fix from MS7 (#9): a judge must compare
the file each completion leaves behind, not the fragment or full file the
model happened to print. Without it, following X1 on an edit task makes a
completion look shorter than its rival for reasons that have nothing to do
with readability.

Also covers starter_to_splice_onto, which decides where that reconstruction
is safe to apply at all -- a splice cannot express a deletion, so a
removal-shaped scenario must be judged as written.

Uses stdlib unittest to match the rest of this repo's tests (see
evals/tests/test_score.py).
"""

from __future__ import annotations

import dataclasses
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

EVALS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EVALS_ROOT))

from evallib.scenarios import load_all_scenarios  # noqa: E402
from judge import code_as_left_on_disk, run_judging, starter_to_splice_onto  # noqa: E402

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


FRAGMENT_ADDING_AN_IMPORT = '''\
Logging a skipped line needs the stdlib logger.

```python
import logging

logger = logging.getLogger(__name__)


def cart_total(cart):
    for line in cart:
        if line["qty"] < 0:
            logger.warning("negative qty on %s", line["sku"])
    return sum(line["qty"] * line["amt"] for line in cart)
```

`add_line` is unchanged.
'''


FRAGMENT_WITH_A_MAIN_GUARD = '''\
```python
def cart_total(cart):
    return sum(line["qty"] * line["amt"] for line in cart)


if __name__ == "__main__":
    print(cart_total([]))
```
'''


CART_STARTER_THAT_IMPORTS = '''\
"""Shopping cart."""

import json


def add_line(cart, sku, qty, amt):
    cart.append({"sku": sku, "qty": qty, "amt": amt})
    return cart


def cart_total(cart):
    return sum(line["qty"] * line["amt"] for line in cart)
'''


FRAGMENT_ADDING_A_FUTURE_IMPORT = '''\
```python
from __future__ import annotations


def cart_total(cart: list[dict]) -> int:
    return sum(line["qty"] * line["amt"] for line in cart)
```
'''


TIMEOUT_STARTER = '''\
def fetch_prices(client):
    timeout_secs = 30
    return client.get("/prices", timeout=timeout_secs)


def fetch_stock(client):
    timeout_secs = 30
    return client.get("/stock", timeout=timeout_secs)
'''


FRAGMENT_HOISTING_A_CONSTANT = '''\
Both callers waited the same 30 seconds, so the literal moves up.

```python
timeout_secs = 30


def fetch_prices(client):
    return client.get("/prices", timeout=timeout_secs)
```
'''


FRAGMENT_EXPLAINING_A_HOISTED_CONSTANT = '''\
```python
# The gateway drops idle sockets at 45s, so stay under it.
timeout_secs = 30


def fetch_prices(client):
    return client.get("/prices", timeout=timeout_secs)
```
'''


FRAGMENT_WITH_A_DISPATCH_TABLE_BELOW_ITS_FUNCTION = '''\
```python
def cart_total(cart):
    return sum(line["qty"] * line["amt"] for line in cart if line["qty"] > 0)


CART_OPERATIONS = {"total": cart_total}
```
'''


EXECUTABLE_STARTER = '''\
#!/usr/bin/env python3

import json


def report(rows):
    return json.dumps(rows)
'''


SHEBANG_ONLY_STARTER = '''\
#!/usr/bin/env python3


def add_line(cart, sku, qty, amt):
    cart.append({"sku": sku, "qty": qty, "amt": amt})
    return cart


def cart_total(cart):
    return sum(line["qty"] * line["amt"] for line in cart)
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

    def test_fragment_is_judged_with_the_imports_it_added(self):
        judged = code_as_left_on_disk(
            self.completion_file(FRAGMENT_ADDING_AN_IMPORT), ".py", CART_STARTER
        )

        self.assertIn("import logging", judged)
        self.assertIn("logger = logging.getLogger(__name__)", judged)
        self.assertIn("logger.warning", judged)

    def test_merged_import_lands_above_the_first_definition(self):
        judged = code_as_left_on_disk(
            self.completion_file(FRAGMENT_ADDING_AN_IMPORT), ".py", CART_STARTER
        )
        lines = judged.splitlines()

        self.assertLess(
            lines.index("import logging"),
            lines.index("def add_line(cart, sku, qty, amt):"),
        )

    def test_merged_import_is_kept_off_the_line_above_it(self):
        judged = code_as_left_on_disk(
            self.completion_file(FRAGMENT_ADDING_AN_IMPORT), ".py", CART_STARTER
        )
        lines = judged.splitlines()

        self.assertEqual(lines[lines.index("import logging") - 1], "")
        self.assertEqual(lines[lines.index("logger = logging.getLogger(__name__)") - 1], "")

    def test_main_guard_is_left_out_rather_than_hoisted_above_its_function(self):
        judged = code_as_left_on_disk(
            self.completion_file(FRAGMENT_WITH_A_MAIN_GUARD), ".py", CART_STARTER
        )

        self.assertNotIn("__main__", judged)
        self.assertIn("def cart_total", judged)

    def test_merged_future_import_leaves_a_file_that_compiles(self):
        """The starter imports before its first definition, so merging below
        that prologue would put the future import where only ast.parse accepts
        it -- 09-add-error-handling's starter opens the same way."""
        judged = code_as_left_on_disk(
            self.completion_file(FRAGMENT_ADDING_A_FUTURE_IMPORT),
            ".py",
            CART_STARTER_THAT_IMPORTS,
        )
        lines = judged.splitlines()

        compile(judged, "<judged>", "exec")
        self.assertLess(
            lines.index("from __future__ import annotations"), lines.index("import json")
        )

    def test_hoisted_constant_survives_a_body_line_that_reads_the_same(self):
        """The starter's other function still assigns `timeout_secs = 30`
        indented, so comparing against every line of the spliced file would
        drop the module-level constant and leave the rewrite undefined."""
        judged = code_as_left_on_disk(
            self.completion_file(FRAGMENT_HOISTING_A_CONSTANT), ".py", TIMEOUT_STARTER
        )

        self.assertIn("timeout_secs = 30", judged.splitlines())

    def test_hoisted_constant_keeps_the_comment_written_above_it(self):
        """The comment is the `why` C5 asks for, and dropping it grades the
        completion on the C rubric for a comment it did write."""
        judged = code_as_left_on_disk(
            self.completion_file(FRAGMENT_EXPLAINING_A_HOISTED_CONSTANT),
            ".py",
            TIMEOUT_STARTER,
        )
        lines = judged.splitlines()

        self.assertEqual(
            lines[lines.index("timeout_secs = 30") - 1],
            "# The gateway drops idle sockets at 45s, so stay under it.",
        )

    def test_assignment_below_the_completions_functions_is_left_out_not_hoisted(self):
        """A dispatch table naming the functions above it resolves nothing once
        the merge lifts it over them -- the NameError the type filter alone was
        argued to prevent."""
        judged = code_as_left_on_disk(
            self.completion_file(FRAGMENT_WITH_A_DISPATCH_TABLE_BELOW_ITS_FUNCTION),
            ".py",
            CART_STARTER,
        )

        exec(compile(judged, "<judged>", "exec"), {})
        self.assertNotIn("CART_OPERATIONS", judged)

    def test_merged_future_import_lands_below_the_starters_shebang(self):
        """Inserted at line 1 instead, the shebang becomes an ordinary comment
        and the file is no longer executable as the script it was."""
        judged = code_as_left_on_disk(
            self.completion_file(FRAGMENT_ADDING_A_FUTURE_IMPORT), ".py", EXECUTABLE_STARTER
        )
        lines = judged.splitlines()

        self.assertEqual(lines[0], "#!/usr/bin/env python3")
        self.assertLess(
            lines.index("from __future__ import annotations"), lines.index("import json")
        )

    def test_merged_import_lands_below_the_starters_shebang(self):
        judged = code_as_left_on_disk(
            self.completion_file(FRAGMENT_ADDING_AN_IMPORT), ".py", SHEBANG_ONLY_STARTER
        )
        lines = judged.splitlines()

        self.assertEqual(lines[0], "#!/usr/bin/env python3")
        self.assertLess(lines.index("import logging"), lines.index("def cart_total(cart):"))

    def test_full_file_completion_does_not_get_a_second_docstring(self):
        rewritten = CART_STARTER.replace("amt", "unit_price_cents")

        judged = code_as_left_on_disk(self.completion_file(rewritten), ".py", CART_STARTER)

        self.assertEqual(judged.count('"""Shopping cart."""'), 1)

    def test_scenario_with_no_starter_is_judged_as_written(self):
        from_scratch = "def quote_shipping_cost(weight_kg):\n    return int(50 * weight_kg)\n"

        judged = code_as_left_on_disk(self.completion_file(from_scratch), ".py", None)

        self.assertEqual(judged, from_scratch)


SLOP_STARTER = '''\
"""Report builder."""


def helper_slop(rows):
    # Step 1: do the thing
    return [row for row in rows if row]


def summarize(rows):
    return len(helper_slop(rows))
'''

DELETION_COMPLETION = '''\
Removed the pointless helper and its narration.

```python
def summarize(rows):
    return len([row for row in rows if row])
```
'''


class StarterToSpliceOntoTest(unittest.TestCase):
    def setUp(self):
        self.scenarios = {s.id: s for s in load_all_scenarios()}

    def test_additive_edit_scenario_splices_onto_its_starter(self):
        starter = starter_to_splice_onto(self.scenarios["03-add-feature"])

        self.assertIsNotNone(starter)

    def test_deletion_scenario_is_judged_as_written_not_spliced(self):
        self.assertIsNone(starter_to_splice_onto(self.scenarios["10-de-slop"]))

    def test_from_scratch_scenario_has_nothing_to_splice_onto(self):
        self.assertIsNone(starter_to_splice_onto(self.scenarios["01-implement-function"]))

    def test_measured_scenario_with_no_matching_starter_warns_before_judging_as_written(self):
        renamed = dataclasses.replace(
            self.scenarios["03-add-feature"], output_file="renamed_by_mistake.py"
        )
        warnings = io.StringIO()

        with redirect_stderr(warnings):
            starter = starter_to_splice_onto(renamed)

        self.assertIsNone(starter)
        self.assertIn("WARNING 03-add-feature", warnings.getvalue())

    def test_splicing_a_deletion_would_restore_the_deleted_code(self):
        """Why the gate above exists: reconstruct_edited_file has no way to
        express a removed definition, so splicing a de-slop completion hands
        the judge back the slop the completion correctly deleted."""
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        completion = Path(scratch.name) / "completion.py"
        completion.write_text(DELETION_COMPLETION, encoding="utf-8")

        spliced = code_as_left_on_disk(completion, ".py", SLOP_STARTER)
        as_written = code_as_left_on_disk(completion, ".py", None)

        self.assertIn("def helper_slop", spliced)
        self.assertIn("# Step 1: do the thing", spliced)
        self.assertNotIn("def helper_slop", as_written)


class UndecidablePairTest(unittest.TestCase):
    def test_leftover_judgment_files_for_a_skipped_pair_are_named_in_the_summary(self):
        """Skipping a pair leaves the summary counting fewer judgments than
        judgments/ holds files. Without the excluded list the two artifacts
        disagree with no marker in either, which is what R7.4 traceability
        cannot afford."""
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        run_dir = Path(scratch.name)
        model_dir = run_dir / "raw" / "03-add-feature" / "claude"
        model_dir.mkdir(parents=True)
        both_conditions_left = "def unchanged(cart):\n    return cart\n"
        (model_dir / "baseline.py").write_text(both_conditions_left, encoding="utf-8")
        (model_dir / "skill.py").write_text(both_conditions_left, encoding="utf-8")
        from_an_earlier_pass = (
            run_dir / "judgments" / "03-add-feature__claude__judge-gpt__pass1.json"
        )
        from_an_earlier_pass.parent.mkdir(parents=True)
        from_an_earlier_pass.write_text("{}", encoding="utf-8")

        outcome = run_judging(run_dir, force=False, seed=None, label=None)

        self.assertEqual(outcome["undecidable_pairs"], ["03-add-feature/claude"])
        self.assertEqual(outcome["excluded_judgment_files"], [from_an_earlier_pass.name])
        self.assertTrue(from_an_earlier_pass.exists())
        self.assertEqual(outcome["preference_counts"]["skill"], 0)


if __name__ == "__main__":
    unittest.main()
