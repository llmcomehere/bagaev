"""Свидетельства и их оценка CHANGE-1 (spec/protocol/agent-protocol.md §5; 03-change-algorithms A03, D13).

Свидетельство — неизменяемая запись прогона теста на снимке кандидата: тест, его ревизия, вердикт, снимок-субъект,
дайджест замыкания зависимостей теста в этом снимке, ревизия извлекателя. Оценка к обязательству:
- integrity — запись совпадает со своим ID;
- applicability — applicable, если субъект — текущий кандидат, или замыкание теста в текущем кандидате то же
  (основание переноса `same-closure`); иначе stale (T10-C03);
- sufficiency — тест — метод правила (method_tests): неизменённый тест базы, который проверяет правило, либо
  новый или изменённый тест, названный методом условия контракта;
- verdict — PASS/FAIL/ERROR или SKIP/TODO/NOT_RUN. supports = valid ∧ applicable ∧ sufficient ∧ PASS;
  applicable FAIL/ERROR — противоречие, неисполненный тест оставляет обязательство открытым.

Набор методов правила сохраняется целиком: тест базы, который изменён, удалён или перестал проверять правило,
держит обязательство открытым (`base-test-changed`), пока контракт не объявит это с причиной (`replace_test`).
Ослабленный тест обязательство не закрывает (T10-C02, K6).
"""
from __future__ import annotations

import hashlib

from bagaev_ref.kernel import canonical as C
from bagaev_ref.links import certs


def run_evidence(cand_files: dict, cand_graph, cand_sid: str, lang=None) -> list:
    """Прогнать тесты кандидата (у bagaev — хранилища в памяти, HST-18) и вернуть записи свидетельств."""
    from bagaev_ref.change import lang as L
    lang = lang or L.LANGS["bagaev"]
    obs = lang.run_tests(cand_files)
    by_name = {n["name"]: n for n in cand_graph.nodes.values() if n["kind"] == "test"}
    out = []

    def record(node, name, verdict, kind="test-run", **extra):
        rec = {"format": "bagaev-evidence/1", "kind": kind, "test": name, "test_id": node["id"],
               "test_rev": node["rev"], "subject": cand_sid, "verdict": verdict,
               "closure": certs.closure_premises(cand_graph, node["id"])["closure"],
               "closure_complete": not certs.incomplete_coverage(cand_graph),
               "extractor_rev": cand_graph.data["extractor_rev"], **extra}
        out.append(dict(rec, id=C.digest("evidence", "1", rec)))

    results = {t["test"]: t["status"] for t in obs.get("tests", [])}
    for name, node in sorted(by_name.items()):
        # Новый SKIP/TODO или отсутствие наблюдения должны вытеснить прежний PASS того же субъекта.
        record(node, name, results.get(name, "NOT_RUN"))
    for runner in obs.get("runners", []):
        node = next((n for n in cand_graph.nodes.values() if n["kind"] == "module" and n["file"] == runner["file"]), None)
        if node is not None:
            record(node, "runner:" + runner["file"], runner["status"], "test-runner", runner=runner)
    if getattr(lang, "runner_suite", None):
        inventory = runner_inventory(cand_files, lang)
        runners = obs.get("runners", [])
        observed = {r["file"]: r["status"] for r in runners}
        complete = (set(observed) == set(inventory) and len(observed) == len(runners)
                    and all(v == "PASS" for v in observed.values()) and obs.get("outcome") != "ERROR")
        # Квитанция существует и для пустого набора: успешный verify после удаления файлов
        # снимает прежний сбой. Она привязана к набору путей/байтов, а не к исчезающему module ID.
        rec = {"format": "bagaev-evidence/1", "kind": "test-suite", "test": lang.runner_suite,
               "subject": cand_sid, "verdict": "PASS" if complete else "ERROR", "inventory": inventory}
        out.append(dict(rec, id=C.digest("evidence", "1", rec)))
    return out


def runner_inventory(files: dict, lang) -> dict:
    return {path: hashlib.sha256(data).hexdigest() for path, data in lang.test_runners(files).items()}


