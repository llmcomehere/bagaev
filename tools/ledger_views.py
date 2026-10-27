#!/usr/bin/env python3
"""Читаемые представления реестра функций V1 из канонического registry/feature-ledger.json.

  python3 tools/ledger_views.py           записать registry/feature-ledger.md и .csv
  python3 tools/ledger_views.py --check   только сравнить (код 1 при расхождении); так вызывает check.py

Представления не правятся руками: источник — JSON.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "registry/feature-ledger.json"
MD = ROOT / "registry/feature-ledger.md"
CSV = ROOT / "registry/feature-ledger.csv"

CSV_FIELDS = ["feature_id", "title", "obligation", "owner_tasks", "criterion_ids", "contract_status",
              "evidence_status", "form_or_interface", "evaluation_or_transition", "open_decisions",
              "future_check_ids", "future_expected_results", "source_refs", "draft_refs"]


def cell(f: dict, name: str) -> str:
    return (f.get("contract_cells") or {}).get(name, {}).get("description", "")


def esc(s: str) -> str:
    return s.replace("|", "\\|")


def render_md(d: dict) -> str:
    out = [d.get("md_title") or f"# Реестр V1 — читаемое представление {d.get('iteration', '')}", "", d["md_intro"], "",
           "| ID | Возможность | Обязательство | Задачи / критерии | Открытое решение |",
           "| --- | --- | --- | --- | --- |"]
    for f in d["features"]:
        tasks = ", ".join(f["owner_tasks"]) + "; " + ", ".join(f["criterion_ids"])
        out.append(f"| {f['feature_id']} | {esc(f['title'])} | {f['obligation']} | {tasks} | "
                   f"{esc('; '.join(f.get('open_decisions', [])))} |")
    out += ["", "## Наблюдаемые взаимодействия", "",
            "| ID | Связанные позиции | Правило | Что осталось |", "| --- | --- | --- | --- |"]
    for i in d["interactions"]:
        out.append(f"| {i['interaction_id']} | {', '.join(i['feature_ids'])} | {esc(i['rule'])} | {esc(i['remaining'])} |")
    return "\n".join(out) + "\n"


def render_csv(d: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CSV_FIELDS)
    for f in d["features"]:
        checks = f.get("future_checks", [])
        w.writerow([f["feature_id"], f["title"], f["obligation"], "; ".join(f["owner_tasks"]),
                    "; ".join(f["criterion_ids"]), f["contract_status"], f["evidence_status"],
                    cell(f, "form_or_interface"), cell(f, "evaluation_or_transition"),
                    "; ".join(f.get("open_decisions", [])), "; ".join(c["id"] for c in checks),
                    "; ".join(f"{c['id']}: {c['expected']}" for c in checks),
                    "; ".join(f"{r['scope']}:{r['ref']}" for r in f.get("source_refs", [])),
                    "; ".join(f.get("draft_refs", []))])
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    d = json.loads(SRC.read_text(encoding="utf-8"))
    views = {MD: render_md(d), CSV: render_csv(d)}
    if a.check:
        bad = [p.name for p, t in views.items() if p.read_text(encoding="utf-8") != t]
        if bad:
            print("расходятся с feature-ledger.json: " + ", ".join(bad) + " (python3 tools/ledger_views.py)")
            return 1
        print("feature-ledger.md и .csv совпадают с JSON")
        return 0
    for p, t in views.items():
        p.write_text(t, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
