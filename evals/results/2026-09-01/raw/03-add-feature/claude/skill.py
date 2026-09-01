## Change

Added after `add_line`, keeping the two list-mutating functions together:

```python
def remove_line(cart, sku):
    """Remove the first line matching `sku`. No-op if no line matches."""
    for i, line in enumerate(cart):
        if line["sku"] == sku:
            del cart[i]
            break
    return cart
```

Notes on the choices:

- **Mutate-and-return, matching `add_line`.** The file's convention is to modify `cart` in place and return it for chaining (`X2`). Returning a new list here would make the two functions behave differently for the same-looking call.
- **`break` rather than a `found` flag** (`V5`), and `del cart[i]` rather than `cart.remove(line)` — `list.remove` would re-scan from the start and match by dict equality, which is a different rule than "first line with this SKU."
- **One docstring, on this function only.** `remove_line` raises two questions its signature can't answer: what happens with no match, and what happens with several (`C14`). `add_line`, `line_total`, and `cart_total` raise neither, which is why they have none — I did not add docstrings to them to make the file look uniform (`X1`).
- **`i` left short.** Its scope is three lines (`N5`).

## Not changed

- The `sku`/`qty`/`amt` keys and all existing function names — out of scope and load-bearing for the checkout service, per the module docstring (`X3`).
- The module docstring already states that `amt` is in cents, so no unit suffix was needed on the new parameter (`N3`).
- No `remove_lines`/`remove_all` variant, and no `strict=True` parameter to raise on a missing SKU — one caller, one behavior (`S6`). Worth adding only when a caller actually needs to distinguish "removed" from "wasn't there," which would likely mean returning a bool instead of the cart and breaking the pattern above.

I don't have file access in this session, so I couldn't run `scripts/taorc_lint.py --changed`. If that script is present in the repo, run it against the change before committing.