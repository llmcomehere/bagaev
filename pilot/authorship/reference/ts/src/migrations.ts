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

export const MIGRATIONS: Migration[] = [
  {
    // «Один автор → список»: прежний автор становится единственным в списке; редакторы и ревизии сохраняются.
    version: 2,
    name: "authors_list",
    up: (db) => {
      db.exec(`
        CREATE TABLE articles_v2 (id TEXT PRIMARY KEY, title TEXT NOT NULL, author_ids TEXT NOT NULL,
          editor_ids TEXT NOT NULL, revision INTEGER NOT NULL);
        INSERT INTO articles_v2 SELECT id, title, json_array(author_id), editor_ids, revision FROM articles;
        DROP TABLE articles;
        ALTER TABLE articles_v2 RENAME TO articles;`);
    },
  },
];

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
