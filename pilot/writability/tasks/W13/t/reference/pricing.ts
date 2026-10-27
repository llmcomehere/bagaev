/** @implements PriceRules.non_negative, PriceRules.rounding */
export function roundPrice(p: number): number {
  return p <= 0 ? 0 : Math.ceil(p / 10) * 10;
}
/** @checks PriceRules.non_negative, PriceRules.rounding */
export function testRoundPriceRules(): void {
  const cases: Array<[number, number]> = [[-5, 0], [30, 30], [31, 40]];
  for (const [x, want] of cases) if (roundPrice(x) !== want) throw new Error(`roundPrice(${x})`);
}
