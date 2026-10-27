"""Подкоманды хоста (spec/runtime/host.md §9): `bag run --db`, `bag status`, `bag events deliver`, `bag replay`,
`bag migrate plan|apply|abort`, `bag seed`, `bag state`. Вывод — JSON-наблюдение одной строкой или с отступами."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def emit(obj, a) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=None if getattr(a, "json", False) else 2))


def load_program(root: str):
    """Проверенная программа или наблюдение PRELAUNCH."""
    from bagaev_ref.cli import project_files
    from bagaev_ref.machine.runner import prepare
    from bagaev_ref.host.driver import Program
    files = project_files(root)
    if files is None:
        return None, {"outcome": "PRELAUNCH", "error": f"корень проекта {root} не каталог"}
    project, prog, pre = prepare(files)
    return (None, pre) if pre is not None else (Program(project, prog), None)


def json_arg(text: str | None, default):
    if text is None:
        return default
    if text.startswith("@"):
        text = Path(text[1:]).read_text(encoding="utf-8")
    return json.loads(text)


def policy_arg(a, root: str | None):
    from bagaev_ref.host.driver import load_policy
    if getattr(a, "policy", None):
        return json.loads(Path(a.policy).read_text(encoding="utf-8"))
    return load_policy(Path(root)) if root else None


def host_run(a: argparse.Namespace) -> int:
    """`bag run ROOT ENTRY --db`: command — транзакция с квитанцией, query — чтение снимка."""
    from bagaev_ref.host import driver as D
    from bagaev_ref.host.store import Store
    program, pre = load_program(a.root)
    if pre is not None:
        emit(dict(pre, phase="host"), a)
        return 1
    info = program.entry(a.entry)
    st = Store(a.db)
    args = json_arg(a.args, [])
    policy = policy_arg(a, a.root)
    if info is not None and info.kind == "query":
        obs = D.run_query(st, program, a.entry, args, a.caller, policy, a.fuel)
        ok = obs["outcome"] == "RETURNED"
    else:
        obs = D.run_command(st, program, a.entry, args, {"namespace": a.namespace or "", "key": a.key or ""},
                            a.caller, a.expected_state_version, policy, a.fuel)
        ok = obs["outcome"] in ("COMMITTED", "ABORTED") and obs.get("final", False)
    emit(dict(obs, phase="host"), a)
    return 0 if ok else 1


def cmd_status(a) -> int:
    from bagaev_ref.host import driver as D
    from bagaev_ref.host.store import Store
    if a.handler is not None:
        if a.seq is None:
            return usage_error("--handler требует --seq")
        emit(D.event_status(Store(a.db), a.handler, a.seq), a)
        return 0
    if a.namespace is None or a.key is None:
        return usage_error("нужны --namespace и --key (квитанция команды) или --handler и --seq (обработки)")
    program = None
    if a.entry is not None:
        program, pre = load_program(a.root or ".")
        if pre is not None:
            emit(pre, a)
            return 1
    emit(D.status(Store(a.db), {"namespace": a.namespace, "key": a.key}, program, a.entry, json_arg(a.args, [])), a)
    return 0


def cmd_deliver(a) -> int:
    from bagaev_ref.host import driver as D
    from bagaev_ref.host.store import Store
    program, pre = load_program(a.root)
    if pre is not None:
        emit(pre, a)
        return 1
    out = D.deliver(Store(a.db), program, a.handler, a.seq, a.fuel, policy_arg(a, a.root))
    emit({"outcome": "DELIVERED", "deliveries": out}, a)
    return 0 if all(r["outcome"] == "COMMITTED" for r in out) else 1


def cmd_replay(a) -> int:
    from bagaev_ref.host import driver as D
    from bagaev_ref.host.store import Store
    program, pre = load_program(a.root)
    if pre is not None:
        emit(pre, a)
        return 1
    obs = D.replay(Store(a.db), program, a.ref, a.fuel)
    emit(obs, a)
    return 0 if obs["outcome"] == "REPLAY_MATCH" else 1


def cmd_migrate(a) -> int:
    from bagaev_ref.host import migrate as M
    from bagaev_ref.host.store import Store
    st = Store(a.db)
    if a.action == "abort":
        emit(M.abort(st), a)
        return 0
    program, pre = load_program(a.root)
    if pre is not None:
        emit(pre, a)
        return 1
    obs = M.plan(st, program) if a.action == "plan" else M.apply(st, program, a.fuel)
    emit(obs, a)
    return 0 if obs["outcome"] in ("PLANNED", "APPLIED", "UP_TO_DATE") else 1


def cmd_seed(a) -> int:
    from bagaev_ref.host import driver as D
    from bagaev_ref.host.store import Store
    program, pre = load_program(a.root)
    if pre is not None:
        emit(pre, a)
        return 1
    obs = D.seed(Store(a.db), program, a.table, json_arg(a.rows, []))
    emit(obs, a)
    return 0 if obs["outcome"] == "COMMITTED" else 1


def cmd_state(a) -> int:
    from bagaev_ref.host import driver as D
    from bagaev_ref.host.store import Store
    program, pre = load_program(a.root)
    if pre is not None:
        emit(pre, a)
        return 1
    emit(D.dump(Store(a.db), program), a)
    return 0


def register(sub, fuel_default: int) -> None:
    def common(p, root=True):
        if root:
            p.add_argument("root")
        p.add_argument("--db", required=True, help="файл SQLite хранилища")
        p.add_argument("--json", action="store_true", help="одной строкой")

    sp = sub.add_parser("status", help="квитанция команды по KeyRef или обработки события: RESULT или ABSENT_AT_READ (HST-07)")
    common(sp, root=False)
    sp.add_argument("--namespace")
    sp.add_argument("--key")
    sp.add_argument("--handler", help="квитанция обработки: обработчик (<модуль>.<имя>)")
    sp.add_argument("--seq", type=int, help="квитанция обработки: seq события")
    sp.add_argument("root", nargs="?", help="корень проекта: нужен вместе с --entry")
    sp.add_argument("--entry", help="сверить квитанцию с запросом: точка входа")
    sp.add_argument("--args", help="сверить квитанцию с запросом: аргументы (JSON или @файл)")
    sp.set_defaults(fn=cmd_status)

    ep = sub.add_parser("events", help="события outbox")
    esub = ep.add_subparsers(dest="events_command", required=True)
    dp = esub.add_parser("deliver", help="доставить недоставленные события обработчикам (HST-11)")
    common(dp)
    dp.add_argument("--handler", help="только этот обработчик (<модуль>.<имя>)")
    dp.add_argument("--seq", type=int, help="только это событие outbox")
    dp.add_argument("--fuel", type=int, default=fuel_default)
    dp.add_argument("--policy", help="файл политики хоста (по умолчанию <корень>/host-policy.json)")
    dp.set_defaults(fn=cmd_deliver)

    rp = sub.add_parser("replay", help="перепроверить исполнение по журналу без доступа к таблицам (HST-13)")
    common(rp)
    rp.add_argument("--ref", required=True, help="<namespace>:<key> команды или <обработчик>:<seq>")
    rp.add_argument("--fuel", type=int, default=fuel_default)
    rp.set_defaults(fn=cmd_replay)

    mp = sub.add_parser("migrate", help="миграция хранилища при остановленных писателях (HST-14, HST-15)")
    mp.add_argument("action", choices=["plan", "apply", "abort"])
    mp.add_argument("root", nargs="?")
    mp.add_argument("--db", required=True)
    mp.add_argument("--json", action="store_true")
    mp.add_argument("--fuel", type=int, default=fuel_default)
    mp.set_defaults(fn=lambda a: cmd_migrate(a) if a.root or a.action == "abort" else usage(mp))

    sd = sub.add_parser("seed", help="служебная загрузка строк таблицы (фикстуры), одна транзакция")
    common(sd)
    sd.add_argument("--table", required=True, help="<модуль>.<store>.<таблица>")
    sd.add_argument("--rows", required=True, help="JSON [[ключ, значение], …] в форме CANON-11 или @файл")
    sd.set_defaults(fn=cmd_seed)

    tp = sub.add_parser("state", help="состояние хранилища: таблицы, outbox, inbox, StateVersion, epoch")
    common(tp)
    tp.set_defaults(fn=cmd_state)


def usage_error(msg: str) -> int:
    print(json.dumps({"error": msg}, ensure_ascii=False), file=sys.stderr)
    return 2


def usage(p) -> int:
    p.print_usage(sys.stderr)
    return 2
