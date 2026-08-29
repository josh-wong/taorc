```python
def remove_line(cart, sku):
    for i, line in enumerate(cart):
        if line["sku"] == sku:
            del cart[i]
            break
    return cart
```

Place it after `add_line`, so the two mutating operations sit together and the total-calculating functions stay grouped below (`A5`).

**Notes on the choices**

- Mutates in place and returns `cart`, matching `add_line`'s existing contract so callers don't have to remember which functions in this module return a new list (`X2`, `A4`).
- `break` after the delete gives you "first match" without a flag variable or a second pass (`V5`), and it's what makes the "no match leaves the cart unchanged" case fall out for free — the loop just ends and returns `cart`.
- `i` is fine here: its scope is three lines (`N5`).
- No docstring, because no other function in the file has one and the behavior is visible in four lines. The module docstring already carries the key-naming rationale, which is the part the code can't say (`C1`, `X2`).

**Deliberately not changed**

- Did not add type hints — the file has none, and adding them to one function only would make the module look half-migrated (`X1`, `X2`).
- Did not touch the `sku`/`qty`/`amt` keys or any existing function name, per your instruction and `X3`.
- Noticed but left alone: `add_line` both mutates its argument and returns it, which is a shape that can mislead a caller into thinking they're getting a copy. Changing it is a behavior change, and it's the established convention here, so `remove_line` follows it rather than diverging (`X4`, precedence rule 2).