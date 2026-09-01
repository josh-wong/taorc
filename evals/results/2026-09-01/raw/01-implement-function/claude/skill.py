`shipping.py`:

```python
"""Shipping price calculation."""

MIN_WEIGHT_KG = 0.1
BASE_CENTS_PER_KG = 50
SURCHARGE_FREE_DISTANCE_KM = 200
SURCHARGE_CENTS_PER_KM = 2
FRAGILE_HANDLING_CENTS = 300


def quote_shipping_cost(
    weight_kg: float, distance_km: float, is_fragile: bool
) -> int:
    """Return the price in whole cents to ship one package.

    The base rate covers the weight plus the first 200 km. Distance past
    that is surcharged per km, and fragile packages add a flat handling fee.

    Boundaries: exactly 0.1 kg is quotable, anything lighter raises
    ValueError. A 200 km trip carries no surcharge; a 201 km trip is
    surcharged for 1 km. Distances under 200 km never produce a credit.

    The total is rounded to the nearest cent once, at the end, so a
    0.15 kg package pays 8 cents rather than 7.
    """
    if weight_kg < MIN_WEIGHT_KG:
        raise ValueError(
            f"package weighs {weight_kg} kg, "
            f"under the {MIN_WEIGHT_KG} kg minimum"
        )

    surcharged_km = max(0.0, distance_km - SURCHARGE_FREE_DISTANCE_KM)

    cents = (
        weight_kg * BASE_CENTS_PER_KG
        + surcharged_km * SURCHARGE_CENTS_PER_KM
    )
    if is_fragile:
        cents += FRAGILE_HANDLING_CENTS

    return round(cents)
```

**Notes on the choices**

- Every constant carries its unit in the name (`N3`), so the arithmetic reads as
  a sentence and no comment is needed to explain what `50` or `200` means
  (`C1`).
- The rejection is a guard clause up front, so the body below it deals only
  with the valid case (`F5`).
- `surcharged_km` names the subexpression the pricing rule is actually about
  (`E1`); the `max(0.0, ...)` makes the "first 200 km are free" rule explicit
  rather than hiding it behind an `if`.
- The docstring spells out the boundaries the rules leave ambiguous — exactly
  0.1 kg, exactly 200 km — since those are the questions a caller would
  otherwise answer by reading the source (`C14`, `C15`).

**What I deliberately did not do**

- No helper function. Each step is one named line, and a `_distance_surcharge`
  helper would have one caller (`S6`) while adding a hop for the reader.
- No rounding of intermediate terms. Rounding once at the end avoids compounding
  error; rounding per-component would be a behavior decision the spec did not
  ask for.
- No validation of negative or non-numeric `distance_km`. The spec names one
  rejection rule, and `max(0.0, ...)` already keeps a negative distance from
  producing a credit (`S5`).
- No `Decimal`. The function returns whole cents, and floats are accurate well
  past any realistic package weight — introducing `Decimal` would change the
  signature's shape for callers without a stated need.