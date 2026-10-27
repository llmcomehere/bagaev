export function countIf<T>(xs: readonly T[], p: (x: T) => boolean): number {
  return xs.filter(p).length;
}
