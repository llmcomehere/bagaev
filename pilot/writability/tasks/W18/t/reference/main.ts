import { Result } from "./result";
export function describe(r: Result<number, string> | undefined): string {
  if (r === undefined) return "нет";
  return r.ok ? String(r.value) : `ошибка: ${r.error}`;
}
