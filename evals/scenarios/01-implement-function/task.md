Write a single Python function in `shipping.py`:

`quote_shipping_cost(weight_kg, distance_km, is_fragile)` returns the price in
whole cents (an `int`) to ship a package.

Pricing rules:

- Base rate: 50 cents per kilogram.
- Distance surcharge: 2 cents per kilometer once distance exceeds 200 km (the
  first 200 km are covered by the base rate).
- Fragile packages add a flat 300-cent handling fee.
- Any package under 0.1 kg is rejected — raise `ValueError`.

No test file is required; just the function and any helper it needs.
