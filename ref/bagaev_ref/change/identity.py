"""Операции идентичности CHANGE-1 (spec/protocol/agent-protocol.md §3; 01-program-model §7A, SURF-07, D67).

Сверяется разница EntityId между кандидатом до и после правки с объявленными identity_ops:
- исчезнувший ID обязан быть объявлен (delete, split.from, merge.from) — иначе ENTITY_REMOVED_WITHOUT_INTENT;
- повтор ID в кандидате (копия без нового ID) — DUPLICATE_ENTITY_ID;
- новый ID не может совпасть с ID из истории принятых снимков, которого нет в кандидате (ENTITY_ID_RETIRED);
- объявленная операция обязана совпасть с фактом — иначе IDENTITY_OP_MISMATCH;
- вид сущности под тем же ID не меняется (01 §3): иначе ENTITY_KIND_CHANGED — нужен delete и новый ID.
Переименование с тем же ID распознаётся само; объявленный rename проверяется. Каждая запись lineage —
`{op, predecessors, successors, reason}` (CHG-07); причина обязательна для delete, split, merge, у rename и copy —
необязательна (null), rename добавляет прежнее и новое имя.
"""
from __future__ import annotations

import random

from bagaev_ref.change.sourceedit import EditError
from bagaev_ref.kernel import canonical as C
from bagaev_ref.syntax import ast as A
from bagaev_ref.syntax.parser import parse
from bagaev_ref.syntax.printer import ID_ATTR, assign_ids, id_sites


def _kind(node) -> str:
    """Вид сущности словом поверхности: FnDecl → fn, TestDecl → test, Field → field."""
    n = type(node).__name__
    return (n[:-4] if n.endswith("Decl") else n).lower()


def entities(files: dict) -> tuple[dict, list]:
    """EntityId → [(файл, вид, имя)] по местам SURF-07; при ошибке разбора — (None, диагностики)."""
    out, diags = {}, []
    for path, data in sorted(files.items()):
        tree, _, d = parse(data, path)
        if d or tree is None:
            diags += [x.to_json() for x in d]
            continue
        mod = ".".join(n.text for n in tree.module.path)
        for node, _ in id_sites(tree):
            ids = [a.args[0][1] for a in node.attrs if a.name.text == "id" and a.args]
            if not ids:
                continue
            if isinstance(node, A.ModuleHeader):
                kind, name = "module", mod
            elif isinstance(node, A.Item):
                kind, name = _kind(node.decl), f"{mod}.{node.decl.name.text}"
            else:
                kind, name = _kind(node), f"{mod}.?.{node.name.text}"
            out.setdefault(ids[0], []).append((path, kind, name))
    return (None, diags) if diags else (out, [])


def _ids(op, key):
    v = op.get(key)
    return [v] if isinstance(v, str) else list(v) if isinstance(v, list) and all(isinstance(x, str) for x in v) else None


def _one(op, key):
    v = op.get(key)
    return v if isinstance(v, str) else None


def _reason(op):
    r = op.get("reason")
    return r if isinstance(r, str) and r else None


def check_form(ops) -> None:
    """Форма identity_ops (CHG-04 шаг 1) — до сравнения с фактом."""
    if not isinstance(ops, list):
        raise EditError("REQUEST_INVALID", detail="identity_ops — список")
    shapes = {"rename": {"id"}, "copy": {"from", "id"}, "delete": {"id", "reason"},
              "split": {"from", "into", "reason"}, "merge": {"from", "into", "reason"}}
    for k, op in enumerate(ops):
        kind = op.get("op") if isinstance(op, dict) else None
        if kind not in shapes:
            raise EditError("REQUEST_INVALID", op=k, detail="op — rename, copy, delete, split, merge")
        extra = set(op) - shapes[kind] - {"op", "reason"}
        ids_ok = all(isinstance(op.get(x), str) for x in shapes[kind] & {"id"}) and (
            kind not in ("copy",) or isinstance(op.get("from"), str)) and (
            kind not in ("split", "merge") or (_ids(op, "from") and _ids(op, "into")))
        if extra or not ids_ok or ("reason" in op and not isinstance(op["reason"], str)):
            raise EditError("REQUEST_INVALID", op=k, detail=f"{kind}: поля {sorted(shapes[kind])}, ID — строки")


