```python
# test_discount.py
import pytest

from starter.discount import apply_discount


def test_normal_discount_no_cap():
    # 20% off 10_000 cents (i.e., $100.00) -> 2_000 cents discount
    assert apply_discount(10_000, 20) == 8_000


def test_discount_capped_by_cap_cents():
    # 50% off 10_000 cents would be 5_000, but cap is 3_000
    # so discount should be capped at 3_000
    assert apply_discount(10_000, 50, cap_cents=3_000) == 7_000


@pytest.mark.parametrize(
    "percent_off,total_cents,expected",
    [
        (0, 10_000, 10_000),   # no discount
        (100, 10_000, 0),      # full discount
    ],
)
def test_boundary_percent_off_values(percent_off, total_cents, expected):
    assert apply_discount(total_cents, percent_off) == expected


@pytest.mark.parametrize("percent_off", [-1, -50, 101, 150])
def test_invalid_percent_off_raises_value_error(percent_off):
    with pytest.raises(ValueError):
        apply_discount(10_000, percent_off)
```