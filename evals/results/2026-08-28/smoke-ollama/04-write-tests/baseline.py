```python
# test_discount.py
"""Tests for apply_discount function in starter/discount.py."""

import pytest
from unittest.mock import patch
from starter.discount import apply_discount


class TestApplyDiscount:
    """Test suite for the apply_discount function."""

    def test_normal_discount_no_cap(self):
        """Test normal discount with no cap (cap_cents=None)."""
        total = 100
        percent = 25
        expected = 75
        assert apply_discount(total, percent) == expected

    def test_discount_with_cap(self):
        """Test discount that exceeds cap_cents and gets capped."""
        total = 1000
        percent = 50
        cap = 300
        expected = 700  # 1000 - min(500, 300) = 1000 - 300
        assert apply_discount(total, percent, cap_cents=cap) == expected

    def test_percent_off_zero(self):
        """Test boundary value: percent_off of 0."""
        total = 100
        percent = 0
        expected = 100  # No discount applied
        assert apply_discount(total, percent) == expected

    def test_percent_off_hundred(self):
        """Test boundary value: percent_off of 100."""
        total = 100
        percent = 100
        expected = 0  # Full discount
        assert apply_discount(total, percent) == expected

    def test_invalid_negative_percent_off(self):
        """Test invalid negative percent_off raises ValueError."""
        total = 100
        percent = -5
        with pytest.raises(ValueError, match="percent_off must be between 0 and 100"):
            apply_discount(total, percent)

    def test_invalid_over_hundred_percent_off(self):
        """Test invalid percent_off over 100 raises ValueError."""
        total = 100
        percent = 105
        with pytest.raises(ValueError, match="percent_off must be between 0 and 100"):
            apply_discount(total, percent)

    def test_invalid_boundary_values(self):
        """Test boundary values at 0 and 100 are valid."""
        total = 100
        assert apply_discount(total, 0) == 100
        assert apply_discount(total, 100) == 0

    def test_cap_applied_correctly(self):
        """Test that cap is applied correctly when discount exceeds it."""
        total = 500
        percent = 80
        cap = 200
        expected = 300  # 500 - min(400, 200) = 500 - 200
        assert apply_discount(total, percent, cap_cents=cap) == expected

    def test_no_cap_when_none(self):
        """Test that None is treated as no cap."""
        total = 100
        percent = 50
        expected = 50
        assert apply_discount(total, percent, cap_cents=None) == expected

    def test_discount_with_zero_total(self):
        """Test discount with zero total amount."""
        total = 0
        percent = 50
        cap = 100
        expected = 0
        assert apply_discount(total, percent, cap_cents=cap) == expected

    def test_discount_with_large_values(self):
        """Test with large values to ensure no overflow issues."""
        total = 999999
        percent = 50
        cap = 1000000
        expected = 499999.5  # Should be integer division
        assert apply_discount(total, percent, cap_cents=cap) == 499999

    def test_cap_less_than_discount(self):
        """Test when cap is less than calculated discount."""
        total = 1000
        percent = 50
        cap = 100
        expected = 900  # 1000 - min(500, 100) = 1000 - 100
        assert apply_discount(total, percent, cap_cents=cap) == expected

    def test_percent_off_boundary_values(self):
        """Test boundary values at 0 and 100."""
        total = 100
        # Test 0
        assert apply_discount(total, 0) == 100
        # Test 100
        assert apply_discount(total, 100) == 0

    def test_invalid_percent_off_boundary(self):
        """Test that values just outside range raise ValueError."""
        total = 100
        with pytest.raises(ValueError):
            apply_discount(total, -1)
        with pytest.raises(ValueError):
            apply_discount(total, 101)


if __name__ == "__main__":
    pytest.main([__file__])
```