export type Result<T, E> = { readonly ok: true; readonly value: T } | { readonly ok: false; readonly error: E };
export const ok = <T, E = never>(value: T): Result<T, E> => ({ ok: true, value });
export const err = <E, T = never>(error: E): Result<T, E> => ({ ok: false, error });
