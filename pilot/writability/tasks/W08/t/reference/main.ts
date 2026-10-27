export type Email = string & { readonly __brand: "Email" };
export function makeEmail(s: string): Email | undefined {
  return s.includes("@") ? (s as Email) : undefined;
}
export function emailText(e: Email): string {
  return e;
}
