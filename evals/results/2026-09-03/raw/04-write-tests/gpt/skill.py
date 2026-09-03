```python
# test_discount.py
import pytest

from starter.discount import apply_discount


def test_apply_discount_normal_no_cap():
    # 20% off 10_00 -> 2_00 discount
    assert apply_discount(total_cents=1000, percent_off=20) == 800


def test_apply_discount_capped_discount():
    # 50% off 10_00 would be 5_00, but cap is 3_00
    assert apply_discount(total_cents=1000, percent_off=50, cap_cents=300) == 700


@pytest.mark.parametrize(
    "percent_off,total_cents,expected_total",
    [
        (0, 1000, 1000),   # no discount
        (100, 1000, 0),    # full discount
    ],
)
def test_apply_discount_boundary_percent_off(percent_off, total_cents, expected_total):
    assert apply_discount(total_cents=total_cents, percent_off=percent_off) == expected_total


@pytest.mark.parametrize("percent_off", [-1, -50, 101, 150])
def test_apply_discount_invalid_percent_raises_value_error(percent_off):
    with pytest.raises(ValueError):
        apply_discount(total_cents=1000, percent_off=percent_off)
```