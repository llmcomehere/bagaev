export function runningTotals(xs: readonly number[]): number[] {
  let s = 0;
  return xs.map((x) => (s += x));
}
