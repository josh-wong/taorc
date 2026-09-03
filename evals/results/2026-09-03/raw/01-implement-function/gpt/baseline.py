```python
def quote_shipping_cost(weight_kg, distance_km, is_fragile):
    """
    Calculate the shipping cost in whole cents.

    Pricing rules:
    - Base rate: 50 cents per kilogram.
    - Distance surcharge: 2 cents per kilometer once distance exceeds 200 km
      (the first 200 km are covered by the base rate).
    - Fragile packages add a flat 300-cent handling fee.
    - Any package under 0.1 kg is rejected — raises ValueError.

    Args:
        weight_kg (float): Weight of the package in kilograms.
        distance_km (float): Shipping distance in kilometers.
        is_fragile (bool): Whether the package is fragile.

    Returns:
        int: Total shipping cost in whole cents.

    Raises:
        ValueError: If weight_kg is less than 0.1.
    """
    if weight_kg < 0.1:
        raise ValueError("Packages under 0.1 kg cannot be shipped.")

    # Base cost: 50 cents per kilogram
    base_cost_cents = int(round(50 * weight_kg))

    # Distance surcharge: 2 cents per km beyond 200 km
    extra_distance_km = max(0, distance_km - 200)
    distance_surcharge_cents = int(round(2 * extra_distance_km))

    # Fragile handling fee
    fragile_fee_cents = 300 if is_fragile else 0

    total_cost_cents = base_cost_cents + distance_surcharge_cents + fragile_fee_cents
    return int(total_cost_cents)
```