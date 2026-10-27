// Минимальные объявления встроенных модулей Node 22, которыми пользуется приложение.
// Пакет @types/node не устанавливается (пилот без сторонних пакетов, кроме компилятора TypeScript).

declare module "node:sqlite" {
  export type SQLValue = null | number | bigint | string | Uint8Array;
  export interface RunResult { changes: number | bigint; lastInsertRowid: number | bigint }
  export class StatementSync {
    run(...params: SQLValue[]): RunResult;
    get(...params: SQLValue[]): Record<string, SQLValue> | undefined;
    all(...params: SQLValue[]): Record<string, SQLValue>[];
  }
  export class DatabaseSync {
    constructor(path: string);
    exec(sql: string): void;
    prepare(sql: string): StatementSync;
    close(): void;
  }
}

declare module "node:fs" {
  export function readFileSync(path: string, encoding: "utf-8"): string;
  export function mkdirSync(path: string, options?: { recursive?: boolean }): void;
  export function existsSync(path: string): boolean;
}

declare module "node:path" {
  export function join(...parts: string[]): string;
}

declare module "node:process" {
  export const argv: string[];
  export const stdout: { write(s: string): boolean };
  export function exit(code?: number): never;
}

declare module "node:test" {
  export function test(name: string, fn: () => void | Promise<void>): void;
}

declare module "node:assert/strict" {
  export function deepEqual(actual: unknown, expected: unknown, message?: string): void;
  export function equal(actual: unknown, expected: unknown, message?: string): void;
  export function ok(value: unknown, message?: string): void;
}

declare const console: { log(...args: unknown[]): void; error(...args: unknown[]): void };
