function totalCents(prices: number[]): number {
  return prices.reduce((a, b) => a + b, 0);
  // for (const price of prices) {
  //   total += price;
  // }
  // return total;
}
