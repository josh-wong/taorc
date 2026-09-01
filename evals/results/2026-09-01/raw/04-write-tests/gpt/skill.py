```python
# test_discount.py
import pytest

from starter.discount import apply_discount


def test_apply_discount_normal_no_cap():
    """Applies a standard percentage discount when no cap is provided."""
    total_cents = 10000  # $100.00
    percent_off = 25

    discounted_total = apply_discount(total_cents, percent_off)

    # 25% of 10000 is 2500, so final total should be 7500
    assert discounted_total == 7500


def test_apply_discount_capped():
    """Caps the discount when the calculated discount exceeds cap_cents."""
    total_cents = 20000  # $200.00
    percent_off = 50     # would be 10000 cents off
    cap_cents = 3000     # but cap at $30.00

    discounted_total = apply_discount(total_cents, percent_off, cap_cents=cap_cents)

    # Discount should be capped at 3000, so final total is 17000
    assert discounted_total == 17000


@pytest.mark.parametrize(
    "percent_off, expected_total",
    [
        (0, 5000),   # no discount
        (100, 0),    # full discount
    ],
)
def test_apply_discount_boundary_percent_off(percent_off, expected_total):
    """Handles boundary percent_off values of 0 and 100."""
    total_cents = 5000  # $50.00

    discounted_total = apply_discount(total_cents, percent_off)

    assert discounted_total == expected_total


@pytest.mark.parametrize("percent_off", [-1, -50, 101, 150])
def test_apply_discount_invalid_percent_raises_value_error(percent_off):
    """Rejects percent_off values outside the inclusive 0–100 range."""
    total_cents = 10000

    with pytest.raises(ValueError):
        apply_discount(total_cents, percent_off)
```