def check_identity(before: dict, after: dict, ops: list, history_ids: set) -> dict:
    """Проверить переход before → after (EntityId → места). Возвращает записи lineage и наблюдённое."""
    check_form(ops)
    dup = sorted(i for i, places in after.items() if len(places) > 1)
    if dup:
        raise EditError("DUPLICATE_ENTITY_ID", ids=dup, places={i: [p for p, _, _ in after[i]] for i in dup})
    removed, added = set(before) - set(after), set(after) - set(before)
    kinds = sorted(i for i in set(before) & set(after) if before[i][0][1] != after[i][0][1])
    if kinds:
        raise EditError("ENTITY_KIND_CHANGED", ids=kinds,
                        kinds={i: [before[i][0][1], after[i][0][1]] for i in kinds})
    retired = sorted(added & (history_ids - set(before)))
    if retired:
        raise EditError("ENTITY_ID_RETIRED", ids=retired)
    declared_removed, declared_added, lineage = set(), set(), []
    for k, op in enumerate(ops):
        kind, reason = op["op"], _reason(op)
        if kind == "rename":
            i = _one(op, "id")
            if i not in before or i not in after or before[i][0][2] == after[i][0][2]:
                raise EditError("IDENTITY_OP_MISMATCH", op=k, detail="rename: ID в обеих версиях и имя изменилось")
            lineage.append({"op": "rename", "predecessors": [i], "successors": [i], "reason": reason,
                            "names": [before[i][0][2], after[i][0][2]]})
        elif kind == "copy":
            src, new = _one(op, "from"), _one(op, "id")
            if src not in after or new not in added or after[new][0][1] != after[src][0][1]:
                raise EditError("IDENTITY_OP_MISMATCH", op=k, detail="copy: источник жив, копия — новый ID того же вида")
            declared_added.add(new)
            lineage.append({"op": "copy", "predecessors": [src], "successors": [new], "reason": reason})
        elif kind == "delete":
            i = _one(op, "id")
            if i not in removed or reason is None:
                raise EditError("IDENTITY_OP_MISMATCH", op=k, detail="delete: ID исчез, причина обязательна")
            declared_removed.add(i)
            lineage.append({"op": "delete", "predecessors": [i], "successors": [], "reason": reason})
        else:
            src, dst = _ids(op, "from"), _ids(op, "into")
            ok = (set(src) <= removed and set(dst) <= added and reason is not None
                  and (len(src) == 1 < len(dst) if kind == "split" else len(src) > 1 == len(dst)))
            if not ok:
                raise EditError("IDENTITY_OP_MISMATCH", op=k, detail=f"{kind}: from исчезли, into новые, причина")
            declared_removed |= set(src)
            declared_added |= set(dst)
            lineage.append({"op": kind, "predecessors": sorted(src), "successors": sorted(dst), "reason": reason})
    silent = sorted(removed - declared_removed)
    if silent:
        raise EditError("ENTITY_REMOVED_WITHOUT_INTENT", ids=silent,
                        names={i: before[i][0][2] for i in silent})
    renamed = sorted(i for i in set(before) & set(after) if before[i][0][2] != after[i][0][2])
    return {"lineage": lineage, "removed": sorted(removed), "added": sorted(added), "renamed": renamed}


def fill_ids(files: dict, touched: set, seed: str, taken: set) -> tuple[dict, dict]:
    """FMT-16 детерминированно: недостающие @id в затронутых файлах из ГПСЧ с семенем работы (CHG-05).
    Возвращает файлы и назначенные ID по файлам в порядке мест — их журнал правок хранит для rebase (CHG-18)."""
    rng = random.Random(C.digest("assign-ids", "1", {"seed": seed}))
    out, assigned = dict(files), {}
    for path in sorted(touched):
        if path in out:
            before = set(ID_ATTR.findall(out[path].decode("utf-8")))
            out[path] = assign_ids(out[path], path, taken, rng)
            new = [x for x in ID_ATTR.findall(out[path].decode("utf-8")) if x not in before]
            if new:
                assigned[path] = new
    return out, assigned


def place_ids(data: bytes, path: str, ids: list) -> bytes:
    """Вставить ранее назначенные ID в места без @id по порядку (повтор CHG-05 при rebase)."""
    tree, _, diags = parse(data, path)
    if diags or tree is None:
        raise EditError("CANDIDATE_UNPARSABLE", path=path)
    sites = [(node.start, inline) for node, inline in id_sites(tree) if not any(a.name.text == "id" for a in node.attrs)]
    if len(sites) != len(ids):
        raise EditError("REBASE_CONFLICT", path=path, detail="места назначенных ID не совпали")
    out = data
    for (pos, inline), i in sorted(zip(sites, ids), reverse=True):
        out = out[:pos] + (f'@id("{i}")' + (" " if inline else "\n")).encode("utf-8") + out[pos:]
    return out
