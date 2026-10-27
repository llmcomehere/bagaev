"""Операции протокола агента PROTO-1 (spec/protocol/agent-protocol.md §7; 04-agent-tooling §2–§7, D86, R16 §7).

Один слой операций для двух транспортов: CLI `bag op` и MCP stdio. Субъект (principal) задаёт транспорт,
полем запроса его назначить нельзя. Запись (CHG-15): форма → дайджест → в транзакции поиск квитанции →
полномочие → guards работы → операция → атомарно состояние, журнал и квитанция. Отказ на полномочии или guard
ключ не резервирует. Любое иное исключение — ответ `failed` с кодом INTERNAL, транспорт продолжает работу.
"""
from __future__ import annotations

import json
from pathlib import Path

from bagaev_ref.change import contract as K
from bagaev_ref.change import identity as I
from bagaev_ref.change import verify as V
from bagaev_ref.change import workstate as W
from bagaev_ref.change.sourceedit import EditError, apply_source_edit
from bagaev_ref.change.store import ProjectStore, crash_point
from bagaev_ref.kernel import canonical as C

PROTOCOL = "bagaev-protocol/1"
KEY_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")
READ = {"inspect", "search", "relations", "impact", "context", "why", "check", "run_tests", "work_resume"}
WRITE = {"change_begin", "contract_update", "apply", "verify", "rebase", "accept", "abandon"}
RETRY = {"REQUEST_INVALID": "fix_request", "UNKNOWN_OPERATION": "fix_request", "UNKNOWN_CHANGE": "fix_request",
         "UNKNOWN_ENTITY": "fix_request", "IDEMPOTENCY_CONFLICT": "new_key", "ACCESS_DENIED": "new_decision",
         "WORK_CONFLICT": "new_decision", "STALE_BASE": "new_decision", "OPEN_OBLIGATIONS": "new_decision",
         "PROJECT_NOT_INITIALIZED": "new_decision", "POLICY_INVALID": "new_decision", "INTERNAL": "new_decision"}


class OpError(Exception):
    def __init__(self, code: str, status: str = "blocked", **data):
        super().__init__(code)
        self.code, self.status, self.data = code, status, data


def response(op, status, replayed=False, change_id=None, work_revision=None, result=None, error=None) -> dict:
    r = {"protocol": PROTOCOL, "operation": op, "status": status, "replayed": replayed}
    if change_id is not None:
        r["change_id"] = change_id
    if work_revision is not None:
        r["work_revision"] = work_revision
    if error is not None:
        r["error"] = dict(error, retry=RETRY.get(error["code"], "new_decision"))
    else:
        r["result"] = result
    return r


def _scalar_text(x: str) -> str:
    try:
        x.encode("utf-8")
    except UnicodeEncodeError:
        raise OpError("REQUEST_INVALID", "failed", detail="строка с одиночным суррогатом не представима в UTF-8")
    return x


def strip_numbers(x):
    """Аргументы для дайджеста и журнала: целое n — `{"$int": "n"}` (BAG-CJSON-1 без чисел, CANON-02). Ключи
    объектов, начинающиеся с `$`, удваивают его — запись однозначна: `5` и `{"$int": "5"}` дают разные дайджесты."""
    if isinstance(x, bool) or x is None:
        return x
    if isinstance(x, str):
        return _scalar_text(x)
    if isinstance(x, int):
        return {"$int": str(x)}
    if isinstance(x, list):
        return [strip_numbers(v) for v in x]
    if isinstance(x, dict):
        return {("$" + _scalar_text(k) if k.startswith("$") else _scalar_text(k)): strip_numbers(v) for k, v in x.items()}
    raise OpError("REQUEST_INVALID", "failed", detail=f"значение {type(x).__name__} недопустимо")


def unstrip(x):
    """Обратное к strip_numbers."""
    if isinstance(x, list):
        return [unstrip(v) for v in x]
    if isinstance(x, dict):
        if set(x) == {"$int"} and isinstance(x["$int"], str):
            return int(x["$int"])
        return {(k[1:] if k.startswith("$") else k): unstrip(v) for k, v in x.items()}
    return x


