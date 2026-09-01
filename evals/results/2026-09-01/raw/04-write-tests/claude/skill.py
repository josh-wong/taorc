```python
# test_discount.py
"""Tests for apply_discount."""

import pytest

from starter.discount import apply_discount


def test_subtracts_percentage_when_no_cap():
    assert apply_discount(10_000, 25) == 7_500


def test_discount_is_limited_to_cap():
    # 50% of 10,000 would be 5,000 off, but the cap allows only 1,000.
    assert apply_discount(10_000, 50, cap_cents=1_000) == 9_000


def test_zero_percent_leaves_total_unchanged():
    assert apply_discount(10_000, 0) == 10_000


def test_hundred_percent_discounts_entire_total():
    assert apply_discount(10_000, 100) == 0


@pytest.mark.parametrize("percent_off", [-1, 101])
def test_percent_off_outside_zero_to_hundred_raises(percent_off):
    with pytest.raises(ValueError, match="between 0 and 100"):
        apply_discount(10_000, percent_off)
```

**Notes on the choices**

- Test names state the situation and the expected outcome, so a failure line in CI is readable without opening the file (`T3`).
- Every number a test is *about* is inline in the assertion — no fixtures or module-level constants to chase (`T1`). `10_000` is reused as an uninteresting stand-in for "some total"; the varying value is the one the test name talks about.
- `10_000` with `25` and `50` divides evenly, so no reader has to reason about the `//` floor division to check the expected value (`T2`).
- Plain `assert a == b` rather than a helper, because pytest's rewriting already prints both sides on failure (`T4`).
- The one comment explains arithmetic the code doesn't state — why 9,000 and not 5,000 (`C15`). The other tests get none; their names already say it (`C1`).
- The two invalid inputs are parametrized rather than split, since they're one behavior at two boundaries (`T5`), and `match=` pins the failure to *this* `ValueError` rather than any exception the function might grow later.

**What I did not do**

- No test for a cap that's larger than the discount (cap present but not binding), no test for rounding when `total_cents * percent_off` isn't divisible by 100 (e.g. `apply_discount(999, 33)`), and no test for a negative or zero `cap_cents`. All three are real gaps, but they're outside the four cases you listed (`X1`). Say the word and I'll add them.
- I didn't touch `starter/discount.py`. Two things I'd flag if you want a separate pass: the docstring doesn't mention that the discount floors rather than rounds, and it doesn't say `ValueError` is raised — both are `C14` gaps a caller would hit. That's a behavior-adjacent edit, so it belongs in its own change (`X4`).
- I assumed the test file sits beside the `starter/` package so `from starter.discount import ...` resolves. If your layout puts tests under `tests/`, that import line needs adjusting.
- I couldn't run `scripts/taorc_lint.py --changed` from here — worth running locally if that file exists in your skills directory.