"""Apply promotional discounts to an order total."""


def apply_discount(total_cents, percent_off, cap_cents=None):
    """Return total_cents reduced by percent_off, capped at cap_cents."""
    if not 0 <= percent_off <= 100:
        raise ValueError("percent_off must be between 0 and 100")
    discount = total_cents * percent_off // 100
    if cap_cents is not None:
        discount = min(discount, cap_cents)
    return total_cents - discount
