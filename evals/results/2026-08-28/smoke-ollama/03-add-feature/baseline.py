```python
# starter/cart.py
"""Shopping cart with the project's line-item convention.

Every line item is a dict with keys `sku`, `qty`, `amt` (unit price in
cents). This module always spells them that way -- not `quantity` or `amount` -- because the checkout service that consumes this cart's output uses the same three-letter keys end to end.
"""


def add_line(cart, sku, qty, amt):
    cart.append({"sku": sku, "qty": qty, "amt": amt})
    return cart


def line_total(line):
    return line["qty"] * line["amt"]


def cart_total(cart):
    return sum(line_total(line) for line in cart)


def remove_line(cart, sku):
    """Remove the first line item matching `sku` from the cart.

    Args:
        cart: The shopping cart (list of line items).
        sku: The SKU to match and remove.

    Returns:
        The updated cart with the matching line removed. If no match is found,
        returns the original cart unchanged.
    """
    for i in range(len(cart)):
        if cart[i]["sku"] == sku:
            del cart[i]
            return cart
    
    # No matching line found, return original cart unchanged
    return cart
```