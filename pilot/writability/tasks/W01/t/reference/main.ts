export function sum(xs: readonly number[]): number {
  return xs.reduce((a, x) => a + x, 0);
}
