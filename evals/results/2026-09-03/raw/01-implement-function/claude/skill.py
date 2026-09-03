`shipping.py`

```python
"""Shipping price quotes, in whole cents."""

BASE_CENTS_PER_KG = 50
SURCHARGE_CENTS_PER_KM = 2
DISTANCE_COVERED_BY_BASE_KM = 200
FRAGILE_HANDLING_CENTS = 300
MIN_SHIPPABLE_WEIGHT_KG = 0.1


def quote_shipping_cost(
    weight_kg: float, distance_km: float, is_fragile: bool
) -> int:
    """Return the price in whole cents to ship one package.

    The base rate covers the first 200 km, so only distance beyond that is
    surcharged; a 150 km trip costs the same as a 0 km trip.

    Fractional cents are rounded to the nearest whole cent once, after every
    component is summed: a 0.147 kg non-fragile local package works out to
    7.35 cents and quotes as 7.

    Raises:
        ValueError: if weight_kg is below 0.1 kg.
    """
    if weight_kg < MIN_SHIPPABLE_WEIGHT_KG:
        raise ValueError(
            f"package weighs {weight_kg} kg, below the "
            f"{MIN_SHIPPABLE_WEIGHT_KG} kg minimum"
        )

    surcharged_distance_km = max(0, distance_km - DISTANCE_COVERED_BY_BASE_KM)
    cents = (
        weight_kg * BASE_CENTS_PER_KG
        + surcharged_distance_km * SURCHARGE_CENTS_PER_KM
    )
    if is_fragile:
        cents += FRAGILE_HANDLING_CENTS
    return round(cents)
```

**Notes on the choices**

- Each pricing number is a named module constant with its unit in the name (`N3`), so the arithmetic reads as the rule rather than as magic numbers (`C5`).
- The rejection is a guard clause up front, and the message reports both the offending weight and the threshold so a failure is diagnosable without a debugger (`F5`, `C14`).
- `max(0, ...)` expresses "only distance beyond the included 200 km" without a second branch, and `surcharged_distance_km` names what the subexpression means (`E1`).
- The docstring covers the two things a caller cannot see from the signature: that the first 200 km are free, and that rounding happens once at the end rather than per component (`C6`, `C15`).

**What I deliberately did not do**

- No helper function. Each step is one named line; extracting `_base_cost` or `_distance_surcharge` would add call sites without adding a describable subproblem (`S1`, `S6`).
- No validation of negative `distance_km` or non-boolean `is_fragile`. The spec names one rejection rule, and `max(0, ...)` already treats a negative distance as zero surcharge (`X1`).
- No `Decimal`. Introducing it would change the rounding behavior, which is a design decision for you rather than a readability edit (`X4`). If exact cent arithmetic matters at your volumes, say so and I will switch and document the new rounding contract.
- I did not look for or run `scripts/taorc_lint.py`, since I have no filesystem access in this conversation; run it yourself if it is installed here.