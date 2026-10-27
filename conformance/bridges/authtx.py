#!/usr/bin/env python3
"""Мост HOST-1 ↔ замороженная модель AUTH-TX-0.1 (models/r07-core/experiments/authorship-transition).

Последовательности A01–A12 фикстуры models/r07-core/fixtures/authorship-transition.json исполняются дважды:
моделью (оракул, импортируется только для чтения) и хостом эталона над программой bridges/authtx/authtx.bag
в настоящем SQLite. После каждого шага сравниваются:
- исход наблюдения: статус, код, повтор;
- ревизии и авторы статей, проекции, индекс «человек → статьи», идентификаторы событий outbox;
- StateVersion со сдвигом: хост засевает таблицы отдельными транзакциями (+3), у него нет ACK (−1 за каждый ACK
  модели), а Err команды фиксирует квитанцию (+1, HST-06).

Расхождения, объяснённые решениями HOST-1, не считаются ошибкой, но перечисляются:
- ERR_RECEIPT: Err команды пишет квитанцию и увеличивает StateVersion, модель ничего не пишет;
- ERR_RESERVES_KEY: тот же ключ после Err занят; модель разрешает повтор с другим запросом (A09). После такого
  шага состояние больше не сравнивается (модель могла зафиксировать то, что хост отверг), а исходы шагов на других
  ключах сравниваются дальше; вердикт последовательности — DEVIATION;
- шаги без соответствия (ACK, чтение при недоступности, guard у доставки) — NOT_APPLICABLE.

  python3 conformance/bridges/authtx.py [--json]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ref"))
sys.dont_write_bytecode = True

from bagaev_ref.host import driver as D  # noqa: E402
from bagaev_ref.host.store import Store  # noqa: E402
from bagaev_ref.machine.runner import prepare  # noqa: E402

ENGINE = ROOT / "models" / "r07-core" / "experiments" / "authorship-transition" / "engine.py"
FIXTURE = ROOT / "models" / "r07-core" / "fixtures" / "authorship-transition.json"
APP = Path(__file__).resolve().parent / "authtx"
ENTRY, HANDLER = "authtx.replace_authorship", "authtx.project"
CUT = {"none": None, "before_commit": "before_commit", "after_commit_before_reply": "after_commit"}
REJECTION = {"UnknownArticle": "UNKNOWN_ARTICLE", "PermissionDenied": "PERMISSION_DENIED", "EmptyAuthors": "EMPTY_AUTHORS",
             "DuplicateAuthor": "DUPLICATE_AUTHOR", "UnknownPerson": "UNKNOWN_PERSON", "ArticleConflict": "ARTICLE_CONFLICT"}
SEEDS = 4                                   # people, articles, projections, author_index — по транзакции


def load_engine():
    spec = importlib.util.spec_from_file_location("authorship_transition_engine_r07", ENGINE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["authorship_transition_engine_r07"] = mod
    spec.loader.exec_module(mod)
    return mod


def s(v):
    return {"type": "String", "value": v}


def i(v):
    return {"type": "Int64", "value": str(v)}


def strs(xs):
    return {"type": "Seq<String>", "items": [s(x) for x in xs]}


def flag():
    return {"type": "Bool", "value": True}


def article(rev, authors, editors):
    return {"type": "authtx.Article", "fields": {"revision": i(rev), "authors": strs(authors), "editors": strs(editors)}}


def projection(rev, authors):
    return {"type": "authtx.Projection", "fields": {"revision": i(rev), "authors": strs(authors)}}


def keyref(req: dict) -> dict:
    """KeyRef модели — (store, actor, command_id); у хоста namespace = actor, key — command_id до 16 символов."""
    return {"namespace": req["actor_id"], "key": req["command_id"].ljust(16, "_")}


def args(req: dict) -> list:
    return [s(req["actor_id"]), s(req["command_id"]), s(req["article_id"]), i(req["expected_article_version"]),
            strs(req["author_ids"])]


def event_row(f: dict) -> tuple:
    """Полезная нагрузка события хоста в полях модели: id, статья, ревизия, авторы, actor и команда-причина."""
    v = lambda x: x["value"]
    return (v(f["event_id"]), v(f["article"]), int(v(f["revision"])), tuple(v(x) for x in f["authors"]["items"]),
            v(f["actor"]), v(f["command"]))


class Host:
    def __init__(self, program, initial: dict):
        self.tmp = tempfile.mkdtemp(prefix="bag-authtx-")
        self.db = os.path.join(self.tmp, "store.db")
        self.program = program
        self.st = Store(self.db)
        arts = initial["articles"]
        idx = {p: {} for p in initial["people"]}
        for a in arts:
            for p in a["author_ids"]:
                idx[p][a["article_id"]] = True
        for table, rows in (
                ("people", [[s(p), flag()] for p in initial["people"]]),
                ("articles", [[s(a["article_id"]), article(a["article_revision"], a["author_ids"], a["editor_ids"])] for a in arts]),
                ("projections", [[s(a["article_id"]), projection(a["article_revision"], a["author_ids"])] for a in arts]),
                ("author_index", [[s(p), {"type": "Map<String,Bool>", "entries": [[s(x), flag()] for x in sorted(m)]}]
                                  for p, m in idx.items()])):
            r = D.seed(self.st, program, f"authtx.A.{table}", rows)
            assert r["outcome"] == "COMMITTED", r

    def guarded(self, fn, crash):
        D.SIMULATED_CRASH = crash
        try:
            return fn()
        except D.Crashed:
            self.st.db.close()               # как kill -9: незафиксированная транзакция теряется
            self.st = Store(self.db)
            return {"outcome": "CRASHED"}
        finally:
            D.SIMULATED_CRASH = None

    def seq_of(self, event_id: str):
        for seq, payload in self.st.db.execute("SELECT seq, payload FROM outbox ORDER BY seq"):
            if json.loads(bytes(payload))["fields"]["event_id"]["value"] == event_id:
                return seq
        return None

    def view(self) -> dict:
        d = D.dump(self.st, self.program)
        t = d["tables"]
        val = lambda o: o["value"]
        return {
            "state_version": d["state_version"],
            "articles": {val(k): (int(val(v["fields"]["revision"])), [val(x) for x in v["fields"]["authors"]["items"]])
                         for k, v in t["authtx.A.articles"]},
            "projections": {val(k): (int(val(v["fields"]["revision"])), [val(x) for x in v["fields"]["authors"]["items"]])
                            for k, v in t["authtx.A.projections"]},
            "index": {val(k): [val(e[0]) for e in v["entries"]] for k, v in t["authtx.A.author_index"] if v["entries"]},
            "events": sorted(event_row({f: v for f, v in o["payload"]["fields"].items()}) for o in d["outbox"]),
            "processed": {val(k): val(v) for k, v in t["authtx.A.processed"]},
        }

    def close(self):
        self.st.close()
        for f in os.listdir(self.tmp):
            os.remove(os.path.join(self.tmp, f))
        os.rmdir(self.tmp)


def model_view(state) -> dict:
    return {
        "articles": {a.article_id: (a.article_revision, list(a.author_ids)) for a in state.articles},
        "projections": {p.article_id: (p.article_revision, list(p.author_ids)) for p in state.projections},
        "index": {e.person_id: sorted(e.article_ids) for e in state.author_index if e.article_ids},
        "events": sorted((e.event_id, e.article_id, e.article_revision, tuple(e.author_ids), e.causation_actor_id,
                          e.causation_id) for e in state.outbox),
    }


def host_command_obs(r: dict):
    """Наблюдение хоста в словаре модели: (статус, код, повтор); Err — RESULT_ERR (квитанция HST-06)."""
    if r["outcome"] == "CRASHED":
        return ("UNKNOWN", "REPLY_LOST", False)
    if r["outcome"] == "REFUSED":
        return ("REJECTED", {"STALE_STATE": "STATE_CONFLICT"}.get(r["code"], r["code"]), False)
    if r["outcome"] == "ABSENT_AT_READ":
        return ("ABSENT_AT_READ", "NO_RECEIPT", False)
    if r["outcome"] in ("COMMITTED", "ABORTED", "RESULT") and "value" in r:
        v = r["value"]
        replayed = r.get("replayed", r["outcome"] == "RESULT")
        if v["tag"] == "Ok":
            return ("RESULT", v["payload"]["tag"].upper(), replayed)
        return ("RESULT_ERR", REJECTION[v["payload"]["tag"]], replayed)
    return ("UNEXPECTED", json.dumps(r, ensure_ascii=False)[:160], False)


def run_sequence(E, fixture, seq_def, program) -> dict:
    init = fixture["initial"]
    mstate = E.make_initial_state(init["store_id"], tuple(init["people"]), tuple(E.Article(**a) for a in init["articles"]))
    host = Host(program, init)
    base = SEEDS - mstate.state_version
    errs = acks = 0
    err_keys = set()
    state_diverged = False
    rows, verdict = [], "MATCH"
    try:
        for n, step in enumerate(seq_def["steps"], 1):
            act = step["action"]
            op = act["op"]
            note = None
            mobs, host_obs = None, None
            if op in ("replace", "recover_command"):
                req = fixture["requests"][act["request_ref"]]
                mreq = E.ReplaceAuthorship(**{**req, "author_ids": tuple(req["author_ids"])})
            if op == "replace":
                tr = E.replace_authorship(mstate, mreq, expected_state_version=act.get("expected_state_version"),
                                          cut=act.get("cut", "none"))
                guard = act.get("expected_state_version")
                hexp = None if guard is None else guard + base + errs - acks
                r = host.guarded(lambda: D.run_command(host.st, program, ENTRY, args(req), keyref(req),
                                                       expected_state=hexp), CUT[act.get("cut", "none")])
                host_obs = host_command_obs(r)
                mstate, mobs = tr.state, tr.observation
            elif op == "deliver":
                event = next(e for e in mstate.outbox if e.event_id == act["event_id"])
                tr = E.deliver_event(mstate, event, expected_state_version=act.get("expected_state_version"),
                                     cut=act.get("cut", "none"))
                mstate, mobs = tr.state, tr.observation
                if act.get("expected_state_version") is not None and not mobs.replayed:
                    note = "NOT_APPLICABLE: у доставки V1 нет guard'а StateVersion"
                else:
                    seq = host.seq_of(act["event_id"])
                    r = host.guarded(lambda: D.deliver(host.st, program, HANDLER, seq), CUT[act.get("cut", "none")])
                    if isinstance(r, dict):
                        host_obs = ("UNKNOWN", "REPLY_LOST", False)
                    elif r and r[0]["outcome"] == "COMMITTED":
                        host_obs = ("RESULT", host.view()["processed"].get(act["event_id"]), r[0]["replayed"])
                    else:
                        host_obs = ("UNEXPECTED", json.dumps(r, ensure_ascii=False)[:160], False)
            elif op == "ack":
                tr = E.acknowledge_event(mstate, act["event_id"], expected_state_version=act.get("expected_state_version"),
                                         cut=act.get("cut", "none"))
                if tr.actual_commit:
                    acks += 1
                mstate, mobs = tr.state, tr.observation
                note = "NOT_APPLICABLE: отдельного ACK в V1 нет, запись inbox — квитанция обработки (HST-11)"
            elif op == "recover_command":
                mobs = E.recover_command(mstate, mreq, available=act.get("available", True))
                if not act.get("available", True):
                    note = "NOT_APPLICABLE: недоступность чтения — свойство канала клиента"
                else:
                    host_obs = host_command_obs(D.status(host.st, keyref(req), program, ENTRY, args(req)))
            elif op == "recover_event":
                event = next((e for e in mstate.outbox if e.event_id == act["event_id"]), None)
                mobs = E.recover_event(mstate, event, available=act.get("available", True))
                if not act.get("available", True):
                    note = "NOT_APPLICABLE: недоступность чтения — свойство канала клиента"
                else:
                    seq = host.seq_of(act["event_id"])
                    r = D.event_status(host.st, HANDLER, seq) if seq is not None else {"outcome": "ABSENT_AT_READ"}
                    host_obs = (("RESULT", host.view()["processed"].get(act["event_id"]), True) if r["outcome"] == "RESULT"
                                else ("ABSENT_AT_READ", "NO_RECEIPT", False))
            else:
                raise ValueError(op)
            want = (mobs.status, mobs.code, bool(mobs.replayed))
            row = {"step": n, "op": op, "model": list(want)}
            for ptr, key in (("/observation/status", 0), ("/observation/code", 1)):   # оракул совпадает с фикстурой
                if ptr in step.get("expected", {}) and step["expected"][ptr] != want[key]:
                    raise AssertionError(f"{seq_def['id']} шаг {n}: модель расходится с фикстурой по {ptr}")
            if note:
                row["status"], row["note"] = "NOT_APPLICABLE", note
                rows.append(row)
                continue
            row["host"] = list(host_obs)
            k = (keyref(req)["namespace"], keyref(req)["key"]) if op in ("replace", "recover_command") else None
            if host_obs == want:
                row["status"] = "MATCH"
            elif host_obs[0] == "RESULT_ERR" and want[0] == "REJECTED" and host_obs[1] == want[1] and not host_obs[2]:
                row["status"], row["deviation"] = "MATCH", "ERR_RECEIPT"
                errs += 1
                err_keys.add(k)
            elif k in err_keys:
                # Ключ занят квитанцией Err (HST-06), модель его не резервировала. Дальше состояние может разойтись
                # (модель зафиксирует то, что хост отверг), поэтому состояние больше не сравнивается, а исходы
                # шагов на других ключах — сравниваются.
                row["status"], row["deviation"] = "DEVIATION", "ERR_RESERVES_KEY"
                rows.append(row)
                verdict = "DEVIATION" if verdict == "MATCH" else verdict
                state_diverged = True
                continue
            else:
                row["status"] = "DIVERGENCE"
                rows.append(row)
                verdict = "DIVERGENCE"
                break
            if state_diverged:
                row["state_compared"] = False
                rows.append(row)
                continue
            hv, mv = host.view(), model_view(mstate)
            diffs = [f for f in ("articles", "projections", "index", "events") if hv[f] != mv[f]]
            if hv["state_version"] != mstate.state_version + base + errs - acks:
                diffs.append(f"state_version {hv['state_version']} ≠ {mstate.state_version} + {base + errs - acks}")
            if diffs:
                row["status"], row["state_diff"] = "DIVERGENCE", diffs
                rows.append(row)
                verdict = "DIVERGENCE"
                break
            rows.append(row)
    finally:
        host.close()
    return {"id": seq_def["id"], "verdict": verdict, "steps": rows,
            "compared": sum(1 for r in rows if r["status"] == "MATCH"),
            "not_applicable": sum(1 for r in rows if r["status"] == "NOT_APPLICABLE"),
            "deviations": sorted({r["deviation"] for r in rows if "deviation" in r}),
            "deviation_steps": sum(1 for r in rows if r["status"] == "DEVIATION"),
            "state_not_compared": sum(1 for r in rows if r.get("state_compared") is False),
            "not_run": len(seq_def["steps"]) - len(rows),
            "total_steps": len(seq_def["steps"])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="подробный отчёт по шагам")
    a = ap.parse_args()
    E = load_engine()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    files = [(f.relative_to(APP).as_posix(), f.read_bytes()) for f in sorted(APP.rglob("*.bag"))]
    project, prog, pre = prepare(files)
    if pre is not None:
        print(json.dumps(pre, ensure_ascii=False))
        return 2
    program = D.Program(project, prog)
    results = [run_sequence(E, fixture, sq, program) for sq in fixture["manual_sequences"]]
    summary = {
        "sequences": len(results),
        "MATCH": sum(r["verdict"] == "MATCH" for r in results),
        "DEVIATION": sum(r["verdict"] == "DEVIATION" for r in results),
        "DIVERGENCE": sum(r["verdict"] == "DIVERGENCE" for r in results),
        "steps_compared": sum(r["compared"] for r in results),
        "steps_not_applicable": sum(r["not_applicable"] for r in results),
        "steps_deviation": sum(r["deviation_steps"] for r in results),
        "steps_state_not_compared": sum(r["state_not_compared"] for r in results),
        "steps_not_run": sum(r["not_run"] for r in results),
        "steps_total": sum(r["total_steps"] for r in results),
        "by_sequence": {r["id"]: r["verdict"] + (f" ({', '.join(r['deviations'])})" if r["deviations"] else "")
                        for r in results},
    }
    print(json.dumps({"summary": summary, "sequences": results} if a.json else summary, ensure_ascii=False, indent=2))
    return 1 if summary["DIVERGENCE"] else 0


if __name__ == "__main__":
    sys.exit(main())
