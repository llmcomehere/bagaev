"""MACHINE-1 — CEK-машина над BIR-1 (spec/runtime/machine.md).

Состояние: режим (Eval узла | Value), окружение, продолжение K (связный список неизменяемых кадров),
регистр возврата rk (продолжение, в которое `return` доставляет значение). Каждый переход — одно
платное правило §4; проверки terminal → cancel → budget перед переходом не платные (§3).
Рекурсия хоста для пользовательской рекурсии не используется: шаг — переход явного состояния.
"""
from __future__ import annotations

from bagaev_ref.ir import bir as B
from bagaev_ref.machine.values import Clo, MapV, Rec, Var
from bagaev_ref.stdlib.prims import Fault, NotImplementedPrim, first_duplicate

(F_LET, F_IF, F_CALLFN, F_CALLARGS, F_PRIM, F_VARIANT, F_MATCH, F_RECORD, F_FIELD, F_SEQ, F_MAP,
 F_RETURN, F_PERFORM) = range(13)


class HostStop(Exception):
    """Хост отказал в операции (ACCESS_DENIED и др.): защитный исход, переход не публикуется (HOST-1)."""

    def __init__(self, code: str, **data):
        super().__init__(code)
        self.code, self.data = code, data


class Execution:
    __slots__ = ("termination", "code", "value", "steps", "trace", "site", "data")

    def __init__(self, termination, code, value=None, steps=0, trace=None, site=None, data=None):
        self.termination, self.code, self.value, self.steps = termination, code, value, steps
        self.trace, self.site, self.data = trace, site, data


