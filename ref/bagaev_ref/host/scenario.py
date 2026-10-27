"""Сценарные случаи conformance для хоста (фазы store, events, migrate; conformance/README.md §Сценарий).

Сценарий — последовательность шагов `run.steps` над одним новым хранилищем. Наблюдение — `value`: список
наблюдений шагов, и `state`: состояние хранилища после последнего шага. Сбой в точке (HST-16) внутри процесса
моделируется исключением: незафиксированная транзакция SQLite теряется так же, как при kill -9.
"""
from __future__ import annotations

import os
import tempfile

from bagaev_ref.host import driver as D, migrate as M
from bagaev_ref.host.store import Store

# Дайджесты привязки и замка, тексты пояснений — не часть наблюдения L2 (HST-14, HST-17).
DROP = {"plan_id", "from_schema", "to_schema", "phase", "lock", "detail"}


def project_program(files, prefix: str, others: set):
    """Файлы программы: каталог prefix; корневая программа ("") — всё, что не лежит в каталогах других версий."""
    from bagaev_ref.machine.runner import prepare
    pre = prefix.rstrip("/") + "/" if prefix else ""
    sub = [(f[len(pre):], b) for f, b in files if f.startswith(pre) and f.endswith(".bag")
           and not (not prefix and f.split("/", 1)[0] in others)]
    project, prog, obs = prepare(sub)
    return (None, obs) if obs is not None else (D.Program(project, prog), None)


def clean(obs):
    if isinstance(obs, dict):
        out = {k: clean(v) for k, v in obs.items() if k not in DROP}
        return {k: v for k, v in out.items() if not (k == "data" and v == {})}
    if isinstance(obs, list):
        return [clean(x) for x in obs]
    return obs


def run_scenario(files, case: dict) -> dict:
    run = case.get("run", {})
    fuel = run.get("fuel", 10_000_000)
    phase = case["expect"]["phase"]
    tmp = tempfile.mkdtemp(prefix="bag-scenario-")
    db = os.path.join(tmp, "store.db")
    programs, out = {}, []
    others = {st.get("program", "") for st in run.get("steps", [])} - {""}
    st = Store(db)
    try:
        for step in run.get("steps", []):
            prefix = step.get("program", "")
            if prefix not in programs:
                programs[prefix] = project_program(files, prefix, others)
            program, pre = programs[prefix]
            if pre is not None:
                return {"phase": phase, "outcome": "PRELAUNCH", "diagnostics": pre.get("diagnostics", []), "value": out}
            D.SIMULATED_CRASH = step.get("crash_at")
            try:
                out.append(clean(execute(st, program, step, fuel)))
            except D.Crashed:
                st.db.close()                            # как kill -9: незафиксированное теряется
                st = Store(db)
                out.append({"outcome": "CRASHED", "at": step["crash_at"]})
            finally:
                D.SIMULATED_CRASH = None
        sp = run.get("state_program", (run.get("steps") or [{}])[-1].get("program", ""))
        last = programs.get(sp) or project_program(files, sp, others)
        state = D.dump(st, last[0]) if last and last[0] is not None else None
        return {"phase": phase, "outcome": "COMPLETED", "value": out, "state": state}
    finally:
        st.close()
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        os.rmdir(tmp)


def execute(st: Store, program, step: dict, fuel: int):
    op = step["op"]
    policy = step.get("policy")
    if op == "seed":
        return D.seed(st, program, step["table"], step["rows"])
    if op == "command":
        return D.run_command(st, program, step["entry"], step.get("args", []),
                             {"namespace": step.get("namespace", ""), "key": step.get("key", "")},
                             step.get("caller", "anonymous"), step.get("expected_state_version"), policy, fuel)
    if op == "query":
        return D.run_query(st, program, step["entry"], step.get("args", []), step.get("caller", "anonymous"), policy, fuel)
    if op == "status":
        return D.status(st, {"namespace": step["namespace"], "key": step["key"]}, program, step.get("entry"),
                        step.get("args"))
    if op == "deliver":
        return {"outcome": "DELIVERED",
                "deliveries": D.deliver(st, program, step.get("handler"), step.get("seq"), fuel, policy)}
    if op == "replay":
        return D.replay(st, program, step["ref"], fuel)
    if op == "migrate":
        act = step.get("action", "apply")
        return M.plan(st, program) if act == "plan" else M.abort(st) if act == "abort" else M.apply(st, program, fuel)
    if op == "lock":                                     # имитация чужой миграции: писатель видит замок
        st.set_meta("writer_lock", step.get("owner", "other"))
        return {"outcome": "LOCKED"}
    raise ValueError(f"неизвестный шаг {op}")
