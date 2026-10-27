"""ChangeContract CHANGE-1 (spec/protocol/agent-protocol.md §4; 03-change-algorithms §1, D27).

Контракт — неизменяемый объект; правка даёт новую ревизию. Условия (clauses) не исчезают молча: замена и
удаление требуют причины и остаются в `replaced` (T10-C02). Так же явно, с причиной, тест базы перестаёт быть
методом своего правила (`replace_test`): изменённый, удалённый или отвязанный тест без этой записи держит
обязательство открытым. Контракт закрепляет ревизию политики приёмки (A05 шаг 3); смена политики — блокер,
пока её не закрепят заново (`pin_policy` с причиной). Политика по умолчанию не ослабляется автоматически.
"""
from __future__ import annotations

from bagaev_ref.change.sourceedit import EditError
from bagaev_ref.kernel import canonical as C

ID_RE_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_-")

# Политика приёмки: вид обязательства → допустимые основания (CHG-09).
DEFAULT_POLICY = {
    "format": "bagaev-acceptance-policy/1",
    "obligations": {
        "implements": ["tests", "D83a"], "requires": ["tests", "D83a"], "checks": ["tests"],
        "about": ["assumption"], "derived_from": ["assumption"], "clause": ["tests"],
    },
    "principals": None,
}


def policy_ref(policy: dict) -> str:
    return C.digest("acceptance-policy", "1", {k: v for k, v in policy.items() if k != "principals"})


def initial(change_id: str, intent: str, base: str, policy: str) -> dict:
    return {"format": "bagaev-change-contract/1", "change_id": change_id, "revision": "1", "intent": intent,
            "base": base, "policy": policy, "clauses": [], "replaced": [], "replaced_tests": [], "policy_pins": [],
            "assumptions": [], "allowed": None}


def _reason(op, k):
    r = op.get("reason")
    if not isinstance(r, str) or not r:
        raise EditError("REQUEST_INVALID", op=k, detail="причина обязательна")
    return r


def _clause(op, k):
    cid, claim, method = op.get("id"), op.get("claim"), op.get("method")
    if not (isinstance(cid, str) and cid and set(cid) <= ID_RE_CHARS and isinstance(claim, str) and claim):
        raise EditError("REQUEST_INVALID", op=k, detail="условие: id [a-z0-9_-], claim — текст")
    if not (isinstance(method, dict) and set(method) == {"test"} and isinstance(method["test"], str)):
        raise EditError("REQUEST_INVALID", op=k, detail="method — {test: <полное имя теста>}")
    stage = op.get("stage", "program_acceptance")
    if stage not in ("program_acceptance", "runtime_activation"):
        raise EditError("REQUEST_INVALID", op=k, detail="stage — program_acceptance или runtime_activation")
    return {"id": cid, "claim": claim, "method": method, "stage": stage}


def update(contract: dict, ops: list, policy: str | None = None) -> dict:
    """Новая ревизия контракта. Операции: add_clause, replace_clause, remove_clause, replace_test, assume, scope,
    pin_policy (закрепить текущую политику `policy`)."""
    if not isinstance(ops, list) or not ops:
        raise EditError("REQUEST_INVALID", detail="ops — непустой список")
    c = C.decode(C.encode(contract))
    by_id = {x["id"]: x for x in c["clauses"]}
    for k, op in enumerate(ops):
        kind = op.get("op") if isinstance(op, dict) else None
        if kind == "add_clause":
            cl = _clause(op, k)
            if cl["id"] in by_id or any(r["id"] == cl["id"] for r in c["replaced"]):
                raise EditError("REQUEST_INVALID", op=k, detail="ID условия уже был")
            c["clauses"].append(cl)
            by_id[cl["id"]] = cl
        elif kind in ("replace_clause", "remove_clause"):
            cid, reason = op.get("id"), op.get("reason")
            if not isinstance(cid, str) or cid not in by_id or not isinstance(reason, str) or not reason:
                raise EditError("REQUEST_INVALID", op=k, detail="условие существует, причина обязательна")
            new = _clause(op, k) if kind == "replace_clause" else None
            if new is not None and new["id"] != cid:
                raise EditError("REQUEST_INVALID", op=k, detail="замена сохраняет ID условия")
            c["replaced"].append({"id": cid, "old": by_id[cid], "new": new, "reason": reason,
                                  "revision": str(int(c["revision"]) + 1)})
            c["clauses"] = [x for x in c["clauses"] if x["id"] != cid] + ([new] if new else [])
            if new:
                by_id[cid] = new
            else:
                del by_id[cid]
        elif kind == "replace_test":
            test, reason = op.get("test"), _reason(op, k)
            if not isinstance(test, str) or not test or set(op) - {"op", "test", "reason"}:
                raise EditError("REQUEST_INVALID", op=k, detail="replace_test: test — полное имя или EntityId теста базы")
            c["replaced_tests"] = [r for r in c["replaced_tests"] if r["test"] != test] + [
                {"test": test, "reason": reason, "revision": str(int(c["revision"]) + 1)}]
            c["replaced_tests"].sort(key=lambda r: r["test"])
        elif kind == "pin_policy":
            reason = _reason(op, k)
            if policy is None:
                raise EditError("REQUEST_INVALID", op=k, detail="политика недоступна")
            c["policy_pins"].append({"from": c["policy"], "to": policy, "reason": reason,
                                     "revision": str(int(c["revision"]) + 1)})
            c["policy"] = policy
        elif kind == "assume":
            ob, reason = op.get("obligation"), op.get("reason")
            if not (isinstance(ob, list) and len(ob) == 3 and all(isinstance(x, str) for x in ob)
                    and isinstance(reason, str) and reason):
                raise EditError("REQUEST_INVALID", op=k, detail="assume: obligation [вид, цель, источник], причина")
            c["assumptions"] = [a for a in c["assumptions"] if a["obligation"] != ob] + [{"obligation": ob, "reason": reason}]
        elif kind == "scope":
            allowed = op.get("allowed")
            if not (allowed is None or (isinstance(allowed, list) and all(isinstance(x, str) for x in allowed))):
                raise EditError("REQUEST_INVALID", op=k, detail="scope.allowed — список сущностей или null")
            c["allowed"] = None if allowed is None else sorted(set(allowed))
        else:
            raise EditError("REQUEST_INVALID", op=k, detail="op — add_clause, replace_clause, remove_clause, "
                                                            "replace_test, assume, scope, pin_policy")
    c["assumptions"].sort(key=lambda a: a["obligation"])
    c["revision"] = str(int(c["revision"]) + 1)
    return c
