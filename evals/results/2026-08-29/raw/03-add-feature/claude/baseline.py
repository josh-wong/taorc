## `starter/cart.py`

```python
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
    for index, line in enumerate(cart):
        if line["sku"] == sku:
            del cart[index]
            break
    return cart


def line_total(line):
    return line["qty"] * line["amt"]


def cart_total(cart):
    return sum(line_total(line) for line in cart)
```

### Notes on the choices made

- **Naming.** The new parameter is `sku`, matching the key used by `add_line` and the module docstring's stated convention. No existing keys or function names were touched.
- **Mutate-and-return.** `add_line` mutates `cart` in place and returns it, so `remove_line` does the same. Callers can use either style (`remove_line(cart, "A1")` or `cart = remove_line(cart, "A1")`) and get the same result, just as they can with `add_line`.
- **First match only.** The `break` after the first deletion satisfies "removes the first line item matching `sku`" and keeps any later duplicate SKUs intact. Iterating with `enumerate` and deleting by index avoids the classic bug of mutating a list while continuing to iterate over it.
- **No match is a no-op.** If the loop finds nothing, nothing is deleted and the unchanged `cart` is returned — no exception, per the spec.

### Quick sanity check

```python
cart = []
add_line(cart, "A1", 2, 500)
add_line(cart, "B2", 1, 250)
add_line(cart, "A1", 3, 500)

remove_line(cart, "A1")
# [{'sku': 'B2', 'qty': 1, 'amt': 250}, {'sku': 'A1', 'qty': 3, 'amt': 500}]
# -> only the first "A1" line is gone

remove_line(cart, "ZZ")
# unchanged; cart_total(cart) == 1750
```