def allowed(policy: dict, principal: str, op: str) -> bool:
    """Полномочия проекта (CHG-14): principal → операции; без раздела principals разрешено всё."""
    ps = policy.get("principals")
    if ps is None:
        return True
    grants = ps.get(principal, [])
    return "*" in grants or op in grants or (op in READ and "read" in grants)


class Ops:
    def __init__(self, root: Path, principal: str):
        self.root, self.principal = Path(root), principal
        self.store = ProjectStore(self.root)

    def close(self):
        self.store.close()

    # ------------------------------------------------------------ вход
    def call(self, req) -> dict:
        op = req.get("operation") if isinstance(req, dict) else None
        op = op if isinstance(op, str) else None
        ch = req.get("change_id") if isinstance(req, dict) and isinstance(req.get("change_id"), str) else None
        try:
            self.validate(req)
            if op in READ:
                return self.read(req)
            return self.write(req)
        except OpError as e:
            return response(op, e.status, error={"code": e.code, "data": e.data}, change_id=ch)
        except EditError as e:
            return response(op, "blocked" if e.code not in ("REQUEST_INVALID", "POLICY_INVALID") else "failed",
                            error={"code": e.code, "data": e.data}, change_id=ch)
        except Exception as e:                           # дефект реализации: отказ, а не падение транспорта
            if self.store.db.in_transaction:
                self.store.db.execute("ROLLBACK")
            return response(op, "failed", error={"code": "INTERNAL", "data": {"detail": type(e).__name__}},
                            change_id=ch)

    def validate(self, req):
        if not isinstance(req, dict):
            raise OpError("REQUEST_INVALID", "failed", detail="запрос — объект")
        extra = set(req) - {"protocol", "operation", "change_id", "expected_work_revision", "idempotency_key", "arguments"}
        if extra:
            raise OpError("REQUEST_INVALID", "failed", detail=f"неизвестные поля {sorted(extra)}")
        if req.get("protocol") != PROTOCOL:
            raise OpError("REQUEST_INVALID", "failed", detail=f"protocol — {PROTOCOL}")
        op = req.get("operation")
        if op not in READ | WRITE:
            raise OpError("UNKNOWN_OPERATION", "failed", operation=op)
        if not isinstance(req.get("arguments", {}), dict):
            raise OpError("REQUEST_INVALID", "failed", detail="arguments — объект")
        needs_change = op not in ("change_begin", "search", "inspect")
        if needs_change and not isinstance(req.get("change_id"), str):
            raise OpError("REQUEST_INVALID", "failed", detail="нужен change_id")
        if op in WRITE:
            key = req.get("idempotency_key")
            if not (isinstance(key, str) and 16 <= len(key) <= 128 and set(key) <= KEY_CHARS):
                raise OpError("REQUEST_INVALID", "failed", detail="idempotency_key — 16…128 [A-Za-z0-9_-] (CANON-10)")
            if op != "change_begin":
                ewr = req.get("expected_work_revision")
                if not (isinstance(ewr, int) and not isinstance(ewr, bool) and ewr >= 1):
                    raise OpError("REQUEST_INVALID", "failed", detail="нужен expected_work_revision ≥ 1")

    def policy(self):
        return W.load_policy(self.store)

    @property
    def lang(self):
        from bagaev_ref.change import lang as L
        return L.of(self.store)

    @staticmethod
    def count(a: dict, name: str, default=None):
        v = a.get(name, default)
        if v is not None and not (isinstance(v, int) and not isinstance(v, bool) and v >= 0):
            raise OpError("REQUEST_INVALID", "failed", detail=f"{name} — целое ≥ 0")
        return v

    # ------------------------------------------------------------ чтение
    ARG_TYPES = {"query": str, "entity": str, "snapshot": str, "direction": str, "affected": bool}

    def read(self, req) -> dict:
        op, a, ch = req["operation"], req.get("arguments", {}), req.get("change_id")
        for name, t in self.ARG_TYPES.items():
            if name in a and not isinstance(a[name], t):
                raise OpError("REQUEST_INVALID", "failed", detail=f"{name} — {t.__name__}")
        if a.get("direction", "both") not in ("in", "out", "both"):
            raise OpError("REQUEST_INVALID", "failed", detail="direction — in, out или both")
        budgets = (self.count(a, "analysis_budget"), self.count(a, "budget") if op in ("context", "work_resume") else None,
                   self.count(a, "cursor", 0))
        if not allowed(self.policy(), self.principal, op):
            raise OpError("ACCESS_DENIED", operation=op, principal=self.principal)
        if op == "search":
            from bagaev_ref.protocol.search import search
            sid = self.store.meta("head")
            if not sid:
                raise OpError("PROJECT_NOT_INITIALIZED")
            return response(op, "succeeded", result=search(self.store, sid, a.get("query", "")))
        if op == "inspect":
            sid = a.get("snapshot") or self.store.meta("head")
            if ch is not None:
                w = W.work_row(self.store, ch)
                if w is None:
                    raise OpError("UNKNOWN_CHANGE", "failed", change_id=ch)
                sid = w["candidate"]
            if self.store.db.execute("SELECT 1 FROM snapshots WHERE id = ?", (sid,)).fetchone() is None:
                raise OpError("REQUEST_INVALID", "failed", detail="снимка нет в хранилище")
            g, files, diags = W.graph_of(self.store, sid, "candidate")
            if g is None:
                return response(op, "succeeded", result={"snapshot": sid, "diagnostics": diags})
            from bagaev_ref.links.graph import relations, resolve
            eid = resolve(g, a.get("entity", ""))
            if eid is None:
                raise OpError("UNKNOWN_ENTITY", "failed", entity=a.get("entity"))
            n = g.nodes[eid]
            s, e = int(n["span"][0]), int(n["span"][1])
            return response(op, "succeeded", result={"snapshot": sid, "entity": n, "text": files[n["file"]][s:e].decode(),
                                                      "relations": relations(g, eid)})
        w = W.work_row(self.store, ch)
        if w is None:
            raise OpError("UNKNOWN_CHANGE", "failed", change_id=ch)
        if op == "check":
            _, diags = W.checked(self.store.files(w["candidate"]), self.lang)
            return response(op, "succeeded", change_id=ch, work_revision=w["work_revision"],
                            result={"candidate": w["candidate"], "diagnostics": diags or []})
        if op == "run_tests":
            return response(op, "succeeded", change_id=ch, work_revision=w["work_revision"],
                            result=self.lang.run_tests(self.store.files(w["candidate"])))
        v = W.view(self.store, ch, *budgets)
        graphs = v.pop("_graphs", None)
        if op == "work_resume":
            return response(op, "succeeded", change_id=ch, work_revision=w["work_revision"], result=v)
        if graphs is None:
            raise OpError("OPEN_OBLIGATIONS", blockers=v["blockers"])
        base_g, cand_g, rep = graphs
        if op == "impact":
            return response(op, "succeeded", change_id=ch, work_revision=w["work_revision"], result=rep)
        if op == "context":
            return response(op, "succeeded", change_id=ch, work_revision=w["work_revision"], result=v["context"])
        if op == "relations":
            from bagaev_ref.links.graph import relations, resolve
            eid = resolve(cand_g, a.get("entity", "")) or resolve(base_g, a.get("entity", ""))
            if eid is None:
                raise OpError("UNKNOWN_ENTITY", "failed", entity=a.get("entity"))
            g = cand_g if eid in cand_g.nodes else base_g
            return response(op, "succeeded", change_id=ch, work_revision=w["work_revision"],
                            result=relations(g, eid, a.get("direction", "both")))
        if op == "why":
            from bagaev_ref.links.graph import resolve
            from bagaev_ref.links.impact import why_affected, why_not
            eid = resolve(cand_g, a.get("entity", "")) or resolve(base_g, a.get("entity", ""))
            if eid is None:
                raise OpError("UNKNOWN_ENTITY", "failed", entity=a.get("entity"))
            out = why_affected(rep, eid) if a.get("affected", True) else why_not(rep, eid)
            return response(op, "succeeded", change_id=ch, work_revision=w["work_revision"], result=out)
        raise AssertionError(op)

    # ------------------------------------------------------------ запись
    def write(self, req) -> dict:
        op, a, key = req["operation"], req.get("arguments", {}), req["idempotency_key"]
        ch = req.get("change_id")
        namespace = ch if op != "change_begin" else "project"
        digest = C.digest("project-op", "1", {"operation": op, "change_id": ch,
                                               "expected_work_revision": str(req.get("expected_work_revision")),
                                               "arguments": strip_numbers(a)})
        db = self.store.db
        db.execute("BEGIN IMMEDIATE")
        try:
            r = db.execute("SELECT digest, response FROM receipts WHERE principal = ? AND namespace = ? AND key = ?",
                           (self.principal, namespace, key)).fetchone()
            if r is not None:                            # квитанция ищется до guard'ов (R16 §7)
                db.execute("ROLLBACK")
                if r[0] != digest:
                    raise OpError("IDEMPOTENCY_CONFLICT", key=key, namespace=namespace)
                return dict(json.loads(bytes(r[1]).decode()), replayed=True)
            if not allowed(self.policy(), self.principal, op):
                raise OpError("ACCESS_DENIED", operation=op, principal=self.principal)
            if op == "change_begin":
                res, ch2, wr = self.begin(a, key)
            else:
                w = W.work_row(self.store, ch)
                if w is None:
                    raise OpError("UNKNOWN_CHANGE", "failed", change_id=ch)
                if w["work_revision"] != req["expected_work_revision"]:
                    raise OpError("WORK_CONFLICT", expected=req["expected_work_revision"], actual=w["work_revision"])
                if w["status"] != "open":
                    raise OpError("WORK_CONFLICT", work_status=w["status"], detail="работа закрыта")
                res, wr = getattr(self, "op_" + op)(ch, w, a)
                ch2 = ch
            resp = response(op, "succeeded", change_id=ch2, work_revision=wr, result=res)
            db.execute("INSERT INTO receipts VALUES (?, ?, ?, ?, ?, ?)",
                       (self.principal, namespace, key, digest, op, json.dumps(resp, ensure_ascii=False, sort_keys=True).encode()))
            self.store.journal(op, ch2, {"principal": self.principal, "key": key, "digest": digest})
            crash_point(f"{op}_before_commit")
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        crash_point(f"{op}_after_commit")
        return resp

    def save_work(self, ch, **fields):
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = [C.encode(v).decode() if isinstance(v, list) else v for v in fields.values()]
        self.store.db.execute(f"UPDATE works SET {cols} WHERE change_id = ?", (*vals, ch))

    def begin(self, a, key):
        intent = a.get("intent")
        if not isinstance(intent, str) or not intent:
            raise OpError("REQUEST_INVALID", "failed", detail="intent — текст намерения")
        head = self.store.meta("head")
        if not head:
            raise OpError("PROJECT_NOT_INITIALIZED")
        ch = "ch-" + C.digest("change-id", "1", {"principal": self.principal, "key": key})[:16]
        contract = K.initial(ch, intent, head, K.policy_ref(self.policy()))
        self.store.db.execute("INSERT INTO works VALUES (?, ?, ?, 1, ?, 1, 'open', ?, '[]', '[]', '[]')",
                              (ch, head, head, self.store.put_json(contract), intent))
        return {"change_id": ch, "base": head, "candidate": head, "contract_revision": 1}, ch, 1

    def op_contract_update(self, ch, w, a):
        c = K.update(self.store.get_json(w["contract"]), a.get("ops"), K.policy_ref(self.policy()))
        self.save_work(ch, contract=self.store.put_json(c), contract_revision=int(c["revision"]),
                       work_revision=w["work_revision"] + 1)
        return {"contract_revision": int(c["revision"]), "contract": c}, w["work_revision"] + 1

    def op_apply(self, ch, w, a):
        edit = a.get("source_edit")
        if isinstance(edit, dict):
            I.check_form(edit.get("identity_ops", []))   # форма — до базы (CHG-04 шаг 1)
        cand = self.store.files(w["candidate"])
        new, touched = apply_source_edit(cand, edit, self.lang.exts)
        hist = W.history_ids(self.store)
        assigned = {}
        if edit.get("assign_ids") and not self.lang.assigns_ids:
            raise OpError("REQUEST_INVALID", "failed", detail=f"assign_ids: у языка {self.lang.name} нет @id")
        if edit.get("assign_ids"):
            ents_new, diags = self.lang.entities(new)
            if ents_new is None:
                raise OpError("CANDIDATE_UNPARSABLE", diagnostics=diags)
            new, assigned = I.fill_ids(new, set(touched) & set(new), f"{ch}:{w['work_revision']}", set(ents_new) | hist)
        before, _ = self.lang.entities(cand)
        after, diags = self.lang.entities(new)
        if after is None:
            raise OpError("CANDIDATE_UNPARSABLE", diagnostics=diags)
        ident = I.check_identity(before or {}, after, edit.get("identity_ops", []), hist)
        sid = self.store.snapshot(new, [w["candidate"]])
        _, cdiags = W.checked(new, self.lang)
        self.save_work(ch, candidate=sid, work_revision=w["work_revision"] + 1,
                       edits=w["edits"] + [self.store.put_json(strip_numbers({"source_edit": edit,
                                                                              "assigned_ids": assigned}))],
                       lineage=w["lineage"] + ident["lineage"])
        return {"candidate": sid, "touched": touched, "identity": ident, "diagnostics": cdiags or [],
                "draft": cdiags is not None}, w["work_revision"] + 1

    def op_verify(self, ch, w, a):
        g, files, diags = W.graph_of(self.store, w["candidate"], "candidate")
        if g is None:
            raise OpError("CANDIDATE_INVALID", diagnostics=len(diags))
        recs = V.run_evidence(files, g, w["candidate"], self.lang)
        for r in recs:
            self.store.db.execute("INSERT OR IGNORE INTO evidence VALUES (?, ?)", (r["id"], C.encode(r)))
        self.save_work(ch, evidence=w["evidence"] + [r["id"] for r in recs], work_revision=w["work_revision"] + 1)
        return {"evidence": [{"test": r["test"], "verdict": r["verdict"], "id": r["id"]} for r in recs]}, w["work_revision"] + 1

    def op_abandon(self, ch, w, a):
        if not isinstance(a.get("reason"), str) or not a["reason"]:
            raise OpError("REQUEST_INVALID", "failed", detail="reason обязателен")
        self.save_work(ch, status="abandoned", work_revision=w["work_revision"] + 1)
        return {"status": "abandoned"}, w["work_revision"] + 1

    def op_accept(self, ch, w, a):
        from bagaev_ref.change.accept import accept
        return accept(self, ch, w)

    def op_rebase(self, ch, w, a):
        from bagaev_ref.change.accept import rebase
        return rebase(self, ch, w)


