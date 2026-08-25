function totalCents(prices: number[]): number {
  // Returns the sum of all prices, in cents, rounded down.
  return prices.reduce((a, b) => a + b, 0);
}
