## `test_discount.py`

```python
"""Tests for apply_discount."""

import pytest

from starter.discount import apply_discount


def test_subtracts_percentage_when_no_cap_is_given():
    assert apply_discount(10_000, percent_off=25) == 7_500


def test_caps_discount_when_percentage_exceeds_cap():
    # 50% of 10_000 is 5_000, but the cap allows only 1_500 off.
    assert apply_discount(10_000, percent_off=50, cap_cents=1_500) == 8_500


def test_ignores_cap_when_discount_stays_below_it():
    # 10% of 10_000 is 1_000, well under the 5_000 cap.
    assert apply_discount(10_000, percent_off=10, cap_cents=5_000) == 9_000


def test_returns_total_unchanged_when_percent_off_is_zero():
    assert apply_discount(10_000, percent_off=0) == 10_000


def test_returns_zero_when_percent_off_is_one_hundred():
    assert apply_discount(10_000, percent_off=100) == 0


def test_rounds_partial_cents_down():
    # 33% of 999 is 329.67 cents; the customer pays the leftover cent.
    assert apply_discount(999, percent_off=33) == 670


@pytest.mark.parametrize("percent_off", [-1, 101])
def test_rejects_percent_off_outside_zero_to_one_hundred(percent_off):
    with pytest.raises(ValueError, match="between 0 and 100"):
        apply_discount(10_000, percent_off=percent_off)
```

## Notes on what I did and didn't do

**Two tests beyond your four bullets.** Both pin a distinct outcome of the code as written, so I'd argue they belong, but they're easy to drop if you disagree:

- `test_ignores_cap_when_discount_stays_below_it` covers the other branch of `min(discount, cap_cents)`. Without it, `min` could be swapped for `max` and only the capped test would notice — and only in one direction.
- `test_rounds_partial_cents_down` pins the `//` truncation. **Worth a decision from you:** if flooring is deliberate (customer pays the extra cent, house wins the rounding), the test documents it. If it's incidental, the test now locks in a bug. I've asserted current behavior, not intended behavior.

**Values inline, no fixtures or factory helper.** Every number a test is about is visible on the assertion line (`T1`). A `make_order()` helper would send a reader to a second location to learn what `10_000` was.

**`10_000` throughout as the base total.** Holding the total constant means the only thing varying between tests is the thing under test.

**Invalid inputs use `-1` and `101`, not `-500` and `9999`.** Just-outside values exercise the boundary check; far-outside values test the same branch while implying a range check that isn't there.

**`match="between 0 and 100"`** rather than the full message — asserts the error is the one you meant without breaking on rewording.

**Left alone:**

- `starter/discount.py` — untouched. The docstring doesn't currently mention that `cap_cents` is in cents-off (not a floor on the total) or that `percent_off` is validated; that's a separate change from writing tests.
- No `conftest.py` or `__init__.py`. `from starter.discount import ...` resolves via namespace packages if this file sits at the repo root next to `starter/`. If your layout differs, that import is the one line to adjust.
- Parametrized only the `ValueError` cases. Rolling the four value-returning tests into one parametrized table would collapse four scenario names into one, and the names are doing real work here.