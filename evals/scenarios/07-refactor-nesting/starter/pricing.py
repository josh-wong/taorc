def compute_price(order):
    if order is not None:
        if order.get("items"):
            total = 0
            for item in order["items"]:
                if item.get("qty", 0) > 0:
                    if item.get("unit_price_cents", 0) > 0:
                        if item.get("category") == "food":
                            if order.get("state") in ("CA", "WA"):
                                total += item["qty"] * item["unit_price_cents"]
                            else:
                                total += int(item["qty"] * item["unit_price_cents"] * 1.05)
                        else:
                            if order.get("state") in ("CA", "WA"):
                                total += int(item["qty"] * item["unit_price_cents"] * 1.08)
                            else:
                                total += int(item["qty"] * item["unit_price_cents"] * 1.05)
                        if order.get("member"):
                            if total > 5000:
                                total = total - 500
            return total
        else:
            return 0
    else:
        return 0
