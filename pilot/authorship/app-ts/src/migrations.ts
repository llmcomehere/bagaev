/**
 * Миграции схемы данных: версия хранится в meta.schema_version. Команды приложения работают только со
 * схемой последней версии (SCHEMA_OUTDATED иначе); `migrate` применяет недостающие миграции одной транзакцией.
 */
import type { Db } from "./db.ts";
import { meta, tx } from "./db.ts";

export interface Migration {
  version: number;
  name: string;
  up: (db: Db) => void;
}

export const MIGRATIONS: Migration[] = [];

export const LATEST = MIGRATIONS.reduce((v, m) => Math.max(v, m.version), 1);

export function version(db: Db): number {
  return Number(meta.get(db, "schema_version") ?? "1");
}

export function migrate(db: Db): { outcome: "APPLIED" | "NOOP"; applied: string[] } {
  const pending = MIGRATIONS.filter((m) => m.version > version(db)).sort((a, b) => a.version - b.version);
  if (pending.length === 0) return { outcome: "NOOP", applied: [] };
  tx(db, () => {
    for (const m of pending) {
      m.up(db);
      meta.set(db, "schema_version", String(m.version));
    }
  });
  return { outcome: "APPLIED", applied: pending.map((m) => m.name) };
}
