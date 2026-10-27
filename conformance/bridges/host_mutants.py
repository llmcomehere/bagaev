#!/usr/bin/env python3
"""Мутационная проверка корпуса хоста (Ф4): заведомая порча правила HOST-1 должна давать FAIL хотя бы одного
сценария conformance/cases/{store,events,migrate}. Мутант — копия пакета эталона во временном каталоге с одной
текстовой заменой; файлы репозитория не меняются.

  python3 conformance/bridges/host_mutants.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "ref" / "bagaev_ref"
AREAS = ("store", "events", "migrate")
_spec = importlib.util.spec_from_file_location("bagaev_conformance_hm", ROOT / "conformance" / "run.py")
_conf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_conf)

# (имя, правило, файл пакета, заменяемый фрагмент, замена)
MUTANTS = [
    ("receipt_after_guard", "HST-05", "host/driver.py", "r = store.receipt(ns, key)",
     "r = store.receipt(ns, key) if expected_state is None else None"),
    ("err_keeps_writes", "HST-06", "host/driver.py",
     '            store.db.execute("ROLLBACK TO body")\n', ""),
    ("err_without_receipt", "HST-06", "host/driver.py", "            host.events = []\n",
     '            store.db.execute("ROLLBACK")\n            return dict(obs, outcome="ABORTED", final=True, replayed=False)\n'),
    ("err_keeps_state_version", "HST-03", "host/driver.py", "            host.events = []\n",
     "            host.events = []\n            new_sv = sv\n"),
    ("delivery_without_dedup", "HST-11", "host/driver.py", "if done is not None:", "if done is not None and False:"),
    ("delivery_skips_failed", "HST-11", "host/driver.py",
     '            if r["outcome"] != "COMMITTED":\n                break', '            if False:\n                break'),
    ("writer_lock_ignored", "HST-15", "host/driver.py",
     'if lock:\n        return refused("MIGRATION_IN_PROGRESS"', 'if False:\n        return refused("MIGRATION_IN_PROGRESS"'),
    ("replay_ignores_arguments", "HST-13", "host/driver.py",
     "if [enc(a, t) for a, t in zip(args, store_arg_types(name, tbl))] != rec.get(\"args\"):", "if False:"),
    ("events_outside_binding", "HST-04", "host/store.py", "events[type_id(t)] = event_shape(t)", "pass"),
    ("revoke_ignored", "HST-09", "host/driver.py", "return frozenset(a for a in info.row.atoms if T.show_atom(a) not in revoked)",
     "return frozenset(info.row.atoms)"),
    ("migration_without_drain", "HST-15", "host/migrate.py", "    if backlog:", "    if False:"),
    ("migration_keeps_epoch", "HST-15", "host/migrate.py", 'epoch = p["epoch"] + 1', 'epoch = p["epoch"]'),
    ("migration_insertion_order", "HST-15", "host/migrate.py", "sorted(rows, key=lambda r: key_of(r[0]))", "rows"),
]


def cases():
    out = []
    for area in AREAS:
        for d in sorted((ROOT / "conformance" / "cases" / area).iterdir()):
            if (d / "case.json").is_file():
                out.append((d, json.loads((d / "case.json").read_text(encoding="utf-8"))))
    return out


def run_case(pythonpath: str, d: Path, c: dict) -> bool:
    env = dict(os.environ, PYTHONPATH=pythonpath, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, "-m", "bagaev_ref", "conformance-exec", "--case", str(d), "--json"],
                       capture_output=True, text=True, env=env, timeout=120, cwd=tempfile.gettempdir())
    try:
        obs = json.loads(p.stdout)
    except ValueError:
        return False
    return p.returncode == 0 and not _conf.compare(c["expect"], obs, c.get("levels", ["L2"]))


def main() -> int:
    all_cases = cases()
    report = {}
    with tempfile.TemporaryDirectory(prefix="bag-host-mut-") as tmp:
        base = Path(tmp) / "ref"
        shutil.copytree(PKG, base / "bagaev_ref", ignore=shutil.ignore_patterns("__pycache__"))
        (Path(tmp) / "spec" / "diagnostics").mkdir(parents=True)          # реестр DIAG-1 рядом, как в репозитории
        shutil.copy(ROOT / "spec" / "diagnostics" / "registry.json", Path(tmp) / "spec" / "diagnostics" / "registry.json")
        for name, rule, rel, old, new in MUTANTS:
            f = base / "bagaev_ref" / rel
            src = f.read_text(encoding="utf-8")
            assert src.count(old) == 1, (name, src.count(old))
            f.write_text(src.replace(old, new), encoding="utf-8")
            try:
                killed = [c["id"] for d, c in all_cases if not run_case(str(base), d, c)]
            finally:
                f.write_text(src, encoding="utf-8")
            report[name] = {"rule": rule, "caught": bool(killed), "by": killed[:4]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(v["caught"] for v in report.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
