/**
 * Хранилище приложения: SQLite (node:sqlite) и репозиторий по таблицам.
 * Доступ к данным — только через объекты репозитория ниже: чтение и запись таблиц видны по вызовам.
 * Базовая схема (версия 1) создаётся при открытии; дальнейшие изменения — только миграциями (migrations.ts).
 */
import { DatabaseSync } from "node:sqlite";
import type { SQLValue } from "node:sqlite";
import type { Person, PersonId } from "./people.ts";
import type { Actor, ActorId } from "./actors.ts";
import type { Article, ArticleId } from "./articles.ts";

export type Db = DatabaseSync;

const BASE_SCHEMA = `
CREATE TABLE IF NOT EXISTS meta (name TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS people (id TEXT PRIMARY KEY, display_name TEXT NOT NULL, email TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS actors (id TEXT PRIMARY KEY, person_id TEXT);
CREATE TABLE IF NOT EXISTS articles (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, author_id TEXT NOT NULL, editor_ids TEXT NOT NULL, revision INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS author_index (person_id TEXT PRIMARY KEY, article_ids TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notifications (
  key TEXT PRIMARY KEY, recipient TEXT NOT NULL, article_id TEXT NOT NULL, subject TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS comments (id TEXT PRIMARY KEY, article_id TEXT NOT NULL, person_id TEXT NOT NULL, text TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS views (article_id TEXT PRIMARY KEY, count INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS outbox (seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
  type TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS inbox (handler TEXT NOT NULL, event_id TEXT NOT NULL, PRIMARY KEY (handler, event_id));
CREATE TABLE IF NOT EXISTS receipts (key TEXT PRIMARY KEY, request TEXT NOT NULL, response TEXT NOT NULL);
INSERT OR IGNORE INTO meta VALUES ('schema_version', '1');
`;

export function open(path: string): Db {
  const db = new DatabaseSync(path);
  db.exec("PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;");
  db.exec(BASE_SCHEMA);
  return db;
}

/** Одна транзакция записи: исключение откатывает всё. */
export function tx<T>(db: Db, body: () => T): T {
  db.exec("BEGIN IMMEDIATE");
  try {
    const out = body();
    db.exec("COMMIT");
    return out;
  } catch (e) {
    db.exec("ROLLBACK");
    throw e;
  }
}

const text = (v: SQLValue | undefined): string => String(v ?? "");
const num = (v: SQLValue | undefined): number => Number(v ?? 0);

export const meta = {
  get(db: Db, name: string): string | undefined {
    const row = db.prepare("SELECT value FROM meta WHERE name = ?").get(name);
    return row === undefined ? undefined : text(row["value"]);
  },
  set(db: Db, name: string, value: string): void {
    db.prepare("INSERT INTO meta VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET value = excluded.value").run(name, value);
  },
};

export const people = {
  all(db: Db): Map<PersonId, Person> {
    const out = new Map<PersonId, Person>();
    for (const r of db.prepare("SELECT id, display_name, email FROM people ORDER BY id").all()) {
      out.set(text(r["id"]), { id: text(r["id"]), displayName: text(r["display_name"]), email: text(r["email"]) });
    }
    return out;
  },
  put(db: Db, p: Person): void {
    db.prepare("INSERT OR REPLACE INTO people VALUES (?, ?, ?)").run(p.id, p.displayName, p.email);
  },
};

export const actors = {
  get(db: Db, id: ActorId): Actor | undefined {
    const r = db.prepare("SELECT id, person_id FROM actors WHERE id = ?").get(id);
    return r === undefined ? undefined : { id: text(r["id"]), person: r["person_id"] === null ? null : text(r["person_id"]) };
  },
  put(db: Db, a: Actor): void {
    db.prepare("INSERT OR REPLACE INTO actors VALUES (?, ?)").run(a.id, a.person);
  },
};

function articleOf(r: Record<string, SQLValue>): Article {
  return {
    id: text(r["id"]),
    title: text(r["title"]),
    author: text(r["author_id"]),
    editors: JSON.parse(text(r["editor_ids"])) as ActorId[],
    revision: num(r["revision"]),
  };
}

export const articles = {
  get(db: Db, id: ArticleId): Article | undefined {
    const r = db.prepare("SELECT * FROM articles WHERE id = ?").get(id);
    return r === undefined ? undefined : articleOf(r);
  },
  all(db: Db): Article[] {
    return db.prepare("SELECT * FROM articles ORDER BY id").all().map(articleOf);
  },
  put(db: Db, a: Article): void {
    db.prepare("INSERT OR REPLACE INTO articles (id, title, author_id, editor_ids, revision) VALUES (?, ?, ?, ?, ?)")
      .run(a.id, a.title, a.author, JSON.stringify(a.editors), a.revision);
  },
};

/** Сохранённая проекция «человек → статьи»; строится из авторства. @derived_from Authorship */
export const authorIndex = {
  all(db: Db): Map<PersonId, ArticleId[]> {
    const out = new Map<PersonId, ArticleId[]>();
    for (const r of db.prepare("SELECT person_id, article_ids FROM author_index ORDER BY person_id").all()) {
      out.set(text(r["person_id"]), JSON.parse(text(r["article_ids"])) as ArticleId[]);
    }
    return out;
  },
  replaceAll(db: Db, index: Map<PersonId, ArticleId[]>): void {
    db.exec("DELETE FROM author_index");
    const ins = db.prepare("INSERT INTO author_index VALUES (?, ?)");
    for (const [p, ids] of index) ins.run(p, JSON.stringify(ids));
  },
};

export interface Notification { key: string; to: string; articleId: ArticleId; subject: string }

export const notifications = {
  all(db: Db): Notification[] {
    return db.prepare("SELECT * FROM notifications ORDER BY key").all().map((r) => ({
      key: text(r["key"]), to: text(r["recipient"]), articleId: text(r["article_id"]), subject: text(r["subject"]),
    }));
  },
  put(db: Db, n: Notification): void {
    db.prepare("INSERT OR REPLACE INTO notifications VALUES (?, ?, ?, ?)").run(n.key, n.to, n.articleId, n.subject);
  },
};

export interface Comment { id: string; articleId: ArticleId; author: PersonId; text: string }

export const comments = {
  forArticle(db: Db, articleId: ArticleId): Comment[] {
    return db.prepare("SELECT * FROM comments WHERE article_id = ? ORDER BY id").all(articleId).map((r) => ({
      id: text(r["id"]), articleId: text(r["article_id"]), author: text(r["person_id"]), text: text(r["text"]),
    }));
  },
  put(db: Db, c: Comment): void {
    db.prepare("INSERT OR REPLACE INTO comments VALUES (?, ?, ?, ?)").run(c.id, c.articleId, c.author, c.text);
  },
};

export const views = {
  get(db: Db, articleId: ArticleId): number {
    return num(db.prepare("SELECT count FROM views WHERE article_id = ?").get(articleId)?.["count"]);
  },
  put(db: Db, articleId: ArticleId, count: number): void {
    db.prepare("INSERT OR REPLACE INTO views VALUES (?, ?)").run(articleId, count);
  },
};

export interface Receipt { request: string; response: string }

export const receipts = {
  get(db: Db, key: string): Receipt | undefined {
    const r = db.prepare("SELECT request, response FROM receipts WHERE key = ?").get(key);
    return r === undefined ? undefined : { request: text(r["request"]), response: text(r["response"]) };
  },
  put(db: Db, key: string, r: Receipt): void {
    db.prepare("INSERT INTO receipts VALUES (?, ?, ?)").run(key, r.request, r.response);
  },
};
