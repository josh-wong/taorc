I wrote `shipping.py`:

```python
"""Shipping price quotes, in whole cents."""

CENTS_PER_KG = 50
SURCHARGE_CENTS_PER_KM = 2
FRAGILE_HANDLING_CENTS = 300

# The base rate already covers the first 200 km; only distance past that is surcharged.
INCLUDED_DISTANCE_KM = 200

MIN_SHIPPABLE_WEIGHT_KG = 0.1


def quote_shipping_cost(weight_kg, distance_km, is_fragile):
    """Return the price in whole cents to ship one package.

    A package of exactly 0.1 kg ships; anything lighter raises ValueError.
    Trips of 200 km or less carry no distance surcharge.

    >>> quote_shipping_cost(2.0, 500, is_fragile=False)
    700
    >>> quote_shipping_cost(2.0, 150, is_fragile=True)
    400
    """
    if weight_kg < MIN_SHIPPABLE_WEIGHT_KG:
        raise ValueError(
            f"package weighs {weight_kg} kg, "
            f"under the {MIN_SHIPPABLE_WEIGHT_KG} kg minimum"
        )

    surcharged_distance_km = max(0, distance_km - INCLUDED_DISTANCE_KM)

    price_cents = (
        weight_kg * CENTS_PER_KG
        + surcharged_distance_km * SURCHARGE_CENTS_PER_KM
    )
    if is_fragile:
        price_cents += FRAGILE_HANDLING_CENTS

    # Round once at the end: rounding each component separately can land a cent
    # off the true total. Note that round() breaks exact .5 ties toward even.
    return round(price_cents)
```

**Choices worth flagging:**

- **Named constants over inline numbers** (`C5`) — `50` and `300` say nothing at the point of use; `CENTS_PER_KG` and `FRAGILE_HANDLING_CENTS` carry both the unit and the intent. `INCLUDED_DISTANCE_KM` is the one that genuinely needed a comment, since the name alone doesn't explain that the base rate absorbs it.
- **Rejection first, as a guard clause** (`F5`) — the invalid case returns before any pricing logic, so the body reads as one unnested arithmetic paragraph.
- **`surcharged_distance_km` as a named subexpression** (`E1`, `N3`) — `max(0, distance_km - 200)` inline inside the total would make the reader compute what it means; the name says it, and the `_km` suffix keeps it from being confused with a cent amount.
- **Rounding is commented, not silent** (`C6`, `C7`) — a reader will stop and ask where the `int` comes from and whether `2.5` rounds up. Python's `round()` ties-to-even is a real trap for money, so it's advertised rather than left to be discovered.

**What I deliberately did not do:**

- **No helper function** (`S6`) — you left the door open for one, but every candidate split (a `_base_cost`, a `_distance_surcharge`) has exactly one caller and a body shorter than its own signature. Extracting them would add indirection without removing any.
- **No validation of `distance_km` or `is_fragile`** (`S5`, `X1`) — the spec names one rejection rule, so that's the only one enforced. A negative distance already produces no surcharge via `max(0, ...)` rather than a negative one.
- **No type hints** — the file is new with no surrounding code to match, so there's no local convention to follow (`X2`). Say the word if the project annotates, and `weight_kg: float, distance_km: float, is_fragile: bool) -> int` is a one-line change.
- **No `Decimal`** — it's the right call if these quotes ever get summed into invoices or compared against a payment processor's arithmetic, but it changes the return contract and the call sites, which is more than this task asked for.

I didn't find a `scripts/taorc_lint.py` under any of the standard skill roots, so the verify step was skipped.