```python
# test_discount.py
"""Tests for starter.discount.apply_discount."""

import pytest

from starter.discount import apply_discount


# --- Normal discount, no cap -------------------------------------------------

def test_normal_discount_no_cap():
    # 20% off $100.00 -> $20.00 off -> $80.00
    assert apply_discount(10_000, 20) == 8_000


def test_cap_that_is_never_reached_has_no_effect():
    # 10% of 10_000 is 1_000, well under the 5_000 cap.
    assert apply_discount(10_000, 10, cap_cents=5_000) == 9_000


# --- Capped discount ---------------------------------------------------------

def test_discount_is_capped():
    # 50% of 10_000 would be 5_000, but the cap limits it to 1_000.
    assert apply_discount(10_000, 50, cap_cents=1_000) == 9_000


def test_cap_exactly_equal_to_discount_is_not_reduced():
    # Boundary: discount == cap, so min() picks either; total is 5_000.
    assert apply_discount(10_000, 50, cap_cents=5_000) == 5_000


def test_zero_cap_means_no_discount_at_all():
    assert apply_discount(10_000, 50, cap_cents=0) == 10_000


# --- percent_off boundary values --------------------------------------------

def test_zero_percent_off_returns_total_unchanged():
    assert apply_discount(10_000, 0) == 10_000


def test_zero_percent_off_with_cap_returns_total_unchanged():
    assert apply_discount(10_000, 0, cap_cents=5_000) == 10_000


def test_hundred_percent_off_returns_zero():
    assert apply_discount(10_000, 100) == 0


def test_hundred_percent_off_still_respects_cap():
    assert apply_discount(10_000, 100, cap_cents=2_500) == 7_500


# --- Invalid percent_off -----------------------------------------------------

@pytest.mark.parametrize("percent_off", [-1, -100, 101, 1_000])
def test_out_of_range_percent_off_raises(percent_off):
    with pytest.raises(ValueError, match="percent_off must be between 0 and 100"):
        apply_discount(10_000, percent_off)


def test_validation_happens_before_any_capping():
    # A cap must not mask an invalid percentage.
    with pytest.raises(ValueError):
        apply_discount(10_000, 150, cap_cents=100)
```

Two notes on things the tests surfaced that you may want to decide on deliberately:

1. **Floor division rounds the discount down**, always in the merchant's favour. `apply_discount(1005, 10)` gives a discount of `100` (not `100.5`), so the customer pays `905`. That's a reasonable policy, but it's currently implicit. If you want it pinned down, add:

   ```python
   def test_fractional_discount_rounds_down():
       assert apply_discount(1_005, 10) == 905
   ```

2. **`cap_cents` caps the discount, not the total** — the docstring's "capped at `cap_cents`" reads ambiguously and could be misread as "the total is capped." The tests above (`test_hundred_percent_off_still_respects_cap`) encode the discount-cap interpretation, which matches the implementation. Worth tightening the docstring to say "with the discount capped at `cap_cents`."

I also didn't test negative `total_cents` or a negative `cap_cents`, since the function has no validation for either and I don't know the intended behaviour — a negative cap currently produces a total *larger* than the input, which is likely a bug worth guarding against if untrusted input can reach this function.