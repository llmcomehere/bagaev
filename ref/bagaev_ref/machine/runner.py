"""`bag run` и `bag test` (spec/runtime/machine.md §6): проверка, понижение, запуск, наблюдение (OUT-01)."""
from __future__ import annotations

from bagaev_ref.diag import canonical_order, make
from bagaev_ref.ir.lower import lower
from bagaev_ref.machine import cek
from bagaev_ref.machine.observe import observe
from bagaev_ref.sema import types as T
from bagaev_ref.sema.project import FnInfo

DEFAULT_FUEL = 10_000_000


def prepare(files):
    """Возвращает (project, program, None) или (None, None, наблюдение PRELAUNCH)."""
    from bagaev_ref.cli import parse_observation
    from bagaev_ref.sema.check import check_project_full
    obs = parse_observation(files)
    if obs["outcome"] != "ACCEPTED":
        return None, None, obs
    project, diags = check_project_full(files)
    if diags:
        return None, None, {"outcome": "PRELAUNCH", "diagnostics": [d.to_json() for d in canonical_order(diags)]}
    return project, lower(project), None


def entry_diag(code: str, info=None, **data) -> dict:
    """Диагностика точки входа: у существующей функции — диапазон её имени, у неизвестной — без места."""
    if info is not None:
        nm = info.decl.name
        d = make(code, info.module.file, nm.start, nm.end, **data)
    else:
        d = make(code, "", 0, 0, **data)
    return {"outcome": "PRELAUNCH", "diagnostics": [d.to_json()]}


def find_entry(project, entry: str):
    """SURF-09: `<модуль>.<имя>` — pub fn без параметров с пустым рядом (EFF-08)."""
    mod, _, name = entry.rpartition(".")
    m = project.modules.get(mod)
    info = m.values.get(name) if m is not None and not m.is_std else None
    if not isinstance(info, FnInfo) or info.kind != "fn" or not info.pub:
        return None, entry_diag("UNKNOWN_ENTRYPOINT", name=entry)
    if info.params or info.tparams or info.eparams:     # тип результата должен быть известен до запуска
        return None, entry_diag("ENTRYPOINT_SIGNATURE", info, name=entry, params=len(info.params),
                                generics=len(info.tparams) + len(info.eparams))
    if info.row.atoms:
        atoms = sorted(T.show_atom(a) for a in info.row.atoms)
        return None, entry_diag("HOST_EFFECT_OUTSIDE_TRANSACTION", info, name=entry, atoms=atoms)
    return info, None


def observation(ex: cek.Execution, ret_type, level_l1: bool) -> dict:
    out = {"outcome": ex.termination}
    if ex.termination == "RETURNED":
        out["value"] = observe(ex.value, ret_type)
    else:
        out["code"] = ex.code
    if ex.termination == "FAULT":
        f, s, e = ex.site
        out["site"] = {"file": f, "span": [s, e]}
        if ex.data:
            out["data"] = ex.data
    if ex.termination == "IMPLEMENTATION_STOP" and ex.data:
        out["detail"] = ex.data.get("detail")
    out["effects"] = []
    if level_l1:
        out["steps"] = ex.steps
        out["trace_l1"] = [r for r, _ in ex.trace]        # MCH-09: правила; nid — внутреннее дело реализации
    return out


def run_entry(files, entry: str, fuel: int = DEFAULT_FUEL, l1: bool = False, cancel_at: int | None = None) -> dict:
    project, prog, pre = prepare(files)
    if pre is None:
        info, pre = find_entry(project, entry)
    if pre is not None:
        return dict(pre, effects=[])                    # шагов не было — эффектов нет
    fn = prog.functions[info]
    try:
        ex = cek.run(fn.body, None, fuel, [] if l1 else None, cancel_at)
        return observation(ex, info.ret, l1)
    except RecursionError:                              # глубокое значение: сравнение или наблюдение (MCH-02)
        return {"outcome": "IMPLEMENTATION_STOP", "code": "RESOURCE_LIMIT", "effects": [],
                "detail": "превышена глубина значения"}


def run_test_body(project, prog, info, fuel):
    if not info.row.atoms:
        return cek.run(prog.functions[info].body, None, fuel)
    from bagaev_ref.host.driver import Program, TxHost
    from bagaev_ref.host.store import Store
    store = Store(":memory:")
    try:
        store.bind(project)
        store.db.execute("BEGIN IMMEDIATE")
        return cek.run(prog.functions[info].body, None, fuel, host=TxHost(store, Program(project, prog), info.row.atoms))
    finally:
        store.close()


def run_tests(files, fuel: int = DEFAULT_FUEL) -> dict:
    """`bag test`: каждое объявление test исполняется отдельно (SURF-14). Тест с эффектами хранилища получает
    отдельное пустое хранилище в памяти (HST-18)."""
    project, prog, pre = prepare(files)
    if pre is not None:
        return pre
    results = []
    for m in project.user:
        for info in m.values.values():
            if not isinstance(info, FnInfo) or info.kind != "test":
                continue
            name = f"{m.name}.{info.name}"
            try:
                ex = run_test_body(project, prog, info, fuel)
            except RecursionError:
                results.append({"test": name, "status": "ERROR", "code": "RESOURCE_LIMIT"})
                continue
            if ex.termination == "RETURNED":
                results.append({"test": name, "status": "PASS", "steps": ex.steps})
            elif ex.termination == "FAULT":
                f, s, e = ex.site
                r = {"test": name, "status": "FAIL", "code": ex.code, "site": {"file": f, "span": [s, e]}}
                if ex.data:
                    r["data"] = ex.data
                results.append(r)
            else:
                results.append({"test": name, "status": "ERROR", "code": ex.code})
    counts = {s: sum(1 for r in results if r["status"] == s) for s in ("PASS", "FAIL", "ERROR", "SKIP")}
    return {"outcome": "TESTED", "counts": counts, "tests": results}
