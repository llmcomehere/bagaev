"""WorkState CHANGE-1 (spec/protocol/agent-protocol.md §6; 04-agent-tooling §4, §6; R16 §11).

Хранятся только входы работы: база, кандидат, контракт, журнал правок, ID свидетельств. Всё производное —
проверка кандидата, граф, влияние, статусы обязательств и условий, готовность к приёмке — пересчитывается
чистой функцией при каждом чтении. Поэтому resume не меняет состояние работы и не зависит от сессии и модели
(T12-C04). Единственная запись при чтении — производный кэш графа D84, атомарный и проверяемый при чтении.
"""
from __future__ import annotations

from bagaev_ref.change import contract as K
from bagaev_ref.change import verify as V
from bagaev_ref.change.sourceedit import EditError
from bagaev_ref.change import lang as L
from bagaev_ref.links.extract import source_digest
from bagaev_ref.links.graph import Graph
from bagaev_ref.links.impact import impact
from bagaev_ref.kernel import canonical as C


def checked(files: dict, lang=None):
    """(контекст, None) или (None, диагностики) — проверка языка проекта (у bagaev — CHECK-1)."""
    return (lang or L.LANGS["bagaev"]).check(files)


_TOOLS_REV = None


def tools_rev() -> str:
    """Ревизия всего эталона: кэш графа хранит и итог проверки CHECK-1, а она зависит от разборщика и проверки,
    не только от извлекателя (D84). Другая ревизия кода — промах кэша."""
    global _TOOLS_REV
    if _TOOLS_REV is None:
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        _TOOLS_REV = C.digest("tools", "1", {f.relative_to(root).as_posix(): f.read_bytes().hex()
                                             for f in sorted(root.rglob("*.py"))})
    return _TOOLS_REV


def graph_of(store, sid: str, side: str):
    """Граф снимка из кэша `.bagaev/graph/<snapshot>/<extractor_rev>.json` (D84) или извлечённый заново.
    Запись в кэше — {tools, graph}; повреждённая, чужой ревизии кода или другого набора исходников — промах.
    Запись атомарна: временный файл и переименование, так что оборванная запись кэш не ломает."""
    import os
    lang = L.of(store)
    path = store.dir / "graph" / sid / f"{lang.extractor_rev}.json"
    files = store.files(sid)
    if path.is_file():
        try:
            entry = C.decode(path.read_bytes())
            if (entry.get("tools") == tools_rev() and isinstance(entry.get("graph"), dict)
                    and entry["graph"].get("source") == source_digest(sorted(files.items()))):
                return Graph(entry["graph"], side), files, None
        except Exception:                               # кэш производный: любой сбой чтения — пересчёт
            pass
    ctx, diags = checked(files, lang)
    if diags is not None:
        return None, files, diags
    data = lang.extract(files, ctx)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(C.encode({"tools": tools_rev(), "graph": data}))
    os.replace(tmp, path)
    return Graph(data, side), files, None


def load_policy(store) -> dict:
    """Политика проекта поверх политики по умолчанию (CHG-10). Неверная форма — отказ POLICY_INVALID."""
    p = store.dir / "policy.json"
    if not p.is_file():
        return K.DEFAULT_POLICY
    import json
    try:
        pol = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise EditError("POLICY_INVALID", detail="policy.json — не JSON")
    lists = lambda d: isinstance(d, dict) and all(isinstance(k, str) and isinstance(v, list)
                                                  and all(isinstance(x, str) for x in v) for k, v in d.items())
    if (not isinstance(pol, dict) or set(pol) - {"format", "obligations", "principals"}
            or not lists(pol.get("obligations", {})) or not (pol.get("principals") is None or lists(pol["principals"]))):
        raise EditError("POLICY_INVALID", detail="policy.json: obligations и principals — {строка: [строки]}")
    rest = {k: v for k, v in pol.items() if k != "obligations"}
    return dict(K.DEFAULT_POLICY, **rest, obligations=dict(K.DEFAULT_POLICY["obligations"], **pol.get("obligations", {})))


def work_row(store, change_id: str):
    r = store.db.execute("SELECT base, candidate, work_revision, contract, contract_revision, status, intent, evidence, "
                         "edits, lineage FROM works WHERE change_id = ?", (change_id,)).fetchone()
    if r is None:
        return None
    keys = ("base", "candidate", "work_revision", "contract", "contract_revision", "status", "intent", "evidence",
            "edits", "lineage")
    w = dict(zip(keys, r))
    for k in ("evidence", "edits", "lineage"):
        w[k] = C.decode(w[k].encode())
    return w


def history_ids(store) -> set:
    """Все EntityId принятых снимков: ID нельзя использовать повторно после удаления (01 §7A)."""
    out = set()
    lang = L.of(store)
    for sid in store.accepted_snapshots():
        ents, _ = lang.entities(store.files(sid))
        out |= set(ents or {})
    return out


