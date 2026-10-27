#!/usr/bin/env python3
"""Раннер conformance-корпуса bagaev.

  python3 conformance/run.py --lint                 проверить форму случаев и манифест правил
  python3 conformance/run.py --impl ref [--area A]  прогнать реализацию по корпусу
  python3 conformance/run.py --impl ref --json      сводка в JSON (stdout)

Только стандартная библиотека Python. Ничего не пишет в рабочее дерево.
Контракт исполнителя и форма случая — conformance/README.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "conformance" / "cases"
MANIFEST = ROOT / "spec" / "conformance-manifest.json"
DIAG_REGISTRY = ROOT / "spec" / "diagnostics" / "registry.json"

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9._-]*$")
ORIGIN_RE = re.compile(r"^(independent|derived|model:(models/[^#\s]+)#\S+)$")
CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
PHASES = {"parse", "fmt", "check", "run", "graph", "impact", "context", "edit", "accept", "store", "events", "migrate",
          "protocol"}
CASE_KEYS = {"id", "spec", "origin", "levels", "files", "note", "run", "expect"}
EXPECT_KEYS = {"phase", "outcome", "value", "code", "site", "data", "effects", "diagnostics", "trace_l1", "steps", "state"}
L2_FIELDS = ("phase", "outcome", "value", "code", "site", "data", "effects", "diagnostics", "state")
L1_FIELDS = ("trace_l1", "steps")


def implementations() -> dict[str, dict]:
    """Известные реализации: команда запуска и окружение. Отсутствующая реализация не регистрируется."""
    impls = {"ref": {"argv": [sys.executable, "-B", "-m", "bagaev_ref"],
                     "env": {"PYTHONPATH": str(ROOT / "ref"), "PYTHONDONTWRITEBYTECODE": "1"}}}
    rust = ROOT / "compiler" / "target" / "release" / "bagc"
    if rust.is_file():
        impls["rust"] = {"argv": [str(rust)], "env": {}}
    return impls


# --------------------------------------------------------------------------- якоря
def slug(heading: str) -> str:
    """GitHub-подобный якорь заголовка Markdown (кириллица сохраняется)."""
    s = re.sub(r"[`*\[\]()<>]", "", heading.strip().lower())
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def anchors(md: Path) -> set[str]:
    """Якоря заголовков; повторный заголовок получает суффикс -1, -2… (как на GitHub)."""
    out, seen, in_fence = set(), {}, False
    for line in md.read_text(encoding="utf-8").split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and re.match(r"^#{1,6} ", line):
            base = slug(line.lstrip("#"))
            n = seen.get(base, 0)
            seen[base] = n + 1
            out.add(base if n == 0 else f"{base}-{n}")
    return out


def check_spec_ref(ref: str) -> str | None:
    path, _, anchor = ref.partition("#")
    p = ROOT / path
    if not p.is_file():
        return f"нет файла {path}"
    if anchor and p.suffix == ".md" and anchor not in anchors(p):
        return f"нет якоря #{anchor} в {path}"
    return None


# --------------------------------------------------------------------------- случаи
def load_cases(area: str | None = None) -> list[tuple[Path, dict | None, str | None]]:
    """[(каталог, case|None, ошибка разбора|None)], в стабильном порядке путей."""
    out = []
    if not CASES.is_dir():
        return out
    for cf in sorted(CASES.rglob("case.json")):
        d = cf.parent
        rel = d.relative_to(CASES).as_posix()
        if area and not rel.startswith(area + "/"):
            continue
        try:
            out.append((d, json.loads(cf.read_text(encoding="utf-8")), None))
        except Exception as e:  # noqa: BLE001
            out.append((d, None, f"case.json не читается: {e}"))
    return out


def diag_codes() -> set[str] | None:
    if not DIAG_REGISTRY.is_file():
        return None
    reg = json.loads(DIAG_REGISTRY.read_text(encoding="utf-8"))
    codes = {c["code"] for c in reg.get("codes", [])}
    codes |= {a["alias"] for a in reg.get("aliases", [])}
    return codes


def lint_case(d: Path, c: dict, codes: set[str] | None) -> list[str]:
    if not isinstance(c, dict):
        return ["case.json — не объект"]
    e = []
    rel = d.relative_to(CASES).as_posix()
    unknown = set(c) - CASE_KEYS
    if unknown:
        e.append(f"лишние поля {sorted(unknown)}")
    for k in ("id", "spec", "origin", "levels", "expect"):
        if k not in c:
            e.append(f"нет поля {k}")
    if e:
        return e
    if not ID_RE.match(c["id"]) or c["id"] != rel:
        e.append(f"id {c['id']!r} не совпадает с каталогом {rel!r} или не по форме область/имя")
    if not isinstance(c["spec"], list) or not c["spec"]:
        e.append("spec — непустой список ссылок")
    else:
        for r in c["spec"]:
            if not isinstance(r, str) or not r.startswith("spec/"):
                e.append(f"spec-ссылка {r!r} не в spec/")
            elif (msg := check_spec_ref(r)):
                e.append(msg)
    m = ORIGIN_RE.match(c["origin"]) if isinstance(c["origin"], str) else None
    if not m:
        e.append(f"origin {c['origin']!r} не допустим")
    elif m.group(2) and not (ROOT / m.group(2)).exists():
        e.append(f"origin ссылается на отсутствующий {m.group(2)}")
    lv = c["levels"]
    if not isinstance(lv, list) or not lv or not all(isinstance(x, str) for x in lv) \
            or set(lv) - {"L1", "L2"} or len(set(lv)) != len(lv):
        e.append("levels — непустой список без повторов из {L1, L2}")
    files = c.get("files", [])
    if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
        e.append("files — список строк")
    else:
        for f in files:
            if f.startswith("/") or ".." in Path(f).parts or not (d / f).is_file():
                e.append(f"нет файла программы {f} (или путь выходит из каталога случая)")
    run = c.get("run")
    if run is not None:
        if not isinstance(run, dict) or set(run) - {"entry", "args", "fuel", "cancel_at", "steps", "state_program", "links", "change"}:
            e.append("run — объект с полями entry, args, fuel, cancel_at или steps, state_program")
        elif "steps" in run and c.get("expect", {}).get("phase") not in ("store", "events", "migrate"):
            e.append("run.steps — только у сценариев фаз store, events, migrate")
        elif "links" in run and c.get("expect", {}).get("phase") not in ("graph", "impact", "context"):
            e.append("run.links — только у фаз graph, impact, context")
        elif "change" in run and c.get("expect", {}).get("phase") not in ("edit", "accept", "protocol"):
            e.append("run.change — только у фаз edit, accept, protocol")
        elif "fuel" in run and (not isinstance(run["fuel"], int) or run["fuel"] < 0):
            e.append("run.fuel — неотрицательное целое")
    x = c["expect"]
    if not isinstance(x, dict):
        return e + ["expect — объект"]
    if set(x) - EXPECT_KEYS:
        e.append(f"лишние поля expect {sorted(set(x) - EXPECT_KEYS)}")
    if x.get("phase") not in PHASES:
        e.append(f"expect.phase {x.get('phase')!r} не из {sorted(PHASES)}")
    if not isinstance(x.get("outcome"), str) or not CODE_RE.match(x["outcome"]):
        e.append("expect.outcome — код UPPER_SNAKE")
    if x.get("phase") == "run" and "effects" not in x:
        e.append("случай исполнения обязан задать expect.effects (хотя бы [])")
    if x.get("outcome") == "PRELAUNCH" and "diagnostics" not in x:
        e.append("исход PRELAUNCH обязан задать expect.diagnostics")
    for dg in x.get("diagnostics", []):
        if isinstance(dg, dict) and "span" in dg:
            sp = dg["span"]
            if not (isinstance(sp, list) and len(sp) == 2 and all(isinstance(v, int) and v >= 0 for v in sp)
                    and sp[0] <= sp[1]):
                e.append(f"span {sp!r} — [начало, конец) из неотрицательных целых")
        code = dg.get("code") if isinstance(dg, dict) else None
        if not isinstance(code, str) or not CODE_RE.match(code):
            e.append(f"код диагностики {code!r} не UPPER_SNAKE")
        elif codes is not None and code not in codes:
            e.append(f"код {code} нет в реестре DIAG-1")
    if "L1" in c["levels"] and c["expect"].get("phase") == "run" and "trace_l1" not in x:
        e.append("уровень L1 у случая исполнения требует expect.trace_l1")
    return e


def load_manifest() -> tuple[list[dict], list[str]]:
    if not MANIFEST.is_file():
        return [], ["нет spec/conformance-manifest.json"]
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errs, seen = [], set()
    rules = m.get("rules", [])
    for r in rules:
        rid = r.get("rule_id")
        if not rid or rid in seen:
            errs.append(f"правило без rule_id или повтор: {rid!r}")
        seen.add(rid)
        if r.get("status") not in ("EXECUTABLE", "NOT_YET_EXECUTABLE"):
            errs.append(f"{rid}: status должен быть EXECUTABLE или NOT_YET_EXECUTABLE")
        if r.get("status") == "NOT_YET_EXECUTABLE" and not r.get("reason"):
            errs.append(f"{rid}: NOT_YET_EXECUTABLE без причины")
        if (msg := check_spec_ref(r.get("spec", ""))):
            errs.append(f"{rid}: {msg}")
    return rules, errs


def lint() -> list[str]:
    errs, ids = [], {}
    codes = diag_codes()
    for d, c, perr in load_cases():
        rel = d.relative_to(CASES).as_posix()
        if perr:
            errs.append(f"{rel}: {perr}")
            continue
        for msg in lint_case(d, c, codes):
            errs.append(f"{rel}: {msg}")
        if c.get("id") in ids:
            errs.append(f"{rel}: повтор id {c['id']}")
        ids[c.get("id")] = rel
    rules, merrs = load_manifest()
    errs += merrs
    for r in rules:
        for cid in r.get("cases", []):
            if cid not in ids:
                errs.append(f"{r.get('rule_id')}: случай {cid} не существует")
    return errs


# --------------------------------------------------------------------------- прогон
MISSING = object()


def compare_diagnostics(want: list, got) -> list[str]:
    """Префикс: k-я ожидаемая против k-й наблюдаемой; code точно, span/file если заданы, data — подмножество."""
    if not isinstance(got, list):
        return [f"diagnostics: ожидался список, получено {type(got).__name__}"]
    diffs = []
    for k, w in enumerate(want):
        if k >= len(got) or not isinstance(got[k], dict):
            diffs.append(f"diagnostics[{k}]: ожидалась {w.get('code')}, наблюдаемой нет")
            continue
        g = got[k]
        for f in ("code", "span", "file"):
            if f in w and g.get(f, MISSING) != w[f]:
                diffs.append(f"diagnostics[{k}].{f}: ожидалось {w[f]!r}, получено {g.get(f, '<нет>')!r}")
        for dk, dv in (w.get("data") or {}).items():
            if (g.get("data") or {}).get(dk, MISSING) != dv:
                diffs.append(f"diagnostics[{k}].data.{dk}: ожидалось {dv!r}")
    return diffs


def compare(expect: dict, obs: dict, levels: list[str]) -> list[str]:
    """Поля, заданные в expect, сравниваются точно (кроме diagnostics); отсутствие поля в наблюдении ≠ null."""
    diffs = []
    fields = list(L2_FIELDS) + (list(L1_FIELDS) if "L1" in levels else [])
    for k in fields:
        if k == "diagnostics" and k in expect:
            diffs += compare_diagnostics(expect[k], obs.get(k, []))
            continue
        if k in expect and obs.get(k, MISSING) != expect[k]:
            got = "поля нет" if k not in obs else f"получено {json.dumps(obs[k], ensure_ascii=False)[:120]}"
            diffs.append(f"{k}: ожидалось {json.dumps(expect[k], ensure_ascii=False)[:120]}, {got}")
    return diffs


def run_impl(name: str, area: str | None = None, timeout: int = 60) -> dict:
    impls = implementations()
    if name not in impls:
        return {"impl": name, "available": False, "cases": [], "passed": 0, "total": 0}
    spec = impls[name]
    env = dict(os.environ, **spec["env"])
    res = []
    import tempfile
    workdir = tempfile.mkdtemp(prefix="bagaev-conf-")   # реализация не пишет в рабочее дерево
    for d, c, perr in load_cases(area):
        rel = d.relative_to(CASES).as_posix()
        if perr or c is None:
            res.append({"id": rel, "status": "ERROR", "detail": perr})
            continue
        if not isinstance(c, dict) or lint_case(d, c, None):
            res.append({"id": rel, "origin": None, "status": "ERROR", "detail": "случай не проходит lint"})
            continue
        levels = c.get("levels", [])
        if name != "ref" and levels == ["L1"]:
            continue  # L1 нормативен только для эталона (D76)
        use_levels = levels if name == "ref" else [lv for lv in levels if lv == "L2"]
        try:
            p = subprocess.run([*spec["argv"], "conformance-exec", "--case", str(d), "--json"],
                               capture_output=True, text=True, env=env, timeout=timeout, cwd=workdir)
            obs = json.loads(p.stdout) if p.stdout.strip() else None
            if p.returncode != 0 or not isinstance(obs, dict):
                res.append({"id": c["id"], "origin": c["origin"], "status": "ERROR",
                            "detail": f"код {p.returncode}, наблюдение не объект: {(p.stdout + p.stderr)[-200:]}"})
                continue
            if obs.get("outcome") == "IMPLEMENTATION_STOP" and obs.get("code") == "NOT_IMPLEMENTED" \
                    and c["expect"].get("outcome") != "IMPLEMENTATION_STOP" \
                    and obs.get("phase") == c["expect"].get("phase"):
                res.append({"id": c["id"], "origin": c["origin"], "status": "SKIP",
                            "detail": "NOT_RUN: реализация ещё не поддерживает эту фазу"})
                continue
            diffs = compare(c["expect"], obs, use_levels)
            st = "PASS" if not diffs else "FAIL"
            res.append({"id": c["id"], "origin": c["origin"], "status": st, "detail": "; ".join(diffs)[:400]})
        except subprocess.TimeoutExpired:
            res.append({"id": c["id"], "origin": c["origin"], "status": "ERROR", "detail": f"timeout {timeout}s"})
        except json.JSONDecodeError as ex:
            res.append({"id": c["id"], "origin": c["origin"], "status": "ERROR", "detail": f"не JSON: {ex}"})
    import shutil
    shutil.rmtree(workdir, ignore_errors=True)
    passed = sum(1 for r in res if r["status"] == "PASS")
    skipped = sum(1 for r in res if r["status"] == "SKIP")
    return {"impl": name, "available": True, "cases": res, "passed": passed, "skipped": skipped, "total": len(res)}


def coverage(ref_run: dict) -> dict:
    rules, _ = load_manifest()
    ok = {r["id"] for r in ref_run.get("cases", [])
          if r["status"] == "PASS" and r.get("origin") != "derived"}
    covered = [r["rule_id"] for r in rules
               if r.get("status") == "EXECUTABLE" and not r.get("partial")
               and r.get("cases") and all(cid in ok for cid in r["cases"])]
    return {"rules_total": len(rules), "rules_covered": len(covered),
            "rules_partial": sum(1 for r in rules if r.get("partial")),
            "rules_not_yet_executable": sum(1 for r in rules if r.get("status") == "NOT_YET_EXECUTABLE")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lint", action="store_true")
    ap.add_argument("--impl", choices=["ref", "rust"])
    ap.add_argument("--area")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    errs = lint()
    for e in errs:
        print(f"[lint] {e}", file=sys.stderr)
    out: dict = {"lint_errors": errs}
    rc = 1 if errs else 0
    if a.impl:
        r = run_impl(a.impl, a.area)
        out["run"] = r
        for c in r["cases"]:
            if c["status"] in ("FAIL", "ERROR"):
                print(f"[{c['status']}] {c['id']}: {c['detail']}", file=sys.stderr)
        if not r["available"]:
            print(f"реализация {a.impl} недоступна", file=sys.stderr)
            rc = 1
        elif any(c["status"] in ("FAIL", "ERROR") for c in r["cases"]):
            rc = 1
        print(f"{a.impl}: {r['passed']}/{r['total']} случаев, NOT_RUN {r.get('skipped', 0)}", file=sys.stderr)
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    elif not a.impl:
        print("lint: " + ("OK" if not errs else f"{len(errs)} ошибок"), file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
