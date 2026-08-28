```python
def quote_shipping_cost(weight_kg: float, distance_km: float, is_fragile: bool) -> int:
    """Calculate the shipping cost for a package in whole cents.
    
    Args:
        weight_kg: Package weight in kilograms
        distance_km: Shipping distance in kilometers
        is_fragile: Boolean indicating if package is fragile
    
    Returns:
        Total shipping cost in whole cents (int)
    
    Raises:
        ValueError: If weight is less than 0.1 kg
    """
    # Validate weight - must be at least 0.1 kg
    if weight_kg < 0.1:
        raise ValueError("Weight must be at least 0.1 kg")
    
    # Base rate: 50 cents per kilogram
    base_cost = int(weight_kg * 50)
    
    # Distance surcharge: 2 cents per km for distances > 200 km
    if distance_km > 200:
        distance_surcharge = int((distance_km - 200) * 2)
    else:
        distance_surcharge = 0
    
    # Fragile handling fee: 300 cents flat
    fragile_fee = 300 if is_fragile else 0
    
    # Return total cost as integer
    return base_cost + distance_surcharge + fragile_fee
```