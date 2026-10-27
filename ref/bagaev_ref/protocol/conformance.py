"""Случаи conformance фаз edit, accept, protocol (conformance/README.md §Изменение).

`run.change`: `principal`, `policy` (необязательно — `.bagaev/policy.json`) и `steps` — запросы протокола.
Проект — копия файлов корня случая; перед шагами `bag project init`. В запросах `"$change"` заменяется ID
работы из первого `change_begin`, `"$sha:<путь>"` — sha256 текущего файла кандидата, `"$head"` — head.
Шаг `{"op": "head_files", "changes": {...}}` — правка head вне работы (чужая приёмка с записью приёмки) для
STALE_BASE; шаг `{"op": "policy", "policy": {...}}` — смена `.bagaev/policy.json` посреди работы.
Наблюдение — проекция ответов (spec/protocol/agent-protocol.md §11): дайджесты заменены на `<digest>`.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

DIGEST = re.compile(r"^[0-9a-f]{64}$")
CHANGE = re.compile(r"^ch-[0-9a-f]{16}$")


def scrub(x):
    """Дайджесты и ID работ — производные байтов реализации: в наблюдении метки."""
    if isinstance(x, str):
        return "<digest>" if DIGEST.match(x) else "<change>" if CHANGE.match(x) else x
    if isinstance(x, list):
        return [scrub(v) for v in x]
    if isinstance(x, dict):
        return {k: scrub(v) for k, v in x.items()}
    return x


def mentioned(eid: str, text: str) -> bool:
    """ID назван в тексте запросов как отдельное слово (а не часть дайджеста)."""
    return re.search(rf"(?<![0-9a-z]){re.escape(eid)}(?![0-9a-z])", text) is not None


def project(op: str, r: dict, req: dict | None = None, seen: str = "") -> dict:
    """Проекция ответа. `seen` — текст всех запросов случая до этого: ID, которых в нём нет, назначил инструмент."""
    out = {"status": r["status"], "replayed": r["replayed"]}
    if "work_revision" in r:
        out["work_revision"] = r["work_revision"]
    if "error" in r:
        out["code"] = r["error"]["code"]
        data = {k: v for k, v in r["error"]["data"].items() if k not in ("detail", "diagnostics", "expected", "actual",
                                                                          "head", "principal")}
        if r["error"]["code"] == "OPEN_OBLIGATIONS":
            data = {"blockers": sorted({b["kind"] for b in r["error"]["data"]["blockers"]})}
        if data:
            out["data"] = scrub(data)
        return out
    res = r["result"]
    if op == "apply":
        ident = dict(res["identity"])
        if (req or {}).get("arguments", {}).get("source_edit", {}).get("assign_ids"):
            text = seen + json.dumps(req, ensure_ascii=False)   # назначенные ID случайны по семени: только их число
            ident["added"] = sorted(i if mentioned(i, text) else "<assigned>" for i in ident["added"])
        out.update(touched=res["touched"], identity=ident, draft=res["draft"],
                   diagnostics=sorted({d["code"] for d in res["diagnostics"]}))
    elif op == "verify":
        out["evidence"] = sorted([e["test"], e["verdict"]] for e in res["evidence"])
    elif op == "work_resume":
        out.update(needs_rebase=res["needs_rebase"], ready_for_acceptance=res["ready_for_acceptance"],
                   contract_revision=res["contract_revision"], status_=res["status"],
                   blockers=sorted(b["kind"] for b in res["blockers"]),
                   obligations=sorted([*o["names"], o["obligation"][0], o["status"], o["basis"]]
                                      for o in res.get("obligations", []) if o["status"] != "excluded_with_basis"),
                   clauses=sorted([c["id"], c["status"], c["basis"]] for c in res.get("clauses", [])))
    elif op == "accept":
        # каждое закрытое обязательство с основанием, а не только множество видов: ослабление видно в записи
        out["obligations"] = sorted([o[0], o[1], o[2], o[3], o[4]] for o in res["obligations"]
                                    if o[3] != "excluded_with_basis")
        out["replaced_clauses"] = res["replaced_clauses"]
        out["replaced_tests"] = res["replaced_tests"]
        out["coverage_gaps"] = res["coverage_gaps"]
        out["lineage"] = [[x["op"], x["predecessors"], x["successors"]] for x in res["lineage"]]
    elif op == "contract_update":
        c = res["contract"]
        out.update(contract_revision=res["contract_revision"], clauses=[x["id"] for x in c["clauses"]],
                   replaced=[[x["id"], x["new"] is not None] for x in c["replaced"]],
                   assumptions=[a["obligation"] for a in c["assumptions"]], allowed=c["allowed"],
                   replaced_tests=[t["test"] for t in c["replaced_tests"]], policy_pins=[x["reason"] for x in c["policy_pins"]])
    elif op == "rebase":
        ident = dict(res["identity"])
        ident["added"] = sorted(i if mentioned(i, seen) else "<assigned>" for i in ident["added"])   # ID из assign_ids
        out["identity"] = ident
    elif op == "search":
        out.update(candidates=[[c["name"], c["score"], sorted(b["kind"] for b in c["basis"])] for c in res["candidates"][:5]],
                   ambiguous=res["ambiguous"], selection=res["selection"])
    return out


def subst(x, env, change=None):
    """$change, $change2, … — ID работ по порядку change_begin; $sha:<путь> — sha256 файла кандидата работы запроса."""
    if isinstance(x, str):
        if x.startswith("$change"):
            n = int(x[7:] or "1")
            return env["changes"][n - 1] if len(env["changes"]) >= n else x
        if x == "$head":
            return env["head"]()
        if x.startswith("$sha:"):
            return hashlib.sha256(env["file"](change, x[5:])).hexdigest()
        return x
    if isinstance(x, list):
        return [subst(v, env, change) for v in x]
    if isinstance(x, dict):
        return {k: subst(v, env, change) for k, v in x.items()}
    return x


def run_change_case(files, case: dict) -> dict:
    from bagaev_ref.change import workstate as W
    from bagaev_ref.protocol.ops import PROTOCOL, Ops, init_project
    spec = case["run"]["change"]
    phase = case["expect"]["phase"]
    tmp = Path(tempfile.mkdtemp(prefix="bag-change-"))
    try:
        root = tmp / "p"
        for rel, data in files:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_bytes(data)
        init_project(root, spec.get("principal", "agent"))
        if spec.get("policy") is not None:
            (root / ".bagaev" / "policy.json").write_text(json.dumps(spec["policy"]), encoding="utf-8")
        ops = {}

        def ops_for(p):
            if p not in ops:
                ops[p] = Ops(root, p)
            return ops[p]
        main = ops_for(spec.get("principal", "agent"))
        env = {"changes": [], "head": lambda: main.store.meta("head")}

        def cur_file(change, path):
            w = W.work_row(main.store, change)
            return main.store.files(w["candidate"])[path]
        env["file"] = cur_file
        out, seen = [], ""
        for step in spec["steps"]:
            if step.get("op") == "head_files":           # чужая приёмка: новый head вне этой работы
                from bagaev_ref.kernel import canonical as C
                st = main.store
                fs = st.files(st.meta("head"))
                fs.update({k: v.encode() for k, v in step["changes"].items()})
                st.db.execute("BEGIN IMMEDIATE")
                sid = st.snapshot(fs, [st.meta("head")])
                rev = int(st.meta("head_revision")) + 1
                rec = {"format": "bagaev-acceptance/1", "kind": "external", "base": st.meta("head"), "candidate": sid,
                       "head_revision": str(rev)}               # инвариант CHG-16: у каждого head есть запись приёмки
                st.db.execute("INSERT INTO acceptance VALUES (?, ?, ?)", (C.digest("acceptance", "1", rec), C.encode(rec), rev))
                st.db.execute("UPDATE snapshots SET accepted = 1 WHERE id = ?", (sid,))
                st.set_meta("head", sid)
                st.set_meta("head_revision", rev)
                st.db.execute("COMMIT")
                out.append({"status": "head_moved"})
                continue
            if step.get("op") == "policy":               # политика проекта сменилась вне работы
                (root / ".bagaev" / "policy.json").write_text(json.dumps(step["policy"]), encoding="utf-8")
                out.append({"status": "policy_changed"})
                continue
            ch = subst(step["request"].get("change_id"), env)
            req = dict(subst(step["request"], env, ch), protocol=PROTOCOL)
            r = ops_for(step.get("principal", spec.get("principal", "agent"))).call(req)
            if r.get("operation") == "change_begin" and r["status"] == "succeeded" and r["change_id"] not in env["changes"]:
                env["changes"].append(r["change_id"])
            out.append(project(req.get("operation"), r, req, seen))
            seen += json.dumps(req, ensure_ascii=False)
        head_rev = int(main.store.meta("head_revision"))
        for o in ops.values():
            o.close()
        return {"phase": phase, "outcome": "COMPLETED", "value": out, "state": {"head_revision": head_rev}}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
