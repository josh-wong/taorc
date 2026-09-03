```python
def quote_shipping_cost(weight_kg, distance_km, is_fragile):
    """
    Calculate the shipping cost in whole cents.

    Rules:
    - Base rate: 50 cents per kilogram, applied to all shipments.
    - Distance surcharge: 2 cents per kilometer for distance beyond 200 km.
    - Fragile packages: flat 300-cent handling fee added if is_fragile is True.
    - Packages under 0.1 kg are rejected with ValueError.

    Returns:
        int: total shipping cost in cents.

    Raises:
        ValueError: if weight_kg is less than 0.1.
    """
    if weight_kg < 0.1:
        raise ValueError("Packages under 0.1 kg cannot be shipped.")

    base_cost_cents = int(round(weight_kg * 50))

    if distance_km <= 200:
        distance_surcharge_cents = 0
    else:
        extra_distance_km = distance_km - 200
        distance_surcharge_cents = int(round(extra_distance_km * 2))

    fragile_fee_cents = 300 if is_fragile else 0

    total_cost_cents = base_cost_cents + distance_surcharge_cents + fragile_fee_cents
    return total_cost_cents
```