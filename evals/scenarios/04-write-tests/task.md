Write `test_discount.py` covering `apply_discount` from `starter/discount.py`:

- A normal discount with no cap.
- A discount that would exceed `cap_cents` and gets capped.
- `percent_off` of 0 and of 100 (boundary values).
- An invalid `percent_off` (negative, or over 100) raising `ValueError`.

Use whatever test framework you'd normally reach for in a Python project
(`pytest` style is fine).