def run(start: B.Node, env, budget: int, trace: list | None = None, cancel_at: int | None = None,
        host=None) -> Execution:
    """Исполнить узел start в окружении env. trace — список для записей L1 (rule, nid) или None (L2).
    host — исполнитель Perform (HOST-1) или None: тогда Perform даёт IMPLEMENTATION_STOP NOT_IMPLEMENTED."""
    CONST, LOCAL, GLOBAL, LET, LAMBDA, CALL, IF, MATCH, VARIANT, RECORD, FIELD, SEQ, MAP, PRIM, RETURN, PERFORM = \
        range(16)
    node, val, ev, K, rk, steps = start, None, True, None, None, 0
    rule = nid = None
    try:
        while True:
            if not ev and K is None:
                return Execution("RETURNED", "RETURNED", val, steps, trace)
            if cancel_at is not None and steps == cancel_at:
                return Execution("SEMANTIC_STOP", "CANCELLED", None, steps, trace)
            if steps >= budget:
                return Execution("SEMANTIC_STOP", "BUDGET_EXCEEDED", None, steps, trace)
            steps += 1
            if ev:
                k = node.k
                nid = node.nid
                if k == LOCAL:
                    e = env
                    for _ in range(node.index):
                        e = e[1]
                    val, ev, rule = e[0], False, "VAR"
                elif k == CONST:
                    val, ev, rule = node.value, False, "CONST"
                elif k == CALL:
                    K = ((F_CALLFN, node, env, rk), K)
                    node, rule = node.fn, "CALL_ENTER"
                elif k == PRIM:
                    if node.args:
                        K = ((F_PRIM, node, env, rk, ()), K)
                        node, rule = node.args[0], "PRIM_ENTER"
                    else:
                        rule = "PRIM_APPLY"
                        try:
                            val, ev = node.fn(), False
                        except Fault as flt:
                            if trace is not None:
                                trace.append((rule, nid))
                            return Execution("FAULT", flt.code, None, steps, trace, node.site, flt.data)
                elif k == GLOBAL:
                    val, ev, rule = node.fn.closure, False, "VAR"
                elif k == LET:
                    K = ((F_LET, node, env, rk), K)
                    node, rule = node.value, "LET_ENTER"
                elif k == IF:
                    K = ((F_IF, node, env, rk), K)
                    node, rule = node.cond, "IF_ENTER"
                elif k == MATCH:
                    K = ((F_MATCH, node, env, rk), K)
                    node, rule = node.scrutinee, "MATCH_ENTER"
                elif k == LAMBDA:
                    val, ev, rule = Clo(node.body, node.arity, env), False, "LAMBDA"
                elif k == VARIANT:
                    K = ((F_VARIANT, node, env, rk), K)
                    node, rule = node.payload, "VARIANT_ENTER"
                elif k == RECORD:
                    rule = "RECORD_ENTER"
                    if node.entries:
                        K = ((F_RECORD, node, env, rk, ()), K)
                        node = node.entries[0][1]
                    else:
                        val, ev = Rec(()), False
                elif k == FIELD:
                    K = ((F_FIELD, node, env, rk), K)
                    node, rule = node.target, "FIELD_ENTER"
                elif k == SEQ:
                    rule = "SEQ_ENTER"
                    if node.items:
                        K = ((F_SEQ, node, env, rk, ()), K)
                        node = node.items[0]
                    else:
                        val, ev = (), False
                elif k == MAP:
                    rule = "MAP_ENTER"
                    if node.items:
                        K = ((F_MAP, node, env, rk, ()), K)
                        node = node.items[0]
                    else:
                        val, ev = MapV({}), False
                elif k == RETURN:
                    K = ((F_RETURN, node, env, rk), K)
                    node, rule = node.value, "RETURN_ENTER"
                elif k == PERFORM:
                    if host is None:
                        steps -= 1                      # непубликованный переход не списывается (§3)
                        return Execution("IMPLEMENTATION_STOP", "NOT_IMPLEMENTED", None, steps, trace, node.site,
                                         {"detail": f"операция хоста {node.op} исполняется хостом в транзакции"})
                    if node.args:
                        K = ((F_PERFORM, node, env, rk, ()), K)
                        node, rule = node.args[0], "PERFORM_ENTER"
                    else:
                        try:
                            val = host.perform(node.op, node.resource, (), node)
                        except HostStop as hs:
                            steps -= 1
                            return Execution("IMPLEMENTATION_STOP", hs.code, None, steps, trace, node.site, hs.data)
                        ev, rule = False, "PERFORM_APPLY"
                else:
                    raise AssertionError(f"неизвестная форма {k}")
            else:
                fr, K = K
                f = fr[0]
                fnode = fr[1]
                nid = fnode.nid
                if f == F_CALLARGS:
                    done = fr[5] + (val,)
                    args = fnode.args
                    if len(done) < len(args):
                        K = ((F_CALLARGS, fnode, fr[2], fr[3], fr[4], done), K)
                        node, env, rk, ev, rule = args[len(done)], fr[2], fr[3], True, "CALL_NEXT"
                    else:
                        clo = fr[4]
                        env = clo.env
                        for a in done:
                            env = (a, env)
                        node, rk, ev, rule = clo.body, K, True, "CALL_BODY"
                elif f == F_PRIM:
                    done = fr[4] + (val,)
                    args = fnode.args
                    if len(done) < len(args):
                        K = ((F_PRIM, fnode, fr[2], fr[3], done), K)
                        node, env, rk, ev, rule = args[len(done)], fr[2], fr[3], True, "PRIM_NEXT"
                    else:
                        rule = "PRIM_APPLY"
                        try:
                            val = fnode.fn(*done)
                        except Fault as flt:
                            if trace is not None:
                                trace.append((rule, nid))
                            return Execution("FAULT", flt.code, None, steps, trace, fnode.site, flt.data)
                elif f == F_LET:
                    env, rk = (val, fr[2]), fr[3]
                    node, ev, rule = fnode.body, True, "LET_BIND"
                elif f == F_CALLFN:
                    clo = val
                    if fnode.args:
                        K = ((F_CALLARGS, fnode, fr[2], fr[3], clo, ()), K)
                        node, env, rk, ev, rule = fnode.args[0], fr[2], fr[3], True, "CALL_ARGS"
                    else:
                        node, env, rk, ev, rule = clo.body, clo.env, K, True, "CALL_BODY"
                elif f == F_IF:
                    env, rk, ev = fr[2], fr[3], True
                    if val:
                        node, rule = fnode.then, "IF_THEN"
                    else:
                        node, rule = fnode.els, "IF_ELSE"
                elif f == F_MATCH:
                    if fnode.opaque:
                        bind, body = next(iter(fnode.arms.values()))
                        payload = val
                    else:
                        bind, body = fnode.arms[val.tag]
                        payload = val.payload
                    env = (payload, fr[2]) if bind else fr[2]
                    node, rk, ev, rule = body, fr[3], True, "MATCH_ARM"
                elif f == F_VARIANT:
                    if fnode.ordinal >= 0:
                        val = Var(fnode.ordinal, fnode.tag, val)
                    rule = "VARIANT_WRAP"
                elif f == F_RECORD:
                    done = fr[4] + (val,)
                    entries = fnode.entries
                    if len(done) < len(entries):
                        K = ((F_RECORD, fnode, fr[2], fr[3], done), K)
                        node, env, rk, ev, rule = entries[len(done)][1], fr[2], fr[3], True, "RECORD_NEXT"
                    else:
                        slots = [None] * fnode.nfields
                        for (s, _), v in zip(entries, done):
                            slots[s] = v
                        val, rule = Rec(tuple(slots)), "RECORD_BUILD"
                elif f == F_FIELD:
                    val, rule = val.fields[fnode.index], "FIELD_GET"
                elif f == F_SEQ:
                    done = fr[4] + (val,)
                    if len(done) < len(fnode.items):
                        K = ((F_SEQ, fnode, fr[2], fr[3], done), K)
                        node, env, rk, ev, rule = fnode.items[len(done)], fr[2], fr[3], True, "SEQ_NEXT"
                    else:
                        val, rule = done, "SEQ_BUILD"
                elif f == F_MAP:
                    done = fr[4] + (val,)
                    if len(done) < len(fnode.items):
                        K = ((F_MAP, fnode, fr[2], fr[3], done), K)
                        node, env, rk, ev, rule = fnode.items[len(done)], fr[2], fr[3], True, "MAP_NEXT"
                    else:
                        rule = "MAP_BUILD"
                        keys = list(done[0::2])
                        dup = first_duplicate(keys)
                        if dup:
                            if trace is not None:
                                trace.append((rule, nid))
                            return Execution("FAULT", "DUPLICATE_KEY", None, steps, trace, fnode.site,
                                             {"first": dup[0], "second": dup[1]})
                        val = MapV(dict(zip(keys, done[1::2])))
                elif f == F_RETURN:
                    K, rule = fr[3], "RETURN_EXIT"   # к продолжению вызова функции (регистр возврата кадра)
                elif f == F_PERFORM:
                    done = fr[4] + (val,)
                    if len(done) < len(fnode.args):
                        K = ((F_PERFORM, fnode, fr[2], fr[3], done), K)
                        node, env, rk, ev, rule = fnode.args[len(done)], fr[2], fr[3], True, "PERFORM_NEXT"
                    else:
                        try:
                            val = host.perform(fnode.op, fnode.resource, done, fnode)
                        except HostStop as hs:
                            steps -= 1                  # отказ хоста не публикует переход
                            return Execution("IMPLEMENTATION_STOP", hs.code, None, steps, trace, fnode.site, hs.data)
                        rule = "PERFORM_APPLY"
                else:
                    raise AssertionError(f"неизвестный кадр {f}")
            if trace is not None:
                trace.append((rule, nid))
    except NotImplementedPrim as e:
        return Execution("IMPLEMENTATION_STOP", "NOT_IMPLEMENTED", None, steps - 1, trace, None, {"detail": str(e)})
    except MemoryError:
        return Execution("IMPLEMENTATION_STOP", "RESOURCE_LIMIT", None, steps - 1, trace)
    except RecursionError:
        raise                                          # глубокое значение — защитный исход вызывающего (CLI)
    except Exception as e:                             # нарушен инвариант принятой программы (OUT-01)
        return Execution("IMPLEMENTATION_STOP", "MACHINE_INVARIANT", None, steps - 1, trace, None,
                         {"detail": f"{type(e).__name__}: {e}"})
