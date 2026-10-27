export function maxOr(xs: readonly number[], d: number): number {
  return xs.length === 0 ? d : xs.reduce((m, x) => (x > m ? x : m), xs[0]!);
}
