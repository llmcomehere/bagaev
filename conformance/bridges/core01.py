#!/usr/bin/env python3
"""Мост MACHINE-1 → CORE-0.1 (spec/runtime/machine.md MCH-11): вторая независимая реализация уровня L1.

Программа модуля из подмножества CORE-0.1 понижается эталоном в BIR-1 и переводится в CORE-0.1 JSON:
`letrec` всех функций модуля вокруг тела точки входа. Затем её исполняет замороженный
models/r07-core/experiments/core-machine/engine.py (байты модели не меняются, только импорт).
Сравниваются исход, значение и трасса правил вместе с nid, с переименованием MCH-11 и без первого `LETREC`.

Источники программ: случаи conformance/cases с фазой run, которые переводятся, и порождённые
программы (типизированный генератор подмножества CORE). Для каждой — полная матрица бюджетов и отмен.

  python3 conformance/bridges/core01.py [--generated N] [--seed S]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ref"))

from bagaev_ref.ir import bir as B  # noqa: E402
from bagaev_ref.machine import cek  # noqa: E402
from bagaev_ref.machine.runner import find_entry, prepare  # noqa: E402
from bagaev_ref.machine.values import NOPAY, Var  # noqa: E402
from bagaev_ref.sema import types as T  # noqa: E402

ENGINE = ROOT / "models" / "r07-core" / "experiments" / "core-machine" / "engine.py"
RENAME = {"RESULT_ENTER": "VARIANT_ENTER", "RESULT_WRAP": "VARIANT_WRAP", "MATCH_OK": "MATCH_ARM",
          "MATCH_ERR": "MATCH_ARM"}
PRIMS = {"std.i64.eq@1": "i64.eq", "std.i64.lt@1": "i64.lt", "std.i64.add@1": "i64.add", "std.i64.sub@1": "i64.sub",
         "std.i64.div@1": "i64.div", "std.i64.rem@1": "i64.rem"}
AE = "std.i64.ArithmeticError"


def load_engine():
    spec = importlib.util.spec_from_file_location("core_machine_engine_r07", ENGINE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["core_machine_engine_r07"] = mod
    spec.loader.exec_module(mod)
    return mod


class NotInSubset(Exception):
    pass


def core_type(t):
    t = T.prune(t)
    if isinstance(t, T.TCon):
        if t.name in ("Bool", "Int64"):
            return t.name
        if t.name == "Unit":
            return "Unit"
        if t.name == "Result" and core_type(t.args[1]) == "ArithmeticError":
            return {"tag": "result", "ok": core_type(t.args[0])}
    if isinstance(t, T.TNom) and t.info.qname == AE:
        return "ArithmeticError"
    if isinstance(t, T.TFn) and not t.row.resolved().atoms:
        return {"tag": "fn", "params": [core_type(p) for p in t.params], "result": core_type(t.ret)}
    raise NotInSubset(f"тип {T.show(t)}")


def ty_of(n):
    t = getattr(n, "ty", None)
    if t is not None:
        return t
    if n.k == B.CONST:                                   # синтезированная константа: тип по значению
        v = n.value
        return T.BOOL if isinstance(v, bool) else T.INT if isinstance(v, int) else T.UNIT if v is None else T.TError()
    raise NotInSubset(f"у узла {B.FORM_NAMES[n.k]} нет типа")


class Translator:
    def __init__(self):
        self.binders = 0
        self.stack: list = []

    def fresh(self, hint: str) -> str:
        self.binders += 1
        return f"b{self.binders}.{hint}"

    def fn_sig(self, info):
        if info.tparams or info.eparams or info.row.atoms:
            raise NotInSubset(f"{info.qname}: обобщения или эффекты")
        return [core_type(p) for p in info.params], core_type(info.ret)

    def program(self, prog, entry_info) -> dict:
        functions = []
        for info, fn in prog.functions.items():
            if info.module.is_std or info.module is not entry_info.module or info.kind != "fn" or info is entry_info:
                continue
            ptypes, ret = self.fn_sig(info)
            names = [self.fresh(p.name.text) for p in info.decl.params]
            self.stack = list(names)
            functions.append({"binder": info.qname, "params": [{"binder": n, "type": t} for n, t in zip(names, ptypes)],
                              "result_type": ret, "body": self.expr(fn.body)})
        main = prog.functions[entry_info]
        self.entry = main
        self.stack = []
        body = self.expr(main.body)
        self.has_letrec = bool(functions)              # CORE не принимает пустую группу
        entry = {"op": "letrec", "nid": "$module", "type_params": [], "functions": functions, "body": body} \
            if functions else body
        return {"source_id": entry_info.qname, "revision": "bridge-r30", "result_type": core_type(entry_info.ret),
                "entry": entry, "profile_revision": "core-machine/r06-v1"}

    def expr(self, n) -> dict:
        k = n.k
        if k == B.CONST:
            if isinstance(n.value, Var):
                if n.value.payload is NOPAY and core_type(ty_of(n)) == "ArithmeticError":
                    return {"op": "const", "nid": n.nid, "type": "ArithmeticError", "value": n.value.tag}
                raise NotInSubset("константа-вариант")
            return {"op": "const", "nid": n.nid, "type": core_type(ty_of(n)), "value": n.value}
        if k == B.LOCAL:
            return {"op": "var", "nid": n.nid, "binder": self.stack[len(self.stack) - 1 - n.index], "type_args": []}
        if k == B.GLOBAL:
            if n.fn is getattr(self, "entry", None):
                raise NotInSubset("рекурсия в точку входа")
            return {"op": "var", "nid": n.nid, "binder": n.fn.qname, "type_args": []}
        if k == B.LET:
            value = self.expr(n.value)
            b = self.fresh(n.name if n.name != "_" else "u")
            self.stack.append(b)
            body = self.expr(n.body)
            self.stack.pop()
            return {"op": "let", "nid": n.nid, "binder": b, "type": core_type(ty_of(n.value)), "value": value, "body": body}
        if k == B.LAMBDA:
            t = core_type(ty_of(n))
            names = [self.fresh("p") for _ in range(n.arity)]
            saved = list(self.stack)
            self.stack += names
            body = self.expr(n.body)
            self.stack = saved
            return {"op": "lambda", "nid": n.nid, "params": [{"binder": b, "type": pt} for b, pt in zip(names, t["params"])],
                    "result_type": t["result"], "body": body}
        if k == B.CALL:
            return {"op": "call", "nid": n.nid, "fn": self.expr(n.fn), "args": [self.expr(a) for a in n.args]}
        if k == B.IF:
            return {"op": "if", "nid": n.nid, "condition": self.expr(n.cond), "then": self.expr(n.then),
                    "else": self.expr(n.els)}
        if k == B.PRIM and n.name in PRIMS:
            return {"op": "prim", "nid": n.nid, "name": PRIMS[n.name], "args": [self.expr(a) for a in n.args]}
        if k == B.VARIANT and n.tag in ("Ok", "Err"):
            t = core_type(ty_of(n))
            return {"op": "result", "nid": n.nid, "tag": n.tag, "ok_type": t["ok"], "value": self.expr(n.payload)}
        if k == B.MATCH and set(n.arms) == {"Ok", "Err"} and not n.opaque:
            scrut = self.expr(n.scrutinee)
            out = {"op": "match_result", "nid": n.nid, "value": scrut}
            for tag, key in (("Ok", "ok"), ("Err", "err")):
                bind, body = n.arms[tag]
                b = self.fresh(key)
                if bind:
                    self.stack.append(b)
                out[f"{key}_binder"], out[f"{key}_body"] = b, self.expr(body)
                if bind:
                    self.stack.pop()
            return out
        raise NotInSubset(f"форма {B.FORM_NAMES[k]}" + (f" {n.name}" if k == B.PRIM else ""))


def same_value(ours, core) -> bool:
    if core.tag == "Scalar":
        if isinstance(ours, Var):
            return ours.payload is NOPAY and ours.tag == core.payload
        return type(ours) is type(core.payload) and ours == core.payload
    if core.tag in ("Ok", "Err"):
        return isinstance(ours, Var) and ours.tag == core.tag and same_value(ours.payload, core.payload)
    if core.tag == "Function":
        return isinstance(ours, cek.Clo) or hasattr(ours, "body")
    return False


def compare_runs(engine, prepared, fn, budget, cancel_at, has_letrec: bool) -> str | None:
    """None — совпало; иначе описание расхождения."""
    mine = cek.run(fn.body, None, budget, [], cancel_at)
    extra = 1 if has_letrec else 0                       # MCH-11: связывание группы модуля бесплатно
    core = engine.run(prepared, budget + extra, cancel_at=None if cancel_at is None else cancel_at + extra)
    trace = [(RENAME.get(e.rule, e.rule), e.node_id) for e in core.trace]
    if has_letrec:
        if not trace or trace[0][0] != "LETREC":
            return "в трассе CORE нет LETREC модуля"
        trace = trace[1:]
    if mine.termination != core.termination or mine.code != core.code:
        return f"исход {mine.termination}/{mine.code} против {core.termination}/{core.code}"
    if mine.trace != trace:
        k = next((i for i, (a, b) in enumerate(zip(mine.trace, trace)) if a != b), min(len(mine.trace), len(trace)))
        return f"трасса расходится с шага {k + 1}: {mine.trace[k:k + 2]} против {trace[k:k + 2]}"
    if mine.termination == "RETURNED" and not same_value(mine.value, core.value):
        return f"значение {mine.value!r} против {engine.observe_value(core.value)}"
    return None


def bridge(files, entry: str, engine, matrix: bool = True):
    """(статус, сведения): PASS, FAIL или SKIP (не подмножество CORE)."""
    project, prog, pre = prepare(files)
    if pre is not None:
        return "SKIP", "не проходит проверку"
    info, pre = find_entry(project, entry)
    if pre is not None:
        return "SKIP", "нет точки входа"
    try:
        tr = Translator()
        core_prog = tr.program(prog, info)
        prepared = engine.prepare(engine.decode_program(core_prog))
    except NotInSubset as e:
        return "SKIP", str(e)
    except engine.CoreError as e:
        return "FAIL", f"CORE отвергла перевод: {e}"
    fn = prog.functions[info]
    extra = 1 if tr.has_letrec else 0
    oracle = engine.run(prepared, engine.MAX_BUDGET)    # длину и завершимость решает оракул, а не проверяемая машина
    if oracle.termination != "RETURNED":
        return "SKIP", f"оракул CORE не завершает программу в пределах {engine.MAX_BUDGET} шагов ({oracle.code})"
    n = oracle.steps - extra
    points = [(engine.MAX_BUDGET - extra, None)]
    if matrix:
        points += [(b, c) for b in range(0, n + 2) for c in (None, 0, b - 1, b, n // 2, n) if c is None or 0 <= c <= n + 1]
    for budget, cancel in dict.fromkeys(points):
        bad = compare_runs(engine, prepared, fn, budget, cancel, tr.has_letrec)
        if bad:
            return "FAIL", f"бюджет {budget}, отмена {cancel}: {bad}"
    return "PASS", f"{n} шагов, {len(points)} точек матрицы"


# ------------------------------------------------------------ генератор программ подмножества CORE
class Gen:
    """Типизированный генератор подмножества CORE-0.1 (ревью m3, H4).

    Порождает: функции модуля с двумя параметрами и рекурсией (в том числе взаимной) по убывающему счётчику,
    фабрики замыканий, лямбды с 0–2 параметрами, вызванные на месте и в другом окружении, затенение имён
    из малого набора, ветви и let с `_`, Bool, Result с примитивами i64."""

    POOL = ["a", "b", "c", "x", "y"]
    ANN = {"I": "Int64", "B": "Bool", "R": "Result<Int64, i64.ArithmeticError>", "F0": "fn() -> Int64",
           "F1": "fn(Int64) -> Int64", "F2": "fn(Int64, Int64) -> Int64"}

    def __init__(self, rnd):
        self.rnd = rnd

    @staticmethod
    def visible(env, ty):
        seen, out = set(), []
        for name, t in reversed(env):
            if name not in seen:
                seen.add(name)
                if t == ty:
                    out.append(name)
        return out

    def name(self):
        return self.rnd.choice(self.POOL)

    def call_args(self, k, env, depth, ctx):
        return ", ".join(self.expr("I", env, depth - 1, ctx) for _ in range(k))

    def expr(self, ty, env, depth, ctx, scrutinee=False) -> str:
        r, leaf = self.rnd, depth <= 0
        vs = self.visible(env, ty)
        if ty == "I":
            opts = ["lit"] + (["var", "var", "var"] if vs else [])
            if not leaf:
                opts += ["match", "if", "let", "lam0", "lam1", "lam2"]
                opts += ["fcall", "fcall", "fcall"] * bool(self.visible(env, "F1") or self.visible(env, "F2")
                                                         or self.visible(env, "F0"))
                opts += ["mod"] * bool(ctx.get("m")) + ["mk", "mk"] * bool(ctx.get("mk"))
            o = r.choice(opts)
            if o == "lit":
                return str(r.choice([0, 1, 2, 7, -3, 9223372036854775807, -9223372036854775808]))
            if o == "var":
                return r.choice(vs)
            if o == "match":
                ok = self.name()
                er = "_" if r.random() < 0.5 else self.name()
                err_env = env + ([(er, "E")] if er != "_" else [])
                return (f"match {self.expr('R', env, depth - 1, ctx, scrutinee=True)} {{ Ok({ok}) => "
                        f"{self.expr('I', env + [(ok, 'I')], depth - 1, ctx)}, Err({er}) => "
                        f"{self.expr('I', err_env, depth - 1, ctx)} }}")
            if o == "if":
                return (f"if {self.expr('B', env, depth - 1, ctx)} {{ {self.expr('I', env, depth - 1, ctx)} }} "
                        f"else {{ {self.expr('I', env, depth - 1, ctx)} }}")
            if o == "let":
                t = r.choice(["I", "I", "B", "R", "F1", "F1", "F2", "F2", "F0"])
                v = self.name()
                skip = f"let _ = {self.expr('I', env, depth - 1, ctx)}; " if r.random() < 0.3 else ""
                return (f"{{ let {v}: {self.ANN[t]} = {self.expr(t, env, depth - 1, ctx)}; {skip}"
                        f"{self.expr('I', env + [(v, t)], depth - 1, ctx)} }}")
            if o in ("lam0", "lam1", "lam2"):
                k = int(o[-1])
                ps = [self.name() for _ in range(k)]
                if len(set(ps)) < k:
                    ps = self.POOL[:k]
                sig = ", ".join(f"{p}: Int64" for p in ps)
                body = self.expr("I", env + [(p, "I") for p in ps], depth - 1, ctx)
                return f"(fn({sig}) => {body})({self.call_args(k, env, depth, ctx)})"
            if o == "fcall":
                kinds = [t for t in ("F0", "F1", "F2") if self.visible(env, t)]
                t = r.choice(kinds)
                return f"{r.choice(self.visible(env, t))}({self.call_args(int(t[1]), env, depth, ctx)})"
            if o == "mod":
                f = r.choice(ctx["fns"])
                return f"{f}({ctx['m']}, {self.expr('I', env, depth - 1, ctx)})"
            return f"{r.choice(ctx['mk'])}({self.expr('I', env, depth - 1, ctx)})({self.expr('I', env, depth - 1, ctx)})"
        if ty == "B":
            opts = ["lit"] + (["var"] if vs else []) + ([] if leaf else ["cmp", "cmp", "if"])
            o = r.choice(opts)
            if o == "lit":
                return r.choice(["true", "false"])
            if o == "var":
                return r.choice(vs)
            if o == "cmp":
                return f"i64.{r.choice(['eq', 'lt'])}({self.expr('I', env, depth - 1, ctx)}, {self.expr('I', env, depth - 1, ctx)})"
            return (f"if {self.expr('B', env, depth - 1, ctx)} {{ {self.expr('B', env, depth - 1, ctx)} }} "
                    f"else {{ {self.expr('B', env, depth - 1, ctx)} }}")
        if ty == "R":
            # в позиции match тип ошибки у Ok/Err не выводится (TYPES-0.1 §5) — там только примитив или имя
            opts = ["prim", "prim"] + ([] if scrutinee else ["ok", "err"]) + (["var"] if vs else [])
            o = r.choice(opts)
            if o == "var":
                return r.choice(vs)
            if o == "ok":
                return f"Ok({self.expr('I', env, depth - 1, ctx)})"
            if o == "err":
                return f"Err(i64.ArithmeticError.{r.choice(['Overflow', 'DivisionByZero'])})"
            return f"i64.{r.choice(['add', 'sub', 'div', 'rem'])}({self.expr('I', env, depth - 1, ctx)}, {self.expr('I', env, depth - 1, ctx)})"
        if ty in ("F0", "F1", "F2"):
            k = int(ty[1])
            if vs and r.random() < 0.4:
                return r.choice(vs)
            if ty == "F1" and ctx.get("mk") and r.random() < 0.3:
                return f"{r.choice(ctx['mk'])}({self.expr('I', env, depth - 1, ctx)})"
            ps = self.POOL[:k] if k else []
            sig = ", ".join(f"{p}: Int64" for p in ps)
            return f"fn({sig}) => {self.expr('I', env + [(p, 'I') for p in ps], depth - 1, ctx)}"
        raise AssertionError(ty)

    def program(self) -> str:
        r = self.rnd
        nf, nmk = r.randint(1, 3), r.randint(0, 2)
        fns, mks = [f"f{i}" for i in range(nf)], [f"mk{i}" for i in range(nmk)]
        out = ['@id("aaaaaa")', "module main", "", "use std.i64", ""]
        for j, mk in enumerate(mks):
            body = self.expr("I", [("n", "I"), ("x", "I")], 2, {})
            out += [f'@id("k{j:05d}")', f"fn {mk}(n: Int64) -> fn(Int64) -> Int64 {{", f"  fn(x: Int64) => {body}", "}", ""]
        for i, f in enumerate(fns):
            env = [("n", "I"), ("a", "I")]
            base = self.expr("I", env, 2, {"mk": mks})
            rec = self.expr("I", env + [("m", "I")], 3, {"m": "m", "fns": fns, "mk": mks})
            out += [f'@id("f{i:05d}")', f"fn {f}(n: Int64, a: Int64) -> Int64 {{",
                    f"  if i64.lt(n, 1) {{ {base} }} else {{ match i64.sub(n, 1) {{ Ok(m) => {rec}, Err(_) => 0 }} }}", "}", ""]
        ret = r.choice(["I", "I", "B", "R"])
        call = f"{r.choice(fns)}({r.randint(0, 3)}, {r.choice([0, 1, 5])})"
        body = {"I": call, "B": f"i64.lt({call}, 3)", "R": f"i64.add({call}, 1)"}[ret]
        out += ['@id("mmmmmm")', f"pub fn main() -> {self.ANN[ret]} {{", f"  {body}", "}", ""]
        return "\n".join(out)


def corpus_programs():
    for cf in sorted((ROOT / "conformance" / "cases").rglob("case.json")):
        c = json.loads(cf.read_text(encoding="utf-8"))
        if c["expect"].get("phase") != "run":
            continue
        files = [(f, (cf.parent / f).read_bytes()) for f in c.get("files", [])]
        yield c["id"], files, c.get("run", {}).get("entry", "main.main")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--generated", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20261024)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    engine = load_engine()
    stats = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    fails = []
    for cid, files, entry in corpus_programs():
        st, info = bridge(files, entry, engine)
        stats[st] += 1
        if st == "FAIL":
            fails.append((cid, info))
    gstats = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    g = Gen(random.Random(a.seed))
    for k in range(a.generated):
        src = g.program()
        st, info = bridge([("main.bag", src.encode("utf-8"))], "main.main", engine, matrix=(k % 3 == 0))
        gstats[st] += 1
        if st == "FAIL":
            fails.append((f"generated#{k}", info + "\n" + src))
    report = {"corpus": stats, "generated": gstats, "failures": fails[:5]}
    print(json.dumps(report, ensure_ascii=False, indent=None if a.json else 2))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
