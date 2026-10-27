#!/usr/bin/env python3
"""Вариант C пилота: общий CLI-контракт (pilot/authorship/contract.md) поверх эталонного хоста bagaev (HOST-1).

  python3 pilot/authorship/arms/bagaev_cli.py --app DIR --state DIR <команда> [параметры]

Адаптер — часть стенда, а не приложения: он вызывает точки входа интерфейса приложения (contract.md §4) по именам
и переводит наблюдения CANON-11 в простой JSON. Единственная часть, знающая схему данных, — `seed`: она пишет
исходные строки D0 в форме исходной программы S0 (seed выполняется базовой версией приложения, contract.md §3).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ref"))
sys.setrecursionlimit(100000)

from bagaev_ref.host import driver as D, migrate as M  # noqa: E402
from bagaev_ref.host.store import Store  # noqa: E402
from bagaev_ref.kernel import canonical as C  # noqa: E402
from bagaev_ref.machine.runner import prepare  # noqa: E402

NS = "pilot"


def load_program(app: Path) -> D.Program:
    files = [(f.relative_to(app).as_posix(), f.read_bytes()) for f in sorted(app.rglob("*.bag"))]
    project, prog, pre = prepare(files)
    if pre is not None:
        raise SystemExit(json.dumps({"status": "error", "code": "PROGRAM_INVALID",
                                     "diagnostics": pre.get("diagnostics", [])[:5]}, ensure_ascii=False))
    return D.Program(project, prog)


# ------------------------------------------------------------ наблюдения CANON-11 ↔ простой JSON
def s(v: str) -> dict:
    return {"type": "String", "value": v}


def i64(n: int) -> dict:
    return {"type": "Int64", "value": str(n)}


def seq(t: str, items: list) -> dict:
    return {"type": f"Seq<{t}>", "items": items}


def plain(o):
    """Наблюдение → JSON: строки, целые, списки, записи — объекты, Option/Result — {"Some": …} и т. п."""
    if not isinstance(o, dict):
        return o
    t = o.get("type", "")
    if t == "Int64":
        return int(o["value"])
    if t in ("String", "Bool"):
        return o["value"]
    if t == "Unit":
        return None
    if "items" in o:
        return [plain(x) for x in o["items"]]
    if "entries" in o:
        return [[plain(k), plain(v)] for k, v in o["entries"]]
    if "fields" in o:
        return {k: plain(v) for k, v in o["fields"].items()}
    if "tag" in o:
        return {o["tag"]: plain(o["payload"]) if "payload" in o else None}
    if "value" in o:
        return plain(o["value"])
    return o


def result_of(obs: dict):
    """(ok, значение) из наблюдения Result<T, String> точки входа."""
    v = obs.get("value")
    p = plain(v)
    if isinstance(p, dict) and len(p) == 1:
        (tag, val), = p.items()
        if tag == "Ok":
            return True, val
        if tag == "Err":
            return False, val
    return None, p


# ------------------------------------------------------------ события
def payload_field(payload: bytes, name: str):
    o = C.decode(bytes(payload))
    return plain(o).get(name) if isinstance(plain(o), dict) else None


def events(st: Store, prog: D.Program) -> list:
    """[(seq, event_id, завершено ли всеми обработчиками)] по outbox и inbox хоста."""
    handlers = {}
    for h in prog.handlers:
        from bagaev_ref.sema import types as T
        handlers.setdefault(T.prune(h.params[0]).info.qname, []).append(h.qname)
    out = []
    for seq_no, ev, payload in st.db.execute("SELECT seq, event, payload FROM outbox ORDER BY seq"):
        done = {r[0] for r in st.db.execute("SELECT handler FROM inbox WHERE seq = ? AND outcome = 'COMMITTED'",
                                            (seq_no,))}
        out.append((seq_no, payload_field(payload, "event_id"), all(h in done for h in handlers.get(ev, []))))
    return out


# ------------------------------------------------------------ команды
def cmd_seed(st, prog, a):
    data = json.loads(Path(a.data).read_text(encoding="utf-8"))
    pid = lambda x: {"type": "blog.people.PersonId", "value": s(x)}
    act = lambda x: {"type": "blog.actors.ActorId", "value": s(x)}
    art = lambda x: {"type": "blog.articles.ArticleId", "value": s(x)}
    tables = {
        "blog.db.Blog.people": [[pid(p["person_id"]), {"type": "blog.people.Person", "fields": {
            "id": pid(p["person_id"]), "display_name": s(p["display_name"]), "email": s(p["email"])}}]
            for p in data["people"]],
        "blog.db.Blog.actors": [[act(x["actor_id"]), {"type": "blog.actors.Actor", "fields": {
            "id": act(x["actor_id"]),
            "person": {"type": "Option<blog.people.PersonId>", "tag": "Some", "payload": pid(x["person_id"])}
            if x["person_id"] else {"type": "Option<blog.people.PersonId>", "tag": "None"}}}]
            for x in data["actors"]],
        "blog.db.Blog.articles": [[art(r["article_id"]), {"type": "blog.articles.Article", "fields": {
            "id": art(r["article_id"]), "title": s(r["title"]), "author": pid(r["author_id"]),
            "editors": seq("blog.actors.ActorId", [act(e) for e in r["editor_ids"]]),
            "revision": i64(r["article_revision"])}}] for r in data["articles"]],
        "blog.db.Blog.author_index": [[pid(p), seq("blog.articles.ArticleId", [art(x) for x in ids])]
                                      for p, ids in data["author_index"].items()],
    }
    for t, rows in tables.items():
        r = D.seed(st, prog, t, rows)
        if r.get("outcome") not in ("SEEDED", None) and "code" in r:
            return {"status": "error", "code": r["code"], "table": t}
    return {"status": "ok"}


def cmd_migrate(st, prog, a):
    p = M.plan(st, prog)
    if p.get("outcome") == "UP_TO_DATE":
        return {"status": "ok", "outcome": "NOOP"}
    if "code" in p:
        return {"status": "rejected", "code": p["code"], "detail": p.get("detail")}
    r = M.apply(st, prog)
    if r.get("outcome") == "APPLIED":
        return {"status": "ok", "outcome": "APPLIED", "rows": r.get("rows")}
    if r.get("outcome") in ("NOOP", "UNCHANGED"):
        return {"status": "ok", "outcome": "NOOP"}
    return {"status": "rejected", "code": r.get("code", r.get("outcome"))}


def cmd_set_authors(st, prog, a):
    c = json.loads(Path(a.command).read_text(encoding="utf-8"))
    args = [s(c["actor_id"]), s(c["article_id"]), seq("String", [s(x) for x in c["author_ids"]]),
            i64(c["expected_article_revision"])]
    r = D.run_command(st, prog, "blog.editor.set_authors", args, {"namespace": NS, "key": c["idempotency_key"]})
    if r.get("outcome") == "REFUSED" or ("code" in r and "value" not in r):
        return {"status": "error", "code": r.get("code"), "detail": r.get("detail")}
    ok, val = result_of(r)
    replayed = bool(r.get("replayed"))
    if ok:
        return {"status": "ok", "article_revision": val, "replayed": replayed}
    if ok is False:
        return {"status": "rejected", "code": val, "replayed": replayed}
    return {"status": "error", "code": r.get("termination", "UNEXPECTED"), "raw": r}


def cmd_deliver(st, prog, a):
    before = {e for _, e, done in events(st, prog) if done}
    res = D.deliver(st, prog)
    stuck = [x for x in res if x.get("outcome") not in ("COMMITTED",) and not x.get("replayed")]
    after = [e for _, e, done in events(st, prog) if done and e not in before]
    out = {"status": "ok", "completed_event_ids": after}
    if stuck:
        out["stuck"] = [{"handler": x.get("handler"), "outcome": x.get("outcome"), "code": x.get("code")} for x in stuck]
    return out


def cmd_redeliver(st, prog, a):
    seqs = [n for n, e, _ in events(st, prog) if e == a.event]
    if not seqs:
        return {"status": "rejected", "code": "UNKNOWN_EVENT"}
    rerun = False
    for h in prog.handlers:
        for r in D.deliver(st, prog, handler=h.qname, seq=seqs[0]):
            rerun = rerun or (r.get("outcome") == "COMMITTED" and not r.get("replayed"))
    return {"status": "ok", "reexecuted": rerun}


def query(st, prog, entry, args):
    r = D.run_query(st, prog, entry, args)
    if "value" not in r:
        return None, r
    return plain(r["value"]), None


def simple(entry, key, argname=None):
    def run(st, prog, a):
        args = [s(getattr(a, argname))] if argname else []
        v, err = query(st, prog, entry, args)
        if err is not None:
            return {"status": "error", "code": err.get("code", err.get("termination")), "raw": err}
        return {"status": "ok", key: v}
    return run


def cmd_state(st, prog, a):
    arts, e1 = query(st, prog, "blog.view.articles_view", [])
    idx, e2 = query(st, prog, "blog.view.index_view", [])
    if e1 or e2:
        return {"status": "error", "code": (e1 or e2).get("code"), "raw": e1 or e2}
    evs = events(st, prog)
    return {"status": "ok",
            "articles": sorted(arts, key=lambda r: r["article_id"]),
            "author_index": {r["person_id"]: r["article_ids"] for r in idx},
            "outbox_pending_event_ids": [e for _, e, done in evs if not done],
            "inbox_completed_event_ids": [e for _, e, done in evs if done]}


def cmd_resize(st, prog, a):
    inp = json.loads(Path(a.input).read_text(encoding="utf-8"))
    src, size = inp["input"], inp["requested_output_size"]
    px = seq("Seq<Int64>", [seq("Int64", [i64(c) for c in p]) for p in src["pixels_row_major"]])
    v, err = query(st, prog, "blog.image.resize_pixels",
                   [i64(src["width"]), i64(src["height"]), px, i64(size["width"]), i64(size["height"])])
    if err is not None:
        return {"status": "error", "code": err.get("code", err.get("termination")), "raw": err}
    return {"status": "ok", "output": {"pixel_format": src.get("pixel_format", "RGBA8"), "width": size["width"],
                                       "height": size["height"], "pixels_row_major": v}}


COMMANDS = {
    "seed": cmd_seed, "migrate": cmd_migrate, "set-authors": cmd_set_authors, "deliver-events": cmd_deliver,
    "redeliver": cmd_redeliver, "state": cmd_state, "resize": cmd_resize,
    "byline": simple("blog.byline.byline_of", "byline", "article"),
    "export": simple("blog.export.export_of", "export", "article"),
    "search": simple("blog.search.articles_by", "article_ids", "person"),
    "profile": simple("blog.profile.profile_articles", "article_ids", "person"),
    "rss": simple("blog.rss.feed", "feed"),
    "notifications": simple("blog.view.notifications_view", "notifications"),
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="bagaev_cli")
    ap.add_argument("--app", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("command", choices=sorted(COMMANDS))
    for opt in ("data", "command-file", "article", "person", "event", "input"):
        ap.add_argument("--" + opt)
    a = ap.parse_args(argv)
    a.command_name, a.command = a.command, getattr(a, "command_file")
    Path(a.state).mkdir(parents=True, exist_ok=True)
    prog = load_program(Path(a.app))
    st = Store(str(Path(a.state) / "state.db"))
    try:
        out = COMMANDS[a.command_name](st, prog, a)
    finally:
        st.close()
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
