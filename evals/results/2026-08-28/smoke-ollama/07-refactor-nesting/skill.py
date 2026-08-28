```python
# starter/pricing.py

def compute_price(order):
    """Calculate total price for an order with tax and membership discounts."""
    
    if order is None or not order.get("items"):
        return 0
    
    subtotal = 0
    state = order.get("state")
    member = order.get("member", False)
    
    # Tax rates by category and state
    food_tax_rate = 1.05 if state not in ("CA", "WA") else 1.0
    non_food_tax_rate = 1.08 if state in ("CA", "WA") else 1.05
    
    for item in order["items"]:
        qty = item.get("qty", 0)
        unit_price_cents = item.get("unit_price_cents", 0)
        
        # Skip items with zero quantity or price
        if qty <= 0 or unit_price_cents <= 0:
            continue
        
        category = item.get("category")
        
        # Apply tax based on category and state
        if category == "food":
            subtotal += int(qty * unit_price_cents * food_tax_rate)
        else:
            subtotal += int(qty * unit_price_cents * non_food_tax_rate)
    
    # Apply membership discount for high-value orders
    if member and subtotal > 5000:
        subtotal -= 500
    
    return subtotal
```

I left the function name, signature, and core logic unchanged. The nested conditionals were flattened by extracting state-based tax rates into variables, and early returns handle edge cases upfront. Each item's contribution is calculated once per loop iteration, eliminating repeated tax-rate checks.