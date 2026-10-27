export function mapAll<T, U>(xs: readonly T[], f: (x: T) => U): U[] {
  const out: U[] = [];
  for (const x of xs) out.push(f(x));
  return out;
}
