```python
# test_discount.py
import pytest

from starter.discount import apply_discount


class TestApplyDiscount:
    def test_normal_discount_no_cap(self):
        # 20% off 10_00 = 2_00 discount
        assert apply_discount(total_cents=1000, percent_off=20) == 800

    def test_discount_capped_by_cap_cents(self):
        # 50% of 10_00 would be 5_00, but cap is 3_00
        assert apply_discount(total_cents=1000, percent_off=50, cap_cents=300) == 700

    def test_zero_percent_off_returns_original_total(self):
        assert apply_discount(total_cents=1234, percent_off=0) == 1234

    def test_hundred_percent_off_zeroes_total(self):
        assert apply_discount(total_cents=999, percent_off=100) == 0

    @pytest.mark.parametrize("percent_off", [-1, -50, 101, 150])
    def test_invalid_percent_off_raises_value_error(self, percent_off):
        with pytest.raises(ValueError):
            apply_discount(total_cents=1000, percent_off=percent_off)
```