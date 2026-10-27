import { Result, ok, err } from "./result";
export type AgeError = { readonly kind: "negative" } | { readonly kind: "too-large"; readonly value: number };
export function validateAge(a: number): Result<number, AgeError> {
  if (a < 0) return err({ kind: "negative" });
  if (a > 150) return err({ kind: "too-large", value: a });
  return ok(a);
}