def pending_runner_verification(base_files: dict, cand_files: dict, evidence: list, lang, cand_sid: str) -> str | None:
    """Новый набор runner-файлов или неповторённый сбой требуют verify (CHG-11/13).

    До первого прогона сравниваем с принятой базой, затем — с последним целым прогоном.
    Поэтому удалить, проверить пустой набор и вернуть прежний путь тоже нельзя без нового прогона.
    Успешная полная квитанция снимает все прежние runner-ошибки, в том числе старого формата.
    """
    suite = getattr(lang, "runner_suite", None)
    if suite is None:
        return None
    baseline, current = runner_inventory(base_files, lang), runner_inventory(cand_files, lang)
    previous, failed, invalid, verified_subject = baseline, False, False, None
    for ev in evidence:
        if ev["kind"] not in ("test-suite", "test-runner"):
            continue
        body = {k: v for k, v in ev.items() if k != "id"}
        valid = C.digest("evidence", "1", body) == ev.get("id")
        if ev["kind"] == "test-suite" and ev["test"] == suite:
            invalid = not valid
            if valid:
                previous, failed = ev.get("inventory"), ev["verdict"] != "PASS"
                verified_subject = ev["subject"]
        elif valid and ev["kind"] == "test-runner" and ev["verdict"] == "ERROR":
            failed = True
    # Граф именованных тестов не моделирует весь верхний уровень runner и его импортов.
    # Успех отдельного файла нельзя переносить только по его байтам или dependency-closure.
    changed_subject = (verified_subject != cand_sid if verified_subject is not None
                       else base_files != cand_files and bool(baseline or current))
    return suite if failed or invalid or changed_subject or previous != current else None


def assess(ev: dict, cand_graph, cand_sid: str) -> dict:
    body = {k: v for k, v in ev.items() if k != "id"}
    integrity = "valid" if C.digest("evidence", "1", body) == ev.get("id") else "invalid"
    if ev["subject"] == cand_sid:
        applicability, basis = "applicable", "same-subject"
    elif ev["kind"] == "test-suite" and ev["verdict"] == "ERROR":
        # Правка и переименование исходников не заменяют повторный прогон всей текущей группы.
        applicability, basis = "applicable", "runner-retry-required"
    elif (ev["kind"] == "test-run" and ev.get("closure_complete") is True and not certs.incomplete_coverage(cand_graph)
          and ev["test_id"] in cand_graph.nodes and ev["extractor_rev"] == cand_graph.data["extractor_rev"]
          and certs.closure_premises(cand_graph, ev["test_id"])["closure"] == ev["closure"]):
        applicability, basis = "applicable", "same-closure"             # перенос: то, что исполняет тест, не менялось
    else:
        applicability, basis = "stale", None
    return {"evidence": ev["id"], "test": ev["test"], "integrity": integrity, "applicability": applicability,
            "transfer_basis": basis, "verdict": ev["verdict"]}


def latest_by_test(evidence: list) -> dict:
    out = {}
    for ev in evidence:                                  # список в порядке добавления; последнее — свежее
        out[ev["test"]] = ev
    return out


def method_tests(target: str, base_g, cand_g, contract: dict) -> tuple[list, list]:
    """(методы правила, выбывшие тесты базы без replace_test) — CHG-12 sufficiency, CHG-13."""
    unchanged, changed = [], []
    for t in sorted(base_g.checkers(target)):
        c = cand_g.nodes.get(t)
        if c is not None and c["rev"] == base_g.nodes[t]["rev"] and target in cand_g.linked(t, "checks"):
            unchanged.append(t)
        else:
            changed.append(t)
    named = {c["method"]["test"] for c in contract["clauses"] if c["stage"] == "program_acceptance"}
    replaced = {r["test"] for r in contract.get("replaced_tests", [])}
    new = sorted(t for t in cand_g.checkers(target) if t not in unchanged and cand_g.nodes[t]["name"] in named)
    undeclared = [t for t in changed if t not in replaced and base_g.nodes[t]["name"] not in replaced]
    return unchanged + new, undeclared