def init_project(root: Path, principal: str) -> dict:
    """Начальный снимок рабочего дерева: первый принятый снимок и head (CHG-01). Не операция протокола."""
    from bagaev_ref.change import lang as L
    from bagaev_ref.change.sourceedit import valid_path
    st = ProjectStore(root)
    try:
        language = L.detect(Path(root))
        exts = L.LANGS[language].exts
        files = {}
        for f in sorted(Path(root).rglob("*")):          # скрытые каталоги (.git, .bagaev, node_modules) — не исходники
            rel = f.relative_to(root).as_posix()
            if valid_path(rel, exts) and f.is_file() and "node_modules" not in rel.split("/") \
                    and not rel.endswith("package-lock.json"):
                files[rel] = f.read_bytes()
        st.db.execute("BEGIN IMMEDIATE")
        if st.meta("head"):                              # внутри транзакции: два init не создадут два head
            head = st.meta("head")
            st.db.execute("ROLLBACK")
            return {"outcome": "REFUSED", "code": "PROJECT_EXISTS", "data": {"head": head}}
        sid = st.snapshot(files, [])
        rec = {"format": "bagaev-acceptance/1", "kind": "bootstrap", "candidate": sid, "principal": principal}
        rid = C.digest("acceptance", "1", rec)
        st.db.execute("INSERT INTO acceptance VALUES (?, ?, 1)", (rid, C.encode(rec)))
        st.db.execute("UPDATE snapshots SET accepted = 1 WHERE id = ?", (sid,))
        st.set_meta("head", sid)
        st.set_meta("head_revision", 1)
        st.set_meta("language", language)
        st.journal("init", sid, rec)
        st.db.execute("COMMIT")
        return {"outcome": "INITIALIZED", "head": sid, "files": len(files), "language": language}
    finally:
        st.close()
