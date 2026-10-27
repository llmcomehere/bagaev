"""Приёмка и перенос работы на новый head CHANGE-1 (spec/protocol/agent-protocol.md §8–§9; A05, D14, D29).

accept — в транзакции записи (её открыл слой операций): head == база (STALE_BASE), ревизия работы уже сверена
(WORK_CONFLICT), производное состояние пересчитано заново, блокеры (OPEN_OBLIGATIONS) — до любых записей.
Затем вместе: запись приёмки, снимок помечен принятым, новый head, ревизия head, закрытая работа, журнал,
квитанция. Приёмка ничего не исполняет: ни тестов, ни миграций, ни точек входа (T10-C06).

rebase — переносит журнал правок работы на текущий head: файл без изменений в head — правка как есть; изменённый —
только правки old_text (ровно одно вхождение), иначе REBASE_CONFLICT. ID, назначенные при apply (assign_ids),
ставятся те же — из журнала. Совместный кандидат и его идентичность проверяются заново; несовпадение
объявленных операций с новым head — тоже REBASE_CONFLICT.
"""
from __future__ import annotations

import hashlib

from bagaev_ref.change import identity as I
from bagaev_ref.change import workstate as W
from bagaev_ref.change.sourceedit import EditError, apply_source_edit
from bagaev_ref.kernel import canonical as C


def accept(ops, ch, w):
    from bagaev_ref.protocol.ops import OpError
    st = ops.store
    head = st.meta("head")
    if head != w["base"]:
        raise OpError("STALE_BASE", expected=w["base"], head=head)
    v = W.view(st, ch)
    v.pop("_graphs", None)
    blockers = [b for b in v["blockers"] if b["kind"] != "NEEDS_REBASE"]
    if blockers:
        raise OpError("OPEN_OBLIGATIONS", blockers=blockers)
    rec = {"format": "bagaev-acceptance/1", "kind": "change", "change_id": ch, "base": w["base"],
           "candidate": w["candidate"], "work_revision": str(w["work_revision"]), "contract": w["contract"],
           "contract_revision": str(w["contract_revision"]), "policy": v["policy"], "principal": ops.principal,
           "evidence": v["evidence"], "lineage": w["lineage"],
           "assessments": [[a["evidence"], a["test"], a["applicability"], a["transfer_basis"], a["verdict"]]
                           for a in v["assessments"]],
           "obligations": [[*o["obligation"], o["status"], o["basis"]] for o in v["obligations"]],
           "clauses": [[c["id"], c["status"]] for c in v["clauses"]],
           "replaced_clauses": [r["id"] for r in v["contract"]["replaced"]],
           "replaced_tests": [[r["test"], r["reason"]] for r in v["contract"]["replaced_tests"]],
           "policy_pins": [[r["from"], r["to"], r["reason"]] for r in v["contract"]["policy_pins"]],
           "coverage_gaps": [[g["entity"], g["reason"]] for g in v["impact"]["gaps"]],
           "head_revision": str(int(st.meta("head_revision")) + 1)}
    rid = C.digest("acceptance", "1", rec)
    st.db.execute("INSERT INTO acceptance VALUES (?, ?, ?)", (rid, C.encode(rec), int(st.meta("head_revision")) + 1))
    st.db.execute("UPDATE snapshots SET accepted = 1 WHERE id = ?", (w["candidate"],))
    st.set_meta("head", w["candidate"])
    st.set_meta("head_revision", int(st.meta("head_revision")) + 1)
    ops.save_work(ch, status="accepted", work_revision=w["work_revision"] + 1)
    return {"acceptance": rid, "head": w["candidate"], "head_revision": int(st.meta("head_revision")),
            "obligations": rec["obligations"], "replaced_clauses": rec["replaced_clauses"],
            "replaced_tests": rec["replaced_tests"], "coverage_gaps": rec["coverage_gaps"],
            "lineage": rec["lineage"]}, w["work_revision"] + 1


def rebase(ops, ch, w):
    from bagaev_ref.protocol.ops import OpError, unstrip
    st = ops.store
    head = st.meta("head")
    if head == w["base"]:
        raise OpError("REBASE_NOT_NEEDED", head=head)
    files = st.files(head)
    ops_all = []
    for ref in w["edits"]:
        entry = unstrip(st.get_json(ref))
        edit, assigned = entry["source_edit"], entry["assigned_ids"]
        ops_all += edit.get("identity_ops", [])
        entries = []
        for f in edit["files"]:
            cur = files.get(f["path"])
            if "create" in f:
                if cur is not None:
                    raise OpError("REBASE_CONFLICT", path=f["path"], detail="файл уже есть в head")
                entries.append(f)
                continue
            if cur is not None and hashlib.sha256(cur).hexdigest() == f.get("base_sha256"):
                entries.append(f)                        # файл в head тот же — правка как есть
            elif cur is not None and "edits" in f and all("old_text" in e for e in f["edits"]):
                entries.append(dict(f, base_sha256=hashlib.sha256(cur).hexdigest()))   # якоря по тексту
            else:
                raise OpError("REBASE_CONFLICT", path=f["path"], detail="файл изменён в head, правка привязана к байтам")
        try:
            files, _ = apply_source_edit(files, dict(edit, files=entries, identity_ops=[], assign_ids=False), ops.lang.exts)
            for path, ids in sorted(assigned.items()):
                files[path] = I.place_ids(files[path], path, ids)
        except EditError as e:
            raise OpError("REBASE_CONFLICT", path=e.data.get("path"), cause=e.code)
    before, _ = ops.lang.entities(st.files(head))
    after, diags = ops.lang.entities(files)
    if after is None:
        raise OpError("CANDIDATE_UNPARSABLE", diagnostics=diags)
    try:
        ident = I.check_identity(before or {}, after, ops_all, W.history_ids(st))
    except EditError as e:                               # например, удалённое работой уже удалено в head
        raise OpError("REBASE_CONFLICT", cause=e.code, detail="идентичность не переносится на новый head")
    sid = st.snapshot(files, [head, w["candidate"]])
    ops.save_work(ch, base=head, candidate=sid, work_revision=w["work_revision"] + 1, lineage=ident["lineage"])
    return {"base": head, "candidate": sid, "identity": ident}, w["work_revision"] + 1
