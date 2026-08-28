```python
# test_discount.py
"""Tests for apply_discount in starter/discount.py."""

import pytest
from starter.discount import apply_discount


@pytest.mark.parametrize(
    "total_cents, percent_off, expected",
    [
        (100, 25, 75),
        (1000, 10, 900),
        (500, 50, 250),
        (100, 0, 100),
        (100, 100, 0),
    ],
)
def test_normal_discount(total_cents: int, percent_off: int, expected: int) -> None:
    """Test normal discount calculation without cap."""
    result = apply_discount(total_cents, percent_off)
    assert result == expected


@pytest.mark.parametrize(
    "total_cents, percent_off, cap_cents, expected",
    [
        (1000, 50, 200, 800),
        (1000, 90, 50, 950),
        (100, 100, 10, 90),
    ],
)
def test_discount_capped_at_cap_cents(
    total_cents: int,
    percent_off: int,
    cap_cents: int,
    expected: int,
) -> None:
    """Test discount when it exceeds the cap and gets capped."""
    result = apply_discount(total_cents, percent_off, cap_cents)
    assert result == expected


@pytest.mark.parametrize(
    "percent_off",
    [
        -10,
        101,
        200,
    ],
)
def test_invalid_percent_off_raises_value_error(percent_off: int) -> None:
    """Test that invalid percent_off raises ValueError."""
    with pytest.raises(ValueError):
        apply_discount(100, percent_off)


@pytest.mark.parametrize(
    "total_cents",
    [
        0,
        1,
        1000000,
    ],
)
def test_edge_cases_with_zero_total(total_cents: int) -> None:
    """Test edge cases with zero or large total."""
    result = apply_discount(total_cents, 50)
    assert result == total_cents // 2


@pytest.mark.parametrize(
    "percent_off",
    [
        0,
        100,
    ],
)
def test_boundary_percent_values(percent_off: int) -> None:
    """Test boundary percent values (0 and 100)."""
    result = apply_discount(100, percent_off)
    assert result == 100 - (100 * percent_off // 100)
```