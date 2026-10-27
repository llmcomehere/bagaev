/**
 * Локальная шина событий: outbox в той же транзакции, что и данные; доставка — отдельной транзакцией на каждый
 * обработчик; inbox (обработчик, событие) делает повтор доставки безвредным.
 */
import type { Db } from "./db.ts";
import { tx } from "./db.ts";
import type { AppEvent } from "./events.ts";
import { HANDLERS } from "./handlers.ts";

/** Поставить событие в outbox (внутри транзакции вызывающего). */
export function emit(db: Db, ev: AppEvent): void {
  db.prepare("INSERT INTO outbox (event_id, type, payload) VALUES (?, ?, ?)").run(ev.eventId, ev.type, JSON.stringify(ev));
}

interface Pending { eventId: string; type: string; event: AppEvent }

export function outbox(db: Db): Pending[] {
  return db.prepare("SELECT event_id, type, payload FROM outbox ORDER BY seq").all().map((r) => ({
    eventId: String(r["event_id"]), type: String(r["type"]), event: JSON.parse(String(r["payload"])) as AppEvent,
  }));
}

function done(db: Db, handler: string, eventId: string): boolean {
  return db.prepare("SELECT 1 FROM inbox WHERE handler = ? AND event_id = ?").get(handler, eventId) !== undefined;
}

/** Событие завершено, когда его обработали все подписанные обработчики. */
export function completed(db: Db, p: Pending): boolean {
  return (HANDLERS[p.type] ?? []).every((h) => done(db, h.name, p.eventId));
}

/** Доставить одно событие одному обработчику; уже обработанное не исполняется повторно. */
export function deliverOne(db: Db, p: Pending, h: { name: string; run: (db: Db, ev: AppEvent) => void }): boolean {
  return tx(db, () => {
    if (done(db, h.name, p.eventId)) return false;
    h.run(db, p.event);
    db.prepare("INSERT INTO inbox VALUES (?, ?)").run(h.name, p.eventId);
    return true;
  });
}

/** Доставить все недоставленные события по порядку outbox. */
export function deliver(db: Db): string[] {
  const finished: string[] = [];
  for (const p of outbox(db)) {
    if (completed(db, p)) continue;
    for (const h of HANDLERS[p.type] ?? []) deliverOne(db, p, h);
    if (completed(db, p)) finished.push(p.eventId);
  }
  return finished;
}
