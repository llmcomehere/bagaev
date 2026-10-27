/**
 * Общий CLI-контракт пилота (pilot/authorship/contract.md): `node src/cli.ts --state DIR <команда> [параметры]`.
 * Ответ — одна строка JSON на stdout.
 */
import { argv, exit, stdout } from "node:process";
import { mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import type { Db } from "./db.ts";
import { actors, articles, authorIndex, notifications, open, people, tx } from "./db.ts";
import { completed, deliver, deliverOne, outbox } from "./bus.ts";
import { HANDLERS } from "./handlers.ts";
import type { SetAuthorsCommand } from "./editor.ts";
import { setAuthors } from "./editor.ts";
import { LATEST, migrate, version } from "./migrations.ts";
import { bylineOf } from "./byline.ts";
import { exportOf } from "./export.ts";
import { articlesBy } from "./search.ts";
import { profileArticles } from "./profile.ts";
import { feed } from "./rss.ts";
import { pipeline } from "./image.ts";

type Json = null | boolean | number | string | Json[] | { [k: string]: Json };
type Opts = Record<string, string>;

function readJson(path: string | undefined): any {
  if (path === undefined) throw new Error("нужен путь к JSON");
  return JSON.parse(readFileSync(path, "utf-8"));
}

interface SeedData {
  people: { person_id: string; display_name: string; email: string }[];
  actors: { actor_id: string; person_id: string | null }[];
  articles: { article_id: string; article_revision: number; title: string; author_id: string; editor_ids: string[] }[];
  author_index: Record<string, string[]>;
}

/** Исходные строки D0 в схеме версии 1 (выполняет базовая версия приложения). */
function seed(db: Db, data: SeedData): Json {
  tx(db, () => {
    for (const p of data.people) people.put(db, { id: p.person_id, displayName: p.display_name, email: p.email });
    for (const a of data.actors) actors.put(db, { id: a.actor_id, person: a.person_id });
    for (const a of data.articles) {
      articles.put(db, { id: a.article_id, title: a.title, author: a.author_id, editors: a.editor_ids, revision: a.article_revision });
    }
    authorIndex.replaceAll(db, new Map(Object.entries(data.author_index)));
  });
  return { status: "ok" };
}

function state(db: Db): Json {
  const events = outbox(db);
  return {
    status: "ok",
    articles: articles.all(db).map((a) => ({
      article_id: a.id, article_revision: a.revision, title: a.title, author_ids: [a.author], editor_ids: a.editors,
    })),
    author_index: Object.fromEntries(authorIndex.all(db)),
    outbox_pending_event_ids: events.filter((e) => !completed(db, e)).map((e) => e.eventId),
    inbox_completed_event_ids: events.filter((e) => completed(db, e)).map((e) => e.eventId),
  };
}

function redeliver(db: Db, eventId: string | undefined): Json {
  const p = outbox(db).find((e) => e.eventId === eventId);
  if (p === undefined) return { status: "rejected", code: "UNKNOWN_EVENT" };
  let reexecuted = false;
  for (const h of HANDLERS[p.type] ?? []) reexecuted = deliverOne(db, p, h) || reexecuted;
  return { status: "ok", reexecuted };
}

const COMMANDS: Record<string, (db: Db, o: Opts) => Json> = {
  seed: (db, o) => seed(db, readJson(o["data"]) as SeedData),
  migrate: (db) => ({ status: "ok", outcome: migrate(db).outcome }),
  "set-authors": (db, o) => setAuthors(db, readJson(o["command-file"]) as SetAuthorsCommand),
  "deliver-events": (db) => ({ status: "ok", completed_event_ids: deliver(db) }),
  redeliver: (db, o) => redeliver(db, o["event"]),
  byline: (db, o) => ({ status: "ok", byline: bylineOf(db, o["article"] ?? "") }),
  export: (db, o) => ({ status: "ok", export: exportOf(db, o["article"] ?? "") }),
  search: (db, o) => ({ status: "ok", article_ids: articlesBy(db, o["person"] ?? "") }),
  profile: (db, o) => ({ status: "ok", article_ids: profileArticles(db, o["person"] ?? "") }),
  rss: (db) => ({ status: "ok", feed: feed(db) }),
  notifications: (db) => ({
    status: "ok",
    notifications: notifications.all(db).map((n) => ({ key: n.key, to: n.to, article_id: n.articleId })),
  }),
  resize: (_db, o) => {
    const inp = readJson(o["input"]);
    const out = pipeline({ width: inp.input.width, height: inp.input.height, pixels: inp.input.pixels_row_major },
      inp.requested_output_size.width, inp.requested_output_size.height);
    return { status: "ok", output: { pixel_format: inp.input.pixel_format ?? "RGBA8", width: out.width, height: out.height,
      pixels_row_major: out.pixels } };
  },
  state,
};

function main(args: string[]): number {
  const opts: Opts = {};
  let command: string | undefined;
  for (let i = 0; i < args.length; i++) {
    const a = args[i] ?? "";
    if (a.startsWith("--")) {
      opts[a.slice(2)] = args[i + 1] ?? "";
      i++;
    } else command = a;
  }
  const run = command === undefined ? undefined : COMMANDS[command];
  const dir = opts["state"];
  if (run === undefined || dir === undefined) {
    stdout.write(JSON.stringify({ status: "error", code: "USAGE" }) + "\n");
    return 2;
  }
  mkdirSync(dir, { recursive: true });
  const db = open(join(dir, "state.db"));
  try {
    if (!["seed", "migrate", "resize"].includes(command ?? "") && version(db) !== LATEST) {
      stdout.write(JSON.stringify({ status: "error", code: "SCHEMA_OUTDATED", version: version(db), latest: LATEST }) + "\n");
      return 0;
    }
    stdout.write(JSON.stringify(run(db, opts)) + "\n");
  } finally {
    db.close();
  }
  return 0;
}

exit(main(argv.slice(2)));
