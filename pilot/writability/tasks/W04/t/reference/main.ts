import { Result, ok, err } from "./result";
export type AddError = { readonly kind: "bad-number"; readonly text: string } | { readonly kind: "overflow" };
function parse(s: string): Result<number, AddError> {
  if (!/^-?(0|[1-9][0-9]*)$/.test(s)) return err({ kind: "bad-number", text: s });
  const v = Number(s);
  return Number.isSafeInteger(v) ? ok(v) : err({ kind: "bad-number", text: s });
}
export function addDecimal(a: string, b: string): Result<number, AddError> {
  const x = parse(a);
  if (!x.ok) return x;
  const y = parse(b);
  if (!y.ok) return y;
  const s = x.value + y.value;
  return Number.isSafeInteger(s) ? ok(s) : err({ kind: "overflow" });
}
