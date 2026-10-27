#!/usr/bin/env python3
"""Мутационная проверка чувствительности (ревью m3, H3–H5): заведомая ошибка в машине или понижении
должна давать FAIL моста core01 или корпуса run. Файлы репозитория не меняются: мутант — копия модуля в памяти.

  python3 conformance/bridges/mutants.py [--generated N]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ref"))

import bagaev_ref.ir.lower as lower_mod  # noqa: E402
import bagaev_ref.machine.cek as cek_mod  # noqa: E402
import bagaev_ref.machine.runner as runner_mod  # noqa: E402
import bagaev_ref.machine.values as values_mod  # noqa: E402

# (имя, модуль, заменяемый фрагмент, замена)
MUTANTS = [
    ("args_reversed", cek_mod, "for a in done:\n                            env = (a, env)",
     "for a in reversed(done):\n                            env = (a, env)"),
    ("lambda_dynamic_env", cek_mod, "env = clo.env\n                        for a in done:",
     "env = fr[2]\n                        for a in done:"),
    ("match_always_binds", cek_mod, "env = (payload, fr[2]) if bind else fr[2]", "env = (payload, fr[2])"),
    ("early_budget_stop", cek_mod, "if steps >= budget:", "if steps >= budget or steps == 40:"),
    ("cancel_after_budget", cek_mod,
     "if cancel_at is not None and steps == cancel_at:\n                return Execution(\"SEMANTIC_STOP\", \"CANCELLED\", None, steps, trace)\n"
     "            if steps >= budget:\n                return Execution(\"SEMANTIC_STOP\", \"BUDGET_EXCEEDED\", None, steps, trace)",
     "if steps >= budget:\n                return Execution(\"SEMANTIC_STOP\", \"BUDGET_EXCEEDED\", None, steps, trace)\n"
     "            if cancel_at is not None and steps == cancel_at:\n                return Execution(\"SEMANTIC_STOP\", \"CANCELLED\", None, steps, trace)"),
    ("call_noargs_rk_stale", cek_mod, "node, env, rk, ev, rule = clo.body, clo.env, K, True, \"CALL_BODY\"",
     "node, env, ev, rule = clo.body, clo.env, True, \"CALL_BODY\""),
    ("let_restore_rk_missing", cek_mod, "env, rk = (val, fr[2]), fr[3]", "env = (val, fr[2])"),
    ("if_branches_swapped", cek_mod, "if val:\n                        node, rule = fnode.then", "if not val:\n                        node, rule = fnode.then"),
    ("lower_shadow_first", lower_mod, "max(k for k, n in enumerate(self.scope) if n == name)",
     "min(k for k, n in enumerate(self.scope) if n == name)"),
    ("key_bool_reversed", values_mod, "return (0, int(v))", "return (0, -int(v))"),
]


def mutate(module, old: str, new: str):
    src = Path(module.__file__).read_text(encoding="utf-8")
    assert src.count(old) == 1, (module.__name__, old[:50])
    m = types.ModuleType(module.__name__)
    m.__file__ = module.__file__
    exec(compile(src.replace(old, new), module.__file__, "exec"), m.__dict__)
    return m


def load_bridge():
    spec = importlib.util.spec_from_file_location("bagaev_core01_mut", ROOT / "conformance" / "bridges" / "core01.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bagaev_core01_mut"] = mod
    spec.loader.exec_module(mod)
    return mod


def corpus_fails(run_entry) -> int:
    """Число случаев фазы run, которые мутант проваливает (сравнение как в conformance/run.py)."""
    spec = importlib.util.spec_from_file_location("bagaev_conformance", ROOT / "conformance" / "run.py")
    conf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conf)
    fails = 0
    for cf in sorted((ROOT / "conformance" / "cases").rglob("case.json")):
        c = json.loads(cf.read_text(encoding="utf-8"))
        if c["expect"].get("phase") != "run":
            continue
        r = c.get("run", {})
        files = [(f, (cf.parent / f).read_bytes()) for f in c["files"]]
        try:
            obs = dict({"phase": "run"}, **run_entry(files, r.get("entry", "main.main"), r.get("fuel", 10_000_000),
                                                     "L1" in c["levels"], r.get("cancel_at")))
        except Exception:                                # падение мутанта — тоже обнаружение
            fails += 1
            continue
        fails += bool(conf.compare(c["expect"], obs, c["levels"]))
    return fails


def check(generated: int) -> dict:
    out = {}
    for name, module, old, new in MUTANTS:
        mut = mutate(module, old, new)
        saved = {}
        import bagaev_ref.stdlib.prims as prims
        targets = {cek_mod: [(runner_mod, "cek")], lower_mod: [(runner_mod, "lower")], values_mod: []}
        try:
            if module is cek_mod:
                saved[(runner_mod, "cek")] = runner_mod.cek
                runner_mod.cek = mut
            elif module is lower_mod:
                saved[(runner_mod, "lower")] = runner_mod.lower
                runner_mod.lower = mut.lower
            else:
                import bagaev_ref.stdlib.prims as prims
                saved[(prims, "key_of")] = prims.key_of
                prims.key_of = mut.key_of
                saved_prims = dict(prims.PRIMS)
                prims.PRIMS["op.lt@1"] = lambda a, b: mut.key_of(a) < mut.key_of(b)
                prims.PRIMS["op.le@1"] = lambda a, b: mut.key_of(a) <= mut.key_of(b)
                prims.PRIMS["op.gt@1"] = lambda a, b: mut.key_of(a) > mut.key_of(b)
                prims.PRIMS["op.ge@1"] = lambda a, b: mut.key_of(a) >= mut.key_of(b)
            corpus = corpus_fails(runner_mod.run_entry)
            bridge_fail = None
            if module is cek_mod:
                br = load_bridge()
                br.cek = mut
                engine = br.load_engine()
                g = br.Gen(__import__("random").Random(7))
                bridge_fail = 0
                for k in range(generated):
                    try:
                        st, _ = br.bridge([("main.bag", g.program().encode("utf-8"))], "main.main", engine,
                                          matrix=(k % 3 == 0))
                    except Exception:
                        st = "FAIL"
                    bridge_fail += st == "FAIL"
            out[name] = {"corpus_fails": corpus, "bridge_fails": bridge_fail,
                         "caught": corpus > 0 or bool(bridge_fail)}
        finally:
            for (obj, attr), v in saved.items():
                setattr(obj, attr, v)
            if module is values_mod:
                prims.PRIMS.clear()
                prims.PRIMS.update(saved_prims)
        del targets
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generated", type=int, default=30)
    a = ap.parse_args(argv)
    res = check(a.generated)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if all(v["caught"] for v in res.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
