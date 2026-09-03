Added below `add_line`, keeping it next to the other cart-mutating function.

```python
def add_line(cart, sku, qty, amt):
    cart.append({"sku": sku, "qty": qty, "amt": amt})
    return cart


def remove_line(cart, sku):
    for index, line in enumerate(cart):
        if line["sku"] == sku:
            del cart[index]
            break
    return cart
```

`break` after the delete is what makes "the first match only" visible without a comment saying so, and it also keeps the loop from mutating a list it is still iterating.

**What I deliberately did not change:**

- **No docstring on `remove_line`.** The self-check normally wants a new function's corner cases stated (`C14`), but no function in this file has a docstring, and the two behaviors a caller might ask about — first match only, mutates in place and returns the same cart — are both readable straight off the four lines. Adding one here would make `remove_line` the odd function out (`A7`, `X2`). Say the word if you'd rather have docstrings, but then it should be all four functions in one pass, not just the new one.
- **No type hints.** The file has none; adding them to one function only would be inconsistent, and adding them everywhere is a wider diff than you asked for (`X1`).
- **Kept the mutate-and-return shape.** `add_line` mutates `cart` and returns it, so `remove_line` does the same. A pure version returning a new list would read better in isolation but would make the two functions behave differently at call sites, which is worse (`X2`).
- **Left the existing keys and functions alone**, as specified — `amt` reads as underspecified on its own (`N3`, no unit in the name), but the module docstring pins it to cents and the checkout service depends on the spelling.