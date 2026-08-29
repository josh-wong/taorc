## `test_discount.py`

```python
"""Tests for apply_discount."""

import pytest

from starter.discount import apply_discount


def test_discount_without_cap_subtracts_full_percentage():
    assert apply_discount(total_cents=10_000, percent_off=20) == 8_000


def test_discount_larger_than_cap_is_limited_to_cap():
    # 50% of 10_000 is 5_000, but the cap allows only 1_500 off.
    assert apply_discount(total_cents=10_000, percent_off=50, cap_cents=1_500) == 8_500


def test_zero_percent_off_leaves_total_unchanged():
    assert apply_discount(total_cents=10_000, percent_off=0) == 10_000


def test_hundred_percent_off_reduces_total_to_zero():
    assert apply_discount(total_cents=10_000, percent_off=100) == 0


@pytest.mark.parametrize("invalid_percent_off", [-1, 101])
def test_percent_off_outside_zero_to_hundred_raises(invalid_percent_off):
    with pytest.raises(ValueError, match="between 0 and 100"):
        apply_discount(total_cents=10_000, percent_off=invalid_percent_off)
```

## Why it's written this way

- **`T3`** — each name states the situation and the expected outcome, so a failure line in CI is already a bug report: `test_discount_larger_than_cap_is_limited_to_cap` tells you what broke without opening the file.
- **`T1`, `C17`** — every call uses keyword arguments. `apply_discount(10_000, 50, 1_500)` would make the reader jump to the signature to decode the third number; `cap_cents=1_500` does not.
- **`T2`** — `10_000` throughout. One total, varied only in the dimension under test, so the expected value is arithmetic a reader can do in their head.
- **`T5`** — the two boundaries are separate tests rather than one `test_boundaries`, because `percent_off=0` and `percent_off=100` fail for different reasons and should be distinguishable at a glance in the output.
- **`T4`** — `match="between 0 and 100"` asserts the message, not just the type, so a `ValueError` raised for some unrelated reason still fails the test.
- **`C5`** — the one comment explains where `8_500` comes from. Without it, that constant is the only number in the file that isn't obvious, and the reader has to reconstruct `min(5_000, 1_500)` themselves. No other test gets a comment, since `10_000 - 20%` needs none (`C1`).
- **`X2`** — parameter names mirror the source (`total_cents`, `percent_off`, `cap_cents`); the `_cents` suffix already carries the unit (`N3`).

## What I did not do

- **Did not add tests beyond the four you listed** (`X1`). Two gaps I noticed while reading `apply_discount`, left for you to decide on:
  - `discount = total_cents * percent_off // 100` truncates. `apply_discount(total_cents=101, percent_off=50)` returns `51`, not `50.5` rounded. That is untested, and it is the kind of behavior that gets changed by accident.
  - A `cap_cents` larger than the computed discount (cap present but not binding) is untested — only the capped branch is covered.
- **Did not touch `starter/discount.py`** (`X4`). The `ValueError` message says "between 0 and 100" without stating that both ends are inclusive, which the code's `<=` implies; that's a docstring nit, not a test concern.
- **Import path assumption**: this places `test_discount.py` at the repo root, as a sibling of `starter/`. If your tests live under `tests/` or inside `starter/` itself, adjust the import to match your existing test layout rather than to match this file.