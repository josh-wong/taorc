```python
def quote_shipping_cost(weight_kg, distance_km, is_fragile):
    """
    Calculate shipping cost in whole cents.

    Rules:
    - Raises ValueError if weight_kg < 0.1.
    - Base rate: 50 cents per kilogram, any distance.
    - Distance surcharge: 2 cents per kilometer beyond 200 km.
    - Fragile packages add a flat 300-cent handling fee.
    """
    if weight_kg < 0.1:
        raise ValueError("Packages under 0.1 kg cannot be shipped.")

    base_rate_cents_per_kg = 50
    distance_surcharge_cents_per_km = 2
    fragile_handling_fee_cents = 300
    distance_included_km = 200

    base_cost_cents = int(round(weight_kg * base_rate_cents_per_kg))

    if distance_km <= distance_included_km:
        distance_surcharge_cents = 0
    else:
        extra_distance_km = distance_km - distance_included_km
        distance_surcharge_cents = int(round(extra_distance_km * distance_surcharge_cents_per_km))

    fragile_fee_cents = fragile_handling_fee_cents if is_fragile else 0

    return base_cost_cents + distance_surcharge_cents + fragile_fee_cents
```