def tests_status(target: str, base_g, cand_g, cand_sid: str, evidence: list, contract: dict) -> dict:
    methods, undeclared = method_tests(target, base_g, cand_g, contract)
    if undeclared:
        return dict(status="open", basis="base-test-changed", tests=[base_g.nodes[t]["name"] for t in undeclared],
                    detail="тест базы изменён, удалён или отвязан — нужен replace_test с причиной")
    if not methods:
        return dict(status="open", basis="no-method-tests",
                    detail="нет неизменённых тестов базы и тестов, названных методом условия контракта")
    latest = latest_by_test(evidence)
    assessments = [assess(latest[cand_g.nodes[t]["name"]], cand_g, cand_sid)
                   for t in methods if cand_g.nodes[t]["name"] in latest]
    good = [a for a in assessments if a["integrity"] == "valid" and a["applicability"] == "applicable"]
    if any(a["verdict"] in ("FAIL", "ERROR") for a in good):
        return dict(status="contradicted", basis="tests", assessments=assessments)
    if any(a["verdict"] not in ("PASS", "FAIL", "ERROR") for a in good):
        return dict(status="open", basis="test-not-run", assessments=assessments)
    if len(good) == len(methods):
        return dict(status="supported", basis="tests", assessments=assessments)
    return dict(status="open", basis="evidence-missing-or-stale", assessments=assessments)


def obligation_status(pair: dict, base_g, cand_g, cand_sid: str, evidence: list, contract: dict, policy: dict,
                      lineage: list = ()) -> dict:
    """Статус обязательства анализа влияния (open/unknown пары LNK-08-17) с учётом свидетельств (WorkState)."""
    kind, target, source = pair["kind"], pair["target"], pair["source"]
    key = [kind, target, source]
    allowed = policy["obligations"].get(kind, [])
    if pair["status"] == "excluded_with_basis":
        if not pair["reason"].startswith("D83a") or "D83a" in allowed:
            return dict(status="excluded_with_basis", basis=pair["reason"])
        # политика не разрешает D83(a) для этого вида: пара остаётся обязательством (M6)
    elif pair["status"] == "unknown":
        return dict(status="unknown", basis=pair["reason"])
    if target not in cand_g.nodes:
        # смысл исчез: удалён объявленно — обязательства нет; split/merge — его закрывают преемники (CHG-06)
        for rec in lineage:
            if target in rec.get("predecessors", ()) and rec["op"] == "delete":
                return dict(status="excluded_with_basis", basis="declared-delete", reason=rec["reason"])
            if target in rec.get("predecessors", ()) and rec["op"] in ("split", "merge"):
                succ = [tests_status(t, base_g, cand_g, cand_sid, evidence, contract) for t in rec["successors"]]
                if any(x["status"] == "contradicted" for x in succ):
                    return dict(status="contradicted", basis="successor-tests", successors=rec["successors"])
                if "tests" in allowed and all(x["status"] == "supported" for x in succ):
                    return dict(status="supported", basis="successor-tests", successors=rec["successors"])
                return dict(status="open", basis="successor-evidence", successors=rec["successors"])
        return dict(status="open", basis="target-removed")
    if "assumption" in allowed:
        for a in contract["assumptions"]:
            if a["obligation"] == key:
                return dict(status="supported", basis="assumption", reason=a["reason"])
    if "tests" in allowed:
        return tests_status(target, base_g, cand_g, cand_sid, evidence, contract)
    return dict(status="open", basis="no-method")


def clause_status(clause: dict, cand_g, cand_sid: str, evidence: list) -> dict:
    name = clause["method"]["test"]
    if not any(n["name"] == name and n["kind"] == "test" for n in cand_g.nodes.values()):
        return {"status": "open", "basis": "test-missing"}
    ev = latest_by_test(evidence).get(name)
    if ev is None:
        return {"status": "open", "basis": "evidence-missing"}
    a = assess(ev, cand_g, cand_sid)
    if a["integrity"] != "valid" or a["applicability"] != "applicable":
        return {"status": "open", "basis": "evidence-stale", "assessments": [a]}
    if a["verdict"] not in ("PASS", "FAIL", "ERROR"):
        return {"status": "open", "basis": "test-not-run", "assessments": [a]}
    return {"status": "supported" if a["verdict"] == "PASS" else "contradicted", "basis": "tests", "assessments": [a]}
