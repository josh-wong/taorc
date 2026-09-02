## `shipping.py`

```python
"""Shipping cost quoting."""

import math

# --- Pricing constants (all monetary values are in whole cents) ---
BASE_RATE_CENTS_PER_KG = 50
DISTANCE_SURCHARGE_CENTS_PER_KM = 2
FREE_DISTANCE_KM = 200          # first 200 km are covered by the base rate
FRAGILE_HANDLING_FEE_CENTS = 300
MIN_WEIGHT_KG = 0.1             # packages lighter than this are rejected


def quote_shipping_cost(weight_kg, distance_km, is_fragile):
    """Return the price, in whole cents, to ship a package.

    Pricing:
      * 50 cents per kilogram (base rate).
      * 2 cents per kilometer for every kilometer beyond the first 200 km.
      * A flat 300-cent handling fee for fragile packages.

    The total is rounded half-up to the nearest whole cent, since fractional
    weights and distances can produce fractional cents.

    Args:
        weight_kg: Package weight in kilograms. Must be at least 0.1 kg.
        distance_km: Shipping distance in kilometers. Must be non-negative.
        is_fragile: Truthy if the package requires fragile handling.

    Returns:
        int: The quoted price in whole cents.

    Raises:
        ValueError: If the inputs are not finite numbers, if the weight is
            under 0.1 kg, or if the distance is negative.
    """
    weight_kg = _as_finite_number(weight_kg, "weight_kg")
    distance_km = _as_finite_number(distance_km, "distance_km")

    if weight_kg < MIN_WEIGHT_KG:
        raise ValueError(
            "package weight must be at least {} kg, got {} kg".format(
                MIN_WEIGHT_KG, weight_kg
            )
        )
    if distance_km < 0:
        raise ValueError(
            "distance must be non-negative, got {} km".format(distance_km)
        )

    cost = weight_kg * BASE_RATE_CENTS_PER_KG

    billable_distance = max(0.0, distance_km - FREE_DISTANCE_KM)
    cost += billable_distance * DISTANCE_SURCHARGE_CENTS_PER_KM

    if is_fragile:
        cost += FRAGILE_HANDLING_FEE_CENTS

    # Round half-up; cost is always non-negative here.
    return int(math.floor(cost + 0.5))


def _as_finite_number(value, name):
    """Coerce ``value`` to a float, rejecting non-numeric/NaN/infinite input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("{} must be a number, got {!r}".format(name, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("{} must be a finite number, got {!r}".format(name, value))
    return value
```

### Notes on the judgment calls

- **Rounding:** weights and distances can be fractional, so the raw total can land on a fraction of a cent. The function rounds half-up to the nearest cent rather than using Python's banker's rounding, which matches typical billing expectations.
- **Distance surcharge:** only kilometers *beyond* 200 are charged, so a 250 km trip incurs `50 × 2 = 100` cents, not `250 × 2`. Exactly 200 km incurs no surcharge ("once distance exceeds 200 km").
- **Weight threshold:** "under 0.1 kg" is rejected, so exactly 0.1 kg is accepted.
- **Extra validation:** negative distances, non-numeric input, and NaN/infinity are rejected with `ValueError` too — they can't produce a meaningful quote, and `bool` is excluded so `True` isn't silently treated as 1 kg.

Quick sanity check: `quote_shipping_cost(2, 500, True)` → `100 + 600 + 300 = 1000` cents.