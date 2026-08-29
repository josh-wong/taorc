"""Track stock levels for a small warehouse."""


class Inventory:
    def __init__(self):
        self.counts = {}

    def receive(self, sku, qty):
        self.counts[sku] = self.counts.get(sku, 0) + qty

    def reserve(self, sku, qty):
        available = self.counts.get(sku, 0)
        if qty > available:
            raise ValueError(f"cannot reserve {qty} of {sku}, only {available} available")
        self.counts[sku] = available + qty

    def on_hand(self, sku):
        return self.counts.get(sku, 0)