def view(store, change_id: str, budget: int | None = None, context_budget: int | None = None, cursor: int = 0) -> dict:
    w = work_row(store, change_id)
    if w is None:
        return {"code": "UNKNOWN_CHANGE", "data": {"change_id": change_id}}
    contract = store.get_json(w["contract"])
    policy = load_policy(store)
    evidence = [C.decode(bytes(store.db.execute("SELECT record FROM evidence WHERE id = ?", (e,)).fetchone()[0]))
                for e in w["evidence"]]
    head = store.meta("head")
    out = {"change_id": change_id, "intent": w["intent"], "status": w["status"], "base": w["base"],
           "candidate": w["candidate"], "head": head, "needs_rebase": head != w["base"],
           "work_revision": w["work_revision"], "contract_revision": int(contract["revision"]),
           "contract": contract, "policy": K.policy_ref(policy), "lineage": w["lineage"],
           "evidence": [e["id"] for e in evidence]}
    base_g, base_files, bdiag = graph_of(store, w["base"], "base")
    cand_g, cand_files, cdiag = graph_of(store, w["candidate"], "candidate")
    blockers = []
    if w["status"] != "open":
        blockers.append({"kind": "WORK_NOT_OPEN", "status": w["status"]})
    if contract.get("policy") != out["policy"]:
        blockers.append({"kind": "POLICY_CHANGED", "pinned": contract.get("policy"), "current": out["policy"]})
    if head != w["base"]:
        blockers.append({"kind": "NEEDS_REBASE", "head": head})
    if cdiag is not None:
        out["diagnostics"] = cdiag
        blockers.append({"kind": "CANDIDATE_INVALID", "diagnostics": len(cdiag)})
        out.update(obligations=[], clauses=[], impact=None, blockers=blockers, ready_for_acceptance=False)
        return out
    latest = V.latest_by_test(evidence)
    assessed = {name: V.assess(ev, cand_g, w["candidate"]) for name, ev in sorted(latest.items())}
    applicable = {name: a["verdict"] for name, a in assessed.items()
                  if a["integrity"] == "valid" and a["applicability"] == "applicable"}
    rep = impact(base_g, cand_g, budget, (), applicable)
    obligations = []
    for pair in rep["obligations"]:
        st = V.obligation_status(pair, base_g, cand_g, w["candidate"], evidence, contract, policy, w["lineage"])
        obligations.append({"obligation": [pair["kind"], pair["target"], pair["source"]],
                            "names": [pair["target_name"], pair["source_name"]], "sides": pair["sides"], **st})
    clauses = [dict(id=c["id"], claim=c["claim"], stage=c["stage"], **V.clause_status(c, cand_g, w["candidate"], evidence))
               for c in contract["clauses"]]
    if rep["status"] != "COMPLETE":
        blockers.append({"kind": "ANALYSIS_INCOMPLETE", "frontier": [f["id"] for f in rep["frontier"]],
                         **({"coverage": rep["coverage_gaps"]} if rep["coverage_gaps"] else {})})
    ob_kind = {"open": "OBLIGATION_OPEN", "unknown": "OBLIGATION_UNKNOWN", "contradicted": "OBLIGATION_CONTRADICTED"}
    for o in obligations:
        if o["status"] in ob_kind:
            blockers.append({"kind": ob_kind[o["status"]], "obligation": o["obligation"], "names": o["names"]})
    cl_kind = {"open": "CLAUSE_OPEN", "contradicted": "CLAUSE_CONTRADICTED"}
    for c in clauses:
        if c["stage"] == "program_acceptance" and c["status"] != "supported":
            blockers.append({"kind": cl_kind[c["status"]], "clause": c["id"]})
    # применимый FAIL любого теста — противоречие (A05 шаг 2, CHG-12), даже если тест не связан с правилом
    for name, verdict in sorted(applicable.items()):
        if verdict in ("FAIL", "ERROR"):
            blockers.append({"kind": "EVIDENCE_CONTRADICTED", "test": name, "verdict": verdict})
    cand_tests = {n["name"] for n in cand_g.nodes.values() if n["kind"] == "test"}
    not_run = [t for t in rep["tests_to_run"] if t in cand_tests and applicable.get(t) not in ("PASS", "FAIL", "ERROR")]
    runner = V.pending_runner_verification(base_files, cand_files, evidence, L.of(store), w["candidate"])
    if runner is not None:
        not_run.append(runner)
        rep["tests_to_run"] = sorted(set(rep["tests_to_run"]) | {runner})
    if not_run:
        blockers.append({"kind": "TESTS_NOT_RUN", "tests": sorted(not_run)})
    changed = sorted({s["id"] for s in rep["seeds"]})
    if contract["allowed"] is not None:
        # сущность в области, если её ID в списке или все её имена — в базе и в кандидате: переименование
        # чужой сущности в разрешённое имя область не обходит
        def inside(i):
            return i in contract["allowed"] or all(g.nodes[i]["name"] in contract["allowed"]
                                                   for g in (base_g, cand_g) if i in g.nodes)
        outside = sorted(i for i in changed if not inside(i))
        if outside:
            blockers.append({"kind": "SCOPE_EXCEEDED", "entities": outside})
    hist = history_ids(store)
    for e in cand_g.data["edges"]:
        if e["kind"] == "supersedes" and (e["dst"] not in hist or e["dst"] in cand_g.nodes):
            blockers.append({"kind": "SUPERSEDES_UNKNOWN", "entity": e["src"], "target": e["dst"]})
    out.update(impact={"status": rep["status"], "readiness": rep["readiness"], "seeds": rep["seeds"],
                       "in_scope": [x["id"] for x in rep["in_scope"]], "unknown": rep["unknown"],
                       "frontier": rep["frontier"], "tests_to_run": rep["tests_to_run"], "gaps": rep["gaps"],
                       "coverage_gaps": rep["coverage_gaps"]},
               assessments=[assessed[n] for n in sorted(assessed)],
               obligations=obligations, clauses=clauses, changed=changed, blockers=blockers,
               ready_for_acceptance=not blockers)
    if context_budget is not None:
        from bagaev_ref.links.context import context_pack
        out["context"] = context_pack(rep, base_g, cand_g, base_files, cand_files, context_budget, cursor)
    out["_graphs"] = (base_g, cand_g, rep)
    return out
