```python
def quote_shipping_cost(weight_kg, distance_km, is_fragile):
    """Calculate shipping cost in whole cents.
    
    Args:
        weight_kg: Package weight in kilograms
        distance_km: Shipping distance in kilometers
        is_fragile: Boolean indicating if package is fragile
    
    Returns:
        int: Total shipping cost in cents
    
    Raises:
        ValueError: If weight is less than 0.1 kg
    """
    
    # Reject packages under minimum weight threshold first
    if weight_kg < 0.1:
        raise ValueError("Package weight must be at least 0.1 kg")
    
    # Base cost: 50 cents per kilogram
    base_cost = weight_kg * 50
    
    # Distance surcharge applies only beyond 200 km
    if distance_km > 200:
        distance_surcharge = (distance_km - 200) * 2
    else:
        distance_surcharge = 0
    
    # Fragile handling fee is flat 300 cents
    fragile_fee = 300 if is_fragile else 0
    
    # Sum all components for total cost
    return int(base_cost + distance_surcharge + fragile_fee)
```