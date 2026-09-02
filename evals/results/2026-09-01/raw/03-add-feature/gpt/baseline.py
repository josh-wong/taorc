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


def remove_line(cart, sku):
    for idx, line in enumerate(cart):
        if line.get("sku") == sku:
            del cart[idx]
            break
    return cart


def line_total(line):
    return line["qty"] * line["amt"]


def cart_total(cart):
    return sum(line_total(line) for line in cart)
```