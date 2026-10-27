export type IntList = { readonly kind: "nil" } | { readonly kind: "cons"; readonly head: number; readonly tail: IntList };
export function listSum(l: IntList): number {
  return l.kind === "nil" ? 0 : l.head + listSum(l.tail);
}
export function fromArray(xs: readonly number[]): IntList {
  let acc: IntList = { kind: "nil" };
  for (let i = xs.length - 1; i >= 0; i--) acc = { kind: "cons", head: xs[i]!, tail: acc };
  return acc;
}
