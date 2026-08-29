```python
# starter/cart.py
"""Shopping cart with the project's line-item convention.

Every line item is a dict with keys `sku`, `qty`, `amt` (unit price in
cents). This module always spells them that way -- not `quantity` or
`amount` -- because the checkout service that consumes this cart's output
uses the same three-letter keys end to end.
"""


def add_line(cart, sku, qty, amt):
    cart.append({"sku": sku, "qty": qty, "amt": amt})
    return cart


def line_total(line):
    return line["qty"] * line["amt"]


def cart_total(cart):
    return sum(line_total(line) for line in cart)


def remove_line(cart, sku):
    """Remove first line item matching `sku` from the cart.

    Returns the updated cart with the matching line removed. If no line
    matches `sku`, returns the original cart unchanged.
    """
    for i, line in enumerate(cart):
        if line["sku"] == sku:
            del cart[i]
            return cart
    return cart
```