#!/usr/bin/env python3
"""Метрика EXEC-1 (registry/EXEC_METHOD.md).

  python3 tools/exec_report.py           прогнать корпус и записать registry/exec-progress.json
  python3 tools/exec_report.py --print   только вывести строку итога и JSON, ничего не записывая

Содержимое детерминировано (без времени и хешей коммита): check.py --exec пересчитывает его
и сравнивает с сохранённым файлом.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "registry" / "exec-progress.json"
DECISIONS = ROOT / "spec" / "architecture" / "07-decisions.md"
PILOT_DECISION = ROOT / "pilot" / "authorship" / "decision.md"
PILOT_STATUSES = ("NOT_RUN", "IN_PROGRESS", "PASS", "FAIL", "INCONCLUSIVE")


def conformance():
    spec = importlib.util.spec_from_file_location("bagaev_conformance", ROOT / "conformance" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def decisions() -> dict:
    """Статусы карточек решений: строки таблиц `| Dnn | … | статус | …` в 07-decisions.md."""
    text = DECISIONS.read_text(encoding="utf-8")
    seen: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\| (D\d+) \|", line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        status = "proposed"
        for c in cells[2:]:
            if c.startswith("accepted") or c.startswith("частично accepted"):
                status = "accepted" if c.startswith("accepted") else "partially_accepted"
        seen[m.group(1)] = status
    out = {"accepted": 0, "partially_accepted": 0, "proposed": 0}
    for s in seen.values():
        out[s] += 1
    out["total"] = len(seen)
    return out


def pilot() -> str:
    if not PILOT_DECISION.is_file():
        return "NOT_RUN"
    m = re.search(r"Статус:\s*\**([A-Z_]+)", PILOT_DECISION.read_text(encoding="utf-8"))
    return m.group(1) if m and m.group(1) in PILOT_STATUSES else "IN_PROGRESS"


def compute() -> dict:
    conf = conformance()
    lint_errors = conf.lint()
    runs = {name: conf.run_impl(name) for name in ("ref", "rust")}
    cov = conf.coverage(runs["ref"])
    return {
        "schema": "bagaev-exec-progress/1",
        "method": "EXEC-1",
        "lint_errors": len(lint_errors),
        "rules": cov,
        "implementations": {
            name: {"available": r["available"], "passed": r["passed"], "total": r["total"],
                   "not_run": r.get("skipped", 0),
                   "failed": sorted(c["id"] for c in r["cases"] if c["status"] in ("FAIL", "ERROR"))}
            for name, r in runs.items()},
        "pilot": pilot(),
        "decisions": decisions(),
    }


def line(d: dict) -> str:
    r, i = d["rules"], d["implementations"]
    rust = f"{i['rust']['passed']}/{i['rust']['total']}" if i["rust"]["available"] else "нет"
    return (f"EXEC-1: правил покрыто {r['rules_covered']}/{r['rules_total']}; "
            f"ref {i['ref']['passed']}/{i['ref']['total']} (NOT_RUN {i['ref']['not_run']}); rust {rust}; пилот {d['pilot']}")


def render(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--print", action="store_true")
    a = ap.parse_args()
    d = compute()
    if a.print:
        print(render(d), end="")
    else:
        OUT.write_text(render(d), encoding="utf-8")
    print(line(d), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
