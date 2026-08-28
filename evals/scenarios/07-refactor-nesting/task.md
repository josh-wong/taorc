Refactor `starter/pricing.py` for readability. `compute_price` must keep its
exact current behavior (same inputs produce the same totals) — this is a
structural cleanup, not a rewrite of the pricing rules.

Focus on the nesting and the repeated tax-rate logic; you do not need to
change the function's name or signature.
