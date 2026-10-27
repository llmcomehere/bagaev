"""Командная строка эталона: `python3 -m bagaev_ref <команда>` (или `bag` после `pip install -e ref`).

Есть `version`, `parse`, `check`, `fmt` и контракт `conformance-exec`. Команды run/test (Ф3)
и остальные добавляются по фазам плана.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
from pathlib import Path

from bagaev_ref import __version__


def cmd_version(_: argparse.Namespace) -> int:
    print(json.dumps({"impl": "bagaev-ref", "version": __version__}, ensure_ascii=False))
    return 0


SUPPORTED_PHASES = {"parse", "fmt", "check", "run"}   # фазы, которые эталон уже исполняет


def parse_observation(files: list[tuple[str, bytes]]) -> dict:
    """Наблюдение фазы parse (OUT-08): ACCEPTED или PRELAUNCH со всеми диагностиками в порядке SURF-58."""
    from bagaev_ref.diag import canonical_order
    from bagaev_ref.syntax.parser import parse
    diags = []
    for name, data in files:
        _, _, d = parse(data, name)
        diags += d
    if diags:
        return {"phase": "parse", "outcome": "PRELAUNCH", "diagnostics": [x.to_json() for x in canonical_order(diags)]}
    return {"phase": "parse", "outcome": "ACCEPTED"}


def check_observation(files: list[tuple[str, bytes]]) -> dict:
    """Наблюдение фазы check (checking.md §1): сначала lex/parse всех файлов, затем имена, типы и эффекты."""
    from bagaev_ref.diag import canonical_order
    from bagaev_ref.sema.check import check_project
    obs = parse_observation(files)
    if obs["outcome"] != "ACCEPTED":
        return dict(obs, phase="check")
    diags = check_project(files)
    if diags:
        return {"phase": "check", "outcome": "PRELAUNCH", "diagnostics": [d.to_json() for d in canonical_order(diags)]}
    return {"phase": "check", "outcome": "ACCEPTED"}


def cmd_check(a: argparse.Namespace) -> int:
    root = Path(a.root)
    if not root.is_dir():
        print(json.dumps({"error": f"корень проекта {a.root} не каталог"}, ensure_ascii=False), file=sys.stderr)
        return 2
    files = [(f.relative_to(root).as_posix(), f.read_bytes()) for f in bag_files([a.root])]
    obs = check_observation(files)
    if a.first and obs.get("diagnostics"):
        obs["diagnostics"] = obs["diagnostics"][:1]
    print(json.dumps(obs, ensure_ascii=False, indent=None if a.json else 2))
    return 0 if obs["outcome"] == "ACCEPTED" else 1


def project_files(root_arg: str):
    root = Path(root_arg)
    if not root.is_dir():
        print(json.dumps({"error": f"корень проекта {root_arg} не каталог"}, ensure_ascii=False), file=sys.stderr)
        return None
    return [(f.relative_to(root).as_posix(), f.read_bytes()) for f in bag_files([root_arg])]


def cmd_run(a: argparse.Namespace) -> int:
    from bagaev_ref.machine.runner import run_entry
    if a.db is not None:                                # command/query с хранилищем (spec/runtime/host.md)
        from bagaev_ref.host.cli import host_run
        return host_run(a)
    files = project_files(a.root)
    if files is None:
        return 2
    if a.fuel < 0:
        print(json.dumps({"error": "--fuel не может быть отрицательным"}, ensure_ascii=False), file=sys.stderr)
        return 2
    obs = dict(run_entry(files, a.entry, a.fuel, a.trace), phase="run")
    print(json.dumps(obs, ensure_ascii=False, indent=None if a.json else 2))
    return 0 if obs["outcome"] == "RETURNED" else 1


def cmd_test(a: argparse.Namespace) -> int:
    from bagaev_ref.machine.runner import run_tests
    files = project_files(a.root)
    if files is None:
        return 2
    obs = run_tests(files, a.fuel)
    print(json.dumps(obs, ensure_ascii=False, indent=None if a.json else 2))
    bad = obs.get("counts", {}).get("FAIL", 0) + obs.get("counts", {}).get("ERROR", 0)
    return 0 if obs["outcome"] == "TESTED" and not bad else 1


def fmt_observation(files: list[tuple[str, bytes]]) -> dict:
    """Наблюдение фазы fmt: FORMATTED с каноническим текстом каждого файла или PRELAUNCH (FMT-15)."""
    from bagaev_ref.syntax.printer import FormatError, format_source
    out = {}
    for name, data in files:
        try:
            out[name] = format_source(data, name)
        except FormatError:
            return dict(parse_observation(files), phase="fmt")
    return {"phase": "fmt", "outcome": "FORMATTED", "value": out}


def cmd_parse(a: argparse.Namespace) -> int:
    files = [(Path(f).name if a.basename else f, Path(f).read_bytes()) for f in a.files]
    obs = parse_observation(files)
    print(json.dumps(obs, ensure_ascii=False, indent=None if a.json else 2))
    return 0 if obs["outcome"] == "ACCEPTED" else 1


def bag_files(paths: list[str]) -> list[Path]:
    out = []
    for p in map(Path, paths):
        out += sorted(p.rglob("*.bag")) if p.is_dir() else [p]
    return out


def cmd_fmt(a: argparse.Namespace) -> int:
    """FORMAT-1: переписать файлы в каноническом виде; --check только сообщает; --assign-ids — FMT-16."""
    from bagaev_ref.diag import canonical_order
    from bagaev_ref.syntax.printer import FormatError, ID_ATTR, assign_ids, format_source
    files = bag_files(a.paths)
    taken: set = set()
    if a.assign_ids:
        for f in files:
            taken |= set(ID_ATTR.findall(f.read_bytes().decode("utf-8", errors="replace")))
    status, report = 0, []
    for f in files:
        data = f.read_bytes()
        try:
            if a.assign_ids:
                data = assign_ids(data, f.name, taken)
            new = format_source(data, f.name).encode("utf-8")
        except FormatError as e:
            report.append({"file": str(f), "status": "error",
                           "diagnostics": [d.to_json() for d in canonical_order(e.diags)]})
            status = 1
            continue
        if new == f.read_bytes():
            continue
        if a.check:
            report.append({"file": str(f), "status": "unformatted"})
            status = 1
        else:
            f.write_bytes(new)
            report.append({"file": str(f), "status": "formatted"})
    print(json.dumps({"files": len(files), "changed": report}, ensure_ascii=False, indent=2))
    return status


def cmd_conformance_exec(a: argparse.Namespace) -> int:
    case_dir = Path(a.case)
    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    phase = case["expect"]["phase"]
    files = [(f, (case_dir / f).read_bytes()) for f in case.get("files", [])]
    if phase == "parse":
        obs = parse_observation(files)
    elif phase == "fmt":
        obs = fmt_observation(files)
    elif phase == "check":
        obs = check_observation(files)
    elif phase == "run":
        from bagaev_ref.machine.runner import DEFAULT_FUEL, run_entry
        r = case.get("run", {})
        obs = dict(run_entry(files, r.get("entry", "main.main"), r.get("fuel", DEFAULT_FUEL),
                             "L1" in case.get("levels", []), r.get("cancel_at")), phase="run")
    elif phase in ("edit", "accept", "protocol"):
        from bagaev_ref.protocol.conformance import run_change_case
        obs = run_change_case(files, case)
    elif phase in ("graph", "impact", "context"):
        from bagaev_ref.links.conformance import run_links_case
        obs = run_links_case(files, case)
    elif phase in ("store", "events", "migrate"):
        from bagaev_ref.host.scenario import run_scenario
        obs = run_scenario(files, case)
    else:
        # Фаза ещё не реализована: честный защитный исход с названием фазы, а не угаданное поведение.
        obs = {"phase": phase, "outcome": "IMPLEMENTATION_STOP", "code": "NOT_IMPLEMENTED"}
    print(json.dumps(obs, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bag", description="эталонная реализация bagaev")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("version", help="версия эталона").set_defaults(fn=cmd_version)
    pp = sub.add_parser("parse", help="лексика и разбор файлов; JSON-наблюдение фазы parse")
    pp.add_argument("files", nargs="+")
    pp.add_argument("--json", action="store_true", help="одной строкой")
    pp.add_argument("--basename", action="store_true", help="в диагностиках — только имя файла")
    pp.set_defaults(fn=cmd_parse)
    cp = sub.add_parser("check", help="имена, типы и эффекты проекта (spec/language/checking.md)")
    cp.add_argument("root", help="корень проекта: файл <корень>/a/b.bag объявляет module a.b")
    cp.add_argument("--json", action="store_true", help="одной строкой")
    cp.add_argument("--first", action="store_true", help="только каноническая первая диагностика (SURF-58)")
    cp.set_defaults(fn=cmd_check)
    from bagaev_ref.machine.runner import DEFAULT_FUEL
    rp = sub.add_parser("run", help="исполнить pub fn без параметров (spec/runtime/machine.md)")
    rp.add_argument("root")
    rp.add_argument("entry", help="<модуль>.<функция>")
    rp.add_argument("--fuel", type=int, default=DEFAULT_FUEL, help="бюджет шагов машины")
    rp.add_argument("--trace", action="store_true", help="уровень L1: шаги и трасса правил")
    rp.add_argument("--json", action="store_true", help="одной строкой")
    rp.add_argument("--db", help="хранилище SQLite: исполнить command или query через хост")
    rp.add_argument("--args", help="аргументы точки входа: JSON-список наблюдений CANON-11 или @файл")
    rp.add_argument("--namespace", help="KeyRef команды: пространство ключей")
    rp.add_argument("--key", help="KeyRef команды: ключ идемпотентности")
    rp.add_argument("--caller", default="anonymous", help="вызывающий по политике хоста")
    rp.add_argument("--policy", help="файл политики хоста (по умолчанию <корень>/host-policy.json)")
    rp.add_argument("--expected-state-version", type=int, help="guard: StateVersion, на которой основан запрос")
    rp.set_defaults(fn=cmd_run)
    from bagaev_ref.host.cli import register
    register(sub, DEFAULT_FUEL)
    from bagaev_ref.links.cli import register as register_links
    register_links(sub)
    from bagaev_ref.protocol.cli import register as register_protocol
    register_protocol(sub)
    tp = sub.add_parser("test", help="исполнить объявления test проекта")
    tp.add_argument("root")
    tp.add_argument("--fuel", type=int, default=DEFAULT_FUEL)
    tp.add_argument("--json", action="store_true")
    tp.set_defaults(fn=cmd_test)
    fp = sub.add_parser("fmt", help="канонический формат (spec/language/format.md)")
    fp.add_argument("paths", nargs="+", help="файлы .bag или каталоги")
    fp.add_argument("--check", action="store_true", help="не переписывать; код 1, если есть неотформатированные")
    fp.add_argument("--assign-ids", action="store_true", help="вставить недостающие @id (FMT-16)")
    fp.set_defaults(fn=cmd_fmt)
    ce = sub.add_parser("conformance-exec", help="исполнить один случай conformance/ и вывести наблюдение")
    ce.add_argument("--case", required=True)
    ce.add_argument("--json", action="store_true", required=True)
    ce.set_defaults(fn=cmd_conformance_exec)
    a = ap.parse_args(argv)
    return run_deep(lambda: a.fn(a))


def run_deep(fn):
    """Рекурсивный спуск и проверка глубоки на длинных цепочках операторов: отдельный поток с большим стеком.
    Исчерпание и этого предела — защитный исход реализации, а не traceback (TYPES-0.1 §10)."""
    result = {}

    def target():
        try:
            result["rc"] = fn()
        except RecursionError:
            print(json.dumps({"outcome": "IMPLEMENTATION_STOP", "code": "RESOURCE_LIMIT",
                              "detail": "превышена глубина вложенности"}, ensure_ascii=False))
            result["rc"] = 3
    sys.setrecursionlimit(200000)
    threading.stack_size(1 << 29)
    t = threading.Thread(target=target)
    t.start()
    t.join()
    return result.get("rc", 3)


if __name__ == "__main__":
    sys.exit(main())
