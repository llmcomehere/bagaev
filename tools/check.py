#!/usr/bin/env python3
"""Проверка публичного исходного пакета: структура, --exec, --models, --all.

Источники, спецификация и независимые проверки образуют один пакет.
Отчёты по --json сохраняются только в явно указанном месте.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_DEPS = ROOT / ".deps"
VENV_PY = ROOT / ".venv" / "bin" / "python"


results: list[dict] = []


def add(name, status, detail="", **kw):
    r = {"name": name, "status": status, "detail": detail, **kw}
    results.append(r)
    print(f"[{status:5}] {name}" + (f" — {detail}" if detail and status != "PASS" else ""), file=sys.stderr, flush=True)
    return r


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# --------------------------------------------------------------------------- живой слой
LINK = re.compile(r"\]\(([^)\s]+)\)")
LIVING_MD = ["*.md", "spec/**/*.md", "registry/**/*.md", "models/*/README.md", "docs/**/*.md", "tools/*.md", "ref/**/*.md", "conformance/**/*.md",
             "pilot/**/*.md", "examples/**/*.md"]


KNOWN_ANCHORS: dict[str, str] = {}


def check_links():
    anchors = load_module("bagaev_conformance", ROOT / "conformance/run.py").anchors
    broken, bad_anchor, known, n = [], [], [], 0
    seen = set()
    for pat in LIVING_MD:
        for p in ROOT.glob(pat):
            if p in seen or not p.is_file():
                continue
            seen.add(p)
            in_fence = False
            for i, line in enumerate(p.read_text(encoding="utf-8").split("\n"), 1):
                if line.lstrip().startswith("```"):
                    in_fence = not in_fence
                if in_fence:
                    continue
                for m in LINK.finditer(line):
                    full = m.group(1)
                    t, _, anchor = full.partition("#")
                    if re.match(r"^[a-z][a-z0-9+.-]*:", full, re.I):
                        continue
                    target = (p.parent / t).resolve() if t else p.resolve()
                    if t:
                        n += 1
                        if ROOT.resolve() not in (target, *target.parents):
                            broken.append(f"{p.relative_to(ROOT)}:{i} → {t} (вне репозитория)")
                            continue
                        if not target.exists():
                            broken.append(f"{p.relative_to(ROOT)}:{i} → {t}")
                            continue
                    if anchor and target.suffix == ".md" and anchor not in anchors(target):
                        key = f"{p.relative_to(ROOT)} → {full}"
                        (known if key in KNOWN_ANCHORS else bad_anchor).append(f"{p.relative_to(ROOT)}:{i} → {full}")
    st = "FAIL" if broken or bad_anchor else ("KNOWN" if known else "PASS")
    add("living: внутренние ссылки и якоря документов", st,
        (f"{len(broken)} битых ссылок: " + "; ".join(broken[:6]) + "; " if broken else "") +
        (f"{len(bad_anchor)} битых якорей: " + "; ".join(bad_anchor[:6]) + "; " if bad_anchor else "") +
        (f"известные (ERRATA): {known}" if known else "") if st != "PASS" else f"{n} ссылок, {len(seen)} документов")


def check_json():
    bad, n = [], 0
    for top in ("spec", "registry", "conformance", "pilot", "examples"):
        for p in (ROOT / top).rglob("*.json"):
            n += 1
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                bad.append(f"{p.relative_to(ROOT)}: {e}")
    add("living: JSON в spec/, registry/, conformance/, pilot/, examples/ читается", "FAIL" if bad else "PASS",
        "; ".join(bad[:5]) if bad else f"{n} файлов")


def tracked_files() -> list[str]:
    r = git("ls-files", "-z")
    if r.returncode == 0:
        return [x for x in r.stdout.decode().split("\0") if x]
    return [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts
            and ".venv" not in p.parts and ".deps" not in p.parts and "__pycache__" not in p.parts]


# --------------------------------------------------------------------------- реестры и исполнимый слой
def load_module(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod          # dataclasses требуют модуль в sys.modules
    spec.loader.exec_module(mod)
    return mod


def md_section(s: str, header: str) -> str | None:
    m = re.search(rf"^## {re.escape(header)}\n(.*?)(?=^## |\Z)", s, re.S | re.M)
    return m.group(1) if m else None


def md_bullets(s: str, header: str) -> list[str]:
    sec = md_section(s, header)
    return [l[2:].strip() for l in sec.splitlines() if l.startswith("- ")] if sec else []


def md_plain(x: str) -> str:
    return re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", x).replace("`", "").strip()


def check_no_model_copies():
    model = {sha256(p) for p in (ROOT / "models").rglob("*") if p.is_file() and p.suffix == ".py"}
    copies = [p.relative_to(ROOT).as_posix() for top in ("ref", "compiler") if (ROOT / top).is_dir()
              for p in (ROOT / top).rglob("*") if p.is_file() and "target" not in p.parts
              and "__pycache__" not in p.parts and sha256(p) in model]
    add("living: нет копий кода моделей в ref/ и compiler/ (T17-C03)", "FAIL" if copies else "PASS",
        f"совпадают с models/: {copies[:5]}" if copies else f"сверено с {len(model)} файлами .py моделей")


def check_track():
    errs = []
    track = json.loads((ROOT / "registry/track.json").read_text(encoding="utf-8"))
    roster = json.loads((ROOT / "registry/criteria.json").read_text(encoding="utf-8"))
    stale = [k for k in ("work", "readiness", "history", "research_iterations") if k in track]
    if stale:
        errs.append(f"в track.json снова состояние работы: {stale} (оно живёт в NEXT.md и progress.json)")
    ids = [t["id"] for t in track["tasks"]]
    cards = sorted(p.name.split("-", 1)[0] for p in (ROOT / "registry/tasks").glob("T*.md"))
    if sorted(ids) != cards:
        errs.append(f"задачи track.json {ids} ≠ карточки registry/tasks {cards}")
    for t in track["tasks"]:
        if not (ROOT / "registry" / t["path"]).is_file():
            errs.append(f"{t['id']}: нет карточки {t['path']}")
    for t in track["tasks"]:
        card = (ROOT / "registry" / t["path"])
        if not card.is_file():
            continue
        s = card.read_text(encoding="utf-8")
        for header, key in (("Входы и зависимости", "inputs"), ("Планируемые выходы", "outputs"),
                            ("Планируемые выходы", "planned_outputs")):
            got = [md_plain(x) for x in md_bullets(s, header)]
            if got != t.get(key):
                errs.append(f"{t['id']}.{key} ≠ карточка «{header}»")
        rec = md_section(s, "Если условие не выполнено")
        if rec is not None and md_plain(" ".join(rec.split())) != t.get("recovery"):
            errs.append(f"{t['id']}.recovery ≠ карточка «Если условие не выполнено»")
        rows = re.findall(r"^\| (T\d\d-C\d\d) \| (.+?) \|$", s, re.M)
        if rows != [(c["id"], c["criterion"]) for c in t["acceptance"]]:
            errs.append(f"{t['id']}: таблица критериев карточки ≠ track.json")
    acc = [(c["id"], c["criterion"]) for t in track["tasks"] if t["profile"] == "V1" for c in t["acceptance"]]
    if acc != [(c["criterion_id"], c["criterion"]) for c in roster]:
        errs.append("критерии V1 в track.json расходятся с criteria.json (состав, порядок или текст)")
    add("living: track.json ↔ criteria.json ↔ registry/tasks", "FAIL" if errs else "PASS",
        "; ".join(errs) if errs else f"{len(ids)} задач, {len(acc)} критериев V1")


def check_ledger_views():
    lv = load_module("bagaev_ledger_views", ROOT / "tools/ledger_views.py")
    d = json.loads(lv.SRC.read_text(encoding="utf-8"))
    bad = [p.name for p, t in ((lv.MD, lv.render_md(d)), (lv.CSV, lv.render_csv(d)))
           if p.read_text(encoding="utf-8") != t]
    add("living: feature-ledger.md/.csv сгенерированы из .json", "FAIL" if bad else "PASS",
        f"расходятся: {bad} — python3 tools/ledger_views.py" if bad else f"{len(d['features'])} позиций")


def check_diagnostics():
    reg = ROOT / "spec/diagnostics/registry.json"
    if not reg.is_file():
        add("living: реестр диагностик DIAG-1", "SKIP", "NOT_RUN: реестра ещё нет (появляется в Ф1)")
        return
    d = json.loads(reg.read_text(encoding="utf-8"))
    codes = [c["code"] for c in d.get("codes", [])]
    aliases = [a["alias"] for a in d.get("aliases", [])]
    dup = sorted({c for c in codes + aliases if (codes + aliases).count(c) > 1})
    bad = [c for c in codes if not re.fullmatch(r"[A-Z][A-Z0-9_]*", c)]
    dangling = [a["alias"] for a in d.get("aliases", []) if a.get("code") and a["code"] not in codes]
    errs = ([f"повторы {dup}"] if dup else []) + ([f"не UPPER_SNAKE {bad}"] if bad else []) + \
           ([f"псевдонимы на неизвестный код {dangling}"] if dangling else [])
    add("living: реестр диагностик DIAG-1", "FAIL" if errs else "PASS",
        "; ".join(errs) if errs else f"{len(codes)} кодов, {len(aliases)} псевдонимов")


def check_grammar():
    gl = load_module("bagaev_grammar_lint", ROOT / "tools/grammar_lint.py")
    g = gl.Grammar(gl.GRAMMAR.read_text(encoding="utf-8"))
    errs, info = gl.lint_grammar(g)
    add("living: грамматика grammar.ebnf (определённость, достижимость, разобранные LL(1)-конфликты)",
        "FAIL" if errs else "PASS", "; ".join(errs[:5]) if errs else "; ".join(info))
    if errs:
        return
    files = sorted((ROOT / "examples").rglob("*.bag"))
    bad = [f"{f.relative_to(ROOT)}: {r}" for f in files if (r := gl.check_file(g, f))]
    add("living: примеры examples/ распознаются грамматикой", "FAIL" if bad else ("PASS" if files else "SKIP"),
        "; ".join(bad[:4]) if bad else f"{len(files)} файлов")
    ok, total, problems = gl.check_corpus(g, ROOT / "conformance" / "cases")
    add("living: случаи parse корпуса согласованы с грамматикой и независимым лексером",
        "FAIL" if problems else ("PASS" if total else "SKIP"), "; ".join(problems[:4]) if problems else f"{ok}/{total}")


def check_ref_codes():
    reg = ROOT / "spec/diagnostics/registry.json"
    if not reg.is_file() or not (ROOT / "ref").is_dir():
        add("living: коды, которые выдаёт ref/, есть в DIAG-1", "SKIP", "NOT_RUN: нет реестра или ref/")
        return
    known = {c["code"] for c in json.loads(reg.read_text(encoding="utf-8"))["codes"]}
    # коды отказов и виды блокеров WorkState ("kind": "OBLIGATION_OPEN", CHG-13) — одни и те же имена DIAG-1
    pat = re.compile(r"""["']code["']\s*:\s*["']([A-Z][A-Z0-9_]+)["']|\bcode\s*=\s*["']([A-Z][A-Z0-9_]+)["']"""
                     r"""|\b(?:refused|HostStop|OpError|EditError)\(\s*["']([A-Z][A-Z0-9_]+)["']"""
                     r"""|["']kind["']\s*:\s*["']([A-Z][A-Z0-9_]+)["']|["'](?:OBLIGATION|CLAUSE)_([A-Z]+)["']""")
    used, missing = set(), []
    for f in (ROOT / "ref").rglob("*.py"):
        for m in pat.finditer(f.read_text(encoding="utf-8")):
            code = m.group(1) or m.group(2) or m.group(3) or m.group(4) or (
                m.group(0).strip("'\"") if m.group(5) else None)
            used.add(code)
            if code not in known:
                missing.append(f"{f.relative_to(ROOT)}: {code}")
    add("living: коды, которые выдаёт ref/, есть в DIAG-1", "FAIL" if missing else "PASS",
        "; ".join(missing[:6]) if missing else f"{len(used)} кодов")


CASE_SCHEMA_SCRIPT = r"""
import json, sys
from pathlib import Path
import jsonschema
from importlib.metadata import version
root = Path(sys.argv[1])
v = jsonschema.Draft202012Validator(json.loads((root / "conformance/schema/case.schema.json").read_text(encoding="utf-8")))
bad, n = [], 0
for cf in sorted((root / "conformance/cases").rglob("case.json")):
    n += 1
    bad += [f"{cf.parent.relative_to(root)}: {e.message[:80]}" for e in v.iter_errors(json.loads(cf.read_text(encoding="utf-8")))]
print(json.dumps({"n": n, "bad": bad, "version": version("jsonschema")}))
"""


def check_case_schema():
    name = "living: case.json по conformance/schema/case.schema.json"
    py, env, have = python_and_env()
    if not have:
        add(name, "SKIP", "NOT_RUN: нет jsonschema — bash tools/setup.sh")
        return
    r = subprocess.run([py, "-B", "-c", CASE_SCHEMA_SCRIPT, str(ROOT)], capture_output=True, text=True, env=env)
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        add(name, "ERROR", (r.stdout + r.stderr)[-200:])
        return
    add(name, "FAIL" if d["bad"] else ("PASS" if d["n"] else "SKIP"),
        "; ".join(d["bad"][:4]) if d["bad"] else f"{d['n']} случаев; jsonschema {d['version']}")


GRAPH_SCHEMA_SCRIPT = r"""
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root / "ref"))
sys.setrecursionlimit(100000)
import jsonschema
from bagaev_ref.links.extract import extract
from bagaev_ref.machine.runner import prepare
v = jsonschema.Draft202012Validator(json.loads((root / "spec/links/graph.schema.json").read_text(encoding="utf-8")))
bad, n = [], 0
for ex in sorted(p for p in (root / "examples").iterdir() if p.is_dir()):
    files = [(f.relative_to(ex).as_posix(), f.read_bytes()) for f in sorted(ex.rglob("*.bag"))]
    project, prog, pre = prepare(files)
    if pre is not None:
        bad.append(f"{ex.name}: не проходит проверку")
        continue
    n += 1
    bad += [f"{ex.name}: {e.message[:80]}" for e in v.iter_errors(extract(project, prog, files))]
import shutil, subprocess
if shutil.which("node"):                         # граф варианта B пилота — та же схема (links-ts/extract.ts)
    for app in ("pilot/authorship/app-ts", "pilot/authorship/reference/ts"):
        out = subprocess.run(["node", "--no-warnings", str(root / "pilot/authorship/links-ts/extract.ts"), str(root / app)],
                             capture_output=True, text=True)
        try:
            g = dict(json.loads(out.stdout), source="0" * 64)
        except ValueError:
            bad.append(f"{app}: извлекатель TS {out.stderr[-120:]}")
            continue
        n += 1
        bad += [f"{app}: {e.message[:80]}" for e in v.iter_errors(g)]
ops = json.loads((root / "spec/protocol/operations.schema.json").read_text(encoding="utf-8"))
vo = jsonschema.Draft202012Validator(ops)
sample = {"protocol": "bagaev-protocol/1", "operation": "accept", "change_id": "ch-x", "expected_work_revision": 2,
          "idempotency_key": "accept-key-000000001", "arguments": {}}
bad += [f"operations.schema: {e.message[:80]}" for e in vo.iter_errors(sample)]
if not list(vo.iter_errors({"protocol": "bagaev-protocol/1", "operation": "accept", "arguments": {}})):
    bad.append("operations.schema принимает запись без ключа и ревизии")
print(json.dumps({"n": n, "bad": bad}))
"""


def check_graph_schema():
    name = "exec: граф связей примеров по spec/links/graph.schema.json и схема операций протокола"
    py, env, have = python_and_env()
    if not have:
        add(name, "SKIP", "NOT_RUN: нет jsonschema — bash tools/setup.sh")
        return
    r = subprocess.run([py, "-B", "-c", GRAPH_SCHEMA_SCRIPT, str(ROOT)], capture_output=True, text=True, env=env)
    try:
        d = json.loads(r.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        add(name, "ERROR", (r.stdout + r.stderr)[-200:])
        return
    add(name, "FAIL" if d["bad"] else "PASS", "; ".join(d["bad"][:4]) if d["bad"] else f"{d['n']} примеров")


def check_conformance():
    conf = load_module("bagaev_conformance", ROOT / "conformance/run.py")
    errs = conf.lint()
    n = len(conf.load_cases())
    add("living: форма conformance-корпуса и манифеста правил", "FAIL" if errs else "PASS",
        "; ".join(errs[:6]) if errs else f"{n} случаев")


def check_pilot_ts(env):
    """Варианты A/B пилота: строгая проверка типов, тесты S0 и эталона, оракул на эталоне и мутантах."""
    tsc = ROOT / "pilot/writability/node_modules/typescript/bin/tsc"
    if shutil.which("node") is None or not tsc.is_file():
        add("exec: варианты A/B пилота на TypeScript (Ф7)", "SKIP", "NOT_RUN: нет node или компилятора TypeScript")
        return
    bad = []
    for app in ("pilot/authorship/app-ts", "pilot/authorship/reference/ts"):
        tc = subprocess.run(["node", str(tsc), "-p", str(ROOT / app / "tsconfig.json")], capture_output=True, text=True,
                            timeout=600)
        if tc.returncode != 0:
            bad.append(f"{app}: tsc {tc.stdout[-160:]}")
        tests = sorted(str(f) for f in (ROOT / app / "test").glob("*.test.ts"))
        tr = subprocess.run(["node", "--no-warnings", "--test", *tests], capture_output=True, text=True, timeout=600)
        if tr.returncode != 0:
            bad.append(f"{app}: node --test {tr.stdout[-160:]}")
    om = subprocess.run([sys.executable, "-B", str(ROOT / "pilot/authorship/oracle/mutants.py"), "--arm", "A"],
                        capture_output=True, text=True, env=env, timeout=3000)
    try:
        res = json.loads(om.stdout)
        missed = [k for k, v in res["mutants"].items() if not v["caught"]]
        detail = f"tsc и тесты S0 и эталона; эталон {res['reference']}; {len(res['mutants']) - len(missed)}/{len(res['mutants'])} мутантов пойманы"
        if missed:
            bad.append(f"пропущены мутанты {missed}")
    except (ValueError, KeyError):
        bad.append((om.stdout + om.stderr)[-200:])
        detail = ""
    add("exec: варианты A/B пилота на TypeScript (Ф7)", "FAIL" if bad or om.returncode != 0 else "PASS",
        "; ".join(bad) if bad else detail)


def check_pilot_mechanism(env):
    r = subprocess.run([sys.executable, "-B", str(ROOT / "pilot/authorship/mechanism/run.py")],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=1200)
    try:
        report = json.loads(r.stdout)
        skipped = [a for a, v in report["arms"].items() if v["outcome"] == "SKIP"]
        if (r.returncode == 0 and report["outcome"] == "PASS" and report["passed"] == report["total"] == 15
                and report["llm_calls"] == 0 and report["pilot_status"] == "NOT_RUN"):
            status = "PASS"
        elif r.returncode == 2 and report["outcome"] == "INCOMPLETE" and skipped:
            status = "SKIP"
        else:
            status = "FAIL"
        detail = f"{report['passed']}/{report['total']}; LLM-вызовов {report['llm_calls']}; пилот {report['pilot_status']}"
        if skipped:
            detail += f"; нет зависимостей для {', '.join(skipped)}"
        if status == "FAIL":
            detail += "; " + json.dumps({a: v for a, v in report["arms"].items() if v["outcome"] != "PASS"},
                                        ensure_ascii=False)[:1200]
    except (ValueError, KeyError, TypeError):
        status, detail = "FAIL", (r.stdout + r.stderr)[-1200:]
    add("exec: механизмы пилота C02/C03/C07/C09/C13 для A/B/C (без LLM)", status, detail)


def check_pilot_harness(env):
    """Ф7: реальные локальные инструменты и сбои без вызовов модели или исследовательских измерений."""
    missing = [name for name in ("node", "git", "bwrap") if shutil.which(name) is None]
    if not (ROOT / "pilot/writability/node_modules/typescript/bin/tsc").is_file():
        missing.append("typescript")
    if missing:
        add("exec: пробный харнесс пилота (Ф7)", "SKIP", "NOT_RUN: нет " + ", ".join(missing))
        return
    unit = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "pilot/harness/tests", "-v"],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    add("exec: регрессии харнесса пилота", "PASS" if unit.returncode == 0 else "FAIL",
        (unit.stdout + unit.stderr).strip()[-700:])
    with tempfile.TemporaryDirectory(prefix="bag-pilot-dry-run-") as tmp:
        out = Path(tmp) / "run"
        r = subprocess.run([sys.executable, "-B", str(ROOT / "pilot/harness/run.py"), "dry-run", "--output", str(out)],
                           cwd=ROOT, env=env, capture_output=True, text=True, timeout=1200)
        try:
            report = json.loads((out / "result.json").read_text(encoding="utf-8"))
            smoke, hooks = report["smoke"], report["hooks"]
            expected_hooks = {(arm, case) for arm in "ABC" for case in ("C04", "C05", "C06", "C07", "C09", "C12")}
            passed = (r.returncode == 0 and report["outcome"] == "PASS" and report["provider"] == "scripted"
                      and report["pilot_status"] == "NOT_RUN" and report["research_attempts"] == []
                      and report["llm_measurements"] is None
                      and len(smoke) == 9 and all(sum(s["arm"] == arm for s in smoke) == 3 for arm in "ABC")
                      and all(s["outcome"] == "PASS" for s in smoke + hooks)
                      and len(hooks) == 18 and {(h["arm"], h["case"]) for h in hooks} == expected_hooks
                      and report["posthoc_separation"]["scripted_false_accept_visible"] is True)
            detail = ("9 копий A/B/C, 18 hooks, отрицательный posthoc; пилот NOT_RUN, LLM-метрики null"
                      if passed else json.dumps(report.get("error", {"outcome": report["outcome"]}), ensure_ascii=False))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            passed = False
            detail = f"{type(exc).__name__}: {(r.stdout + r.stderr)[-300:]}"
    add("exec: пробный харнесс пилота (Ф7)", "PASS" if passed else "FAIL", detail)


def check_pilot_freeze():
    proto = "pilot/authorship/protocol.md"
    tags = [t for t in git("tag", "--list", "pilot-freeze-*").stdout.decode().split() if t]
    if not tags:
        add("living: протокол пилота после заморозки", "SKIP", "NOT_RUN: тегов pilot-freeze-* ещё нет")
        return
    if not (ROOT / proto).is_file():
        add("living: протокол пилота после заморозки", "FAIL", f"{proto} отсутствует, а теги {tags} есть")
        return
    changed = [t for t in tags if git("show", f"{t}:{proto}").stdout != (ROOT / proto).read_bytes()]
    # Поправка допустима, только если её файл появился после тега и прямо ссылается на него.
    unexplained = []
    for tag in changed:
        ok = False
        for a in (ROOT / "pilot/authorship/amendments").glob("*.md"):
            rel = a.relative_to(ROOT).as_posix()
            in_tag = git("cat-file", "-e", f"{tag}:{rel}").returncode == 0
            if not in_tag and tag in a.read_text(encoding="utf-8"):
                ok = True
        if not ok:
            unexplained.append(tag)
    add("living: протокол пилота после заморозки", "FAIL" if unexplained else "PASS",
        f"{proto} изменён после {unexplained} без поправки, ссылающейся на тег" if unexplained
        else f"теги {tags}; изменения {'оформлены поправками' if changed else 'нет'}")


def run_exec():
    r = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tools/tests", "-q"],
                       cwd=ROOT, capture_output=True, text=True, timeout=600)
    add("exec: тесты инструментов tools/tests", "PASS" if r.returncode == 0 else "FAIL",
        (r.stdout + r.stderr)[-400:])
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-q"],
                       cwd=ROOT / "ref", capture_output=True, text=True, env=env)
    tail = (r.stdout + r.stderr).strip().splitlines()
    add("exec: тесты эталона ref/tests", "PASS" if r.returncode == 0 else "FAIL",
        " | ".join(tail[-2:])[-240:])
    er = load_module("bagaev_exec_report", ROOT / "tools/exec_report.py")
    d = er.compute()                 # один прогон корпуса на каждую реализацию
    for impl, res in d["implementations"].items():
        if not res["available"]:
            add(f"exec: conformance --impl {impl}", "SKIP", "NOT_RUN: реализации ещё нет")
        elif res["total"] == 0:
            add(f"exec: conformance --impl {impl}", "SKIP", "NOT_RUN: корпус пуст (0/0 не PASS)")
        elif not res["failed"] and res["passed"] == 0:
            add(f"exec: conformance --impl {impl}", "SKIP",
                f"NOT_RUN: реализация ещё не поддерживает ни одной фазы корпуса ({res['not_run']}/{res['total']})")
        else:
            add(f"exec: conformance --impl {impl}", "FAIL" if res["failed"] else "PASS",
                f"{res['passed']}/{res['total']}; не прошли: {res['failed'][:6]}" if res["failed"]
                else f"{res['passed']}/{res['total']} случаев, NOT_RUN {res['not_run']}")
    br = subprocess.run([sys.executable, "-B", str(ROOT / "conformance/bridges/core01.py"), "--generated", "100", "--json"],
                        capture_output=True, text=True, env=env, timeout=600)
    try:
        rep = json.loads(br.stdout.strip().splitlines()[-1])
        detail = (f"корпус {rep['corpus']['PASS']} совпали (SKIP {rep['corpus']['SKIP']} — вне подмножества CORE); "
                  f"порождённые {rep['generated']['PASS']}/{sum(rep['generated'].values())}")
    except (ValueError, IndexError, KeyError):
        detail = (br.stdout + br.stderr)[-240:]
    add("exec: мост MACHINE-1 ↔ CORE-0.1 (замороженный исполнитель R07)", "PASS" if br.returncode == 0 else "FAIL", detail)
    mu = subprocess.run([sys.executable, "-B", str(ROOT / "conformance/bridges/mutants.py"), "--generated", "20"],
                        capture_output=True, text=True, env=env, timeout=900)
    try:
        res = json.loads(mu.stdout)
        missed = [k for k, v in res.items() if not v["caught"]]
        detail = f"{len(res) - len(missed)}/{len(res)} мутаций пойманы" + (f"; пропущены: {missed}" if missed else "")
    except ValueError:
        detail = (mu.stdout + mu.stderr)[-240:]
    add("exec: мутационная проверка машины и понижения", "PASS" if mu.returncode == 0 else "FAIL", detail)
    tx = subprocess.run([sys.executable, "-B", str(ROOT / "conformance/bridges/authtx.py")],
                        capture_output=True, text=True, env=env, timeout=600)
    try:
        rep = json.loads(tx.stdout)
        detail = (f"A01–A12: совпали {rep['MATCH']}, отклонения HOST-1 {rep['DEVIATION']}, расхождения {rep['DIVERGENCE']}; "
                  f"шагов сравнено {rep['steps_compared']}/{rep['steps_total']}, неприменимы {rep['steps_not_applicable']}")
    except (ValueError, KeyError):
        detail = (tx.stdout + tx.stderr)[-240:]
    add("exec: мост HOST-1 ↔ AUTH-TX-0.1 (замороженная модель R07)", "PASS" if tx.returncode == 0 else "FAIL", detail)
    hm = subprocess.run([sys.executable, "-B", str(ROOT / "conformance/bridges/host_mutants.py")],
                        capture_output=True, text=True, env=env, timeout=1200)
    try:
        res = json.loads(hm.stdout)
        missed = [k for k, v in res.items() if not v["caught"]]
        detail = f"{len(res) - len(missed)}/{len(res)} мутаций HOST-1 пойманы корпусом" + (f"; пропущены: {missed}" if missed else "")
    except ValueError:
        detail = (hm.stdout + hm.stderr)[-240:]
    add("exec: мутационная проверка хоста (store/events/migrate)", "PASS" if hm.returncode == 0 else "FAIL", detail)
    iv = subprocess.run([sys.executable, "-B", str(ROOT / "conformance/tools/incremental_vs_full.py")],
                        capture_output=True, text=True, env=env, timeout=1200)
    try:
        rep = json.loads(iv.stdout)
        detail = (f"правок {rep['steps']}, графы равны {rep['equal']}; неисправности штампа пойманы: "
                  + ", ".join(f"{k} — {v['first']}" for k, v in rep["faults"].items() if v["detected"]))
    except (ValueError, KeyError):
        detail = (iv.stdout + iv.stderr)[-240:]
    add("exec: инкрементальное извлечение графа = полное (LNK-08-18)", "PASS" if iv.returncode == 0 else "FAIL", detail)
    lm = subprocess.run([sys.executable, "-B", str(ROOT / "conformance/bridges/links_mutants.py")],
                        capture_output=True, text=True, env=env, timeout=1800)
    try:
        res = json.loads(lm.stdout)
        missed = [k for k, v in res.items() if not v["caught"]]
        detail = f"{len(res) - len(missed)}/{len(res)} мутаций LINKS-1 пойманы корпусом" + (f"; пропущены: {missed}" if missed else "")
    except ValueError:
        detail = (lm.stdout + lm.stderr)[-240:]
    add("exec: мутационная проверка связей (graph/impact/context)", "PASS" if lm.returncode == 0 else "FAIL", detail)
    check_graph_schema()
    cm = subprocess.run([sys.executable, "-B", str(ROOT / "conformance/bridges/change_mutants.py")],
                        capture_output=True, text=True, env=env, timeout=3000)
    try:
        res = json.loads(cm.stdout)
        missed = [k for k, v in res.items() if not v["caught"]]
        detail = f"{len(res) - len(missed)}/{len(res)} мутаций CHANGE-1 пойманы корпусом" + (f"; пропущены: {missed}" if missed else "")
    except ValueError:
        detail = (cm.stdout + cm.stderr)[-240:]
    add("exec: мутационная проверка изменения (edit/accept/protocol)", "PASS" if cm.returncode == 0 else "FAIL", detail)
    mc = subprocess.run([sys.executable, "-B", "-m", "bagaev_ref", "mcp", str(ROOT / "conformance/cases/accept/flow-01"),
                         "--selftest", "--json"], capture_output=True, text=True, env=dict(env, PYTHONPATH=str(ROOT / "ref")),
                        timeout=600)
    try:
        rep = json.loads(mc.stdout)
        detail = f"{rep['outcome']}: шагов {rep['steps']}, инструментов {rep['tools']}, MCP {rep['mcp_protocol']}"
    except (ValueError, KeyError):
        detail = (mc.stdout + mc.stderr)[-240:]
    add("exec: паритет транспортов MCP stdio и CLI (CHG-20)", "PASS" if mc.returncode == 0 else "FAIL", detail)
    om = subprocess.run([sys.executable, "-B", str(ROOT / "pilot/authorship/oracle/mutants.py"), "--arm", "C"],
                        capture_output=True, text=True, env=env, timeout=3000)
    try:
        res = json.loads(om.stdout)
        missed = [k for k, v in res["mutants"].items() if not v["caught"]]
        detail = (f"эталон {res['reference']}; {len(res['mutants']) - len(missed)}/{len(res['mutants'])} мутантов изменения "
                  f"пойманы оракулом" + (f"; пропущены: {missed}" if missed else ""))
    except (ValueError, KeyError):
        detail = (om.stdout + om.stderr)[-240:]
    add("exec: оракул пилота на эталоне варианта C и его мутантах (Ф7)", "PASS" if om.returncode == 0 else "FAIL", detail)
    check_pilot_ts(env)
    check_pilot_mechanism(env)
    check_pilot_harness(env)
    stored = er.OUT.read_text(encoding="utf-8") if er.OUT.is_file() else ""
    add("exec: registry/exec-progress.json актуален", "PASS" if stored == er.render(d) else "FAIL",
        er.line(d) if stored == er.render(d) else "устарел — python3 tools/exec_report.py")


# --------------------------------------------------------------------------- модели
def model_checks(rep: Path) -> list[dict]:
    m = []

    def add_m(model, cwd, argv, deps=False, prepare=None):
        m.append({"name": f"models/{model}: {cwd}/{argv[0]}", "model": model, "cwd": cwd, "argv": argv,
                  "deps": deps, "prepare": prepare})

    for e in ["authorship-transition", "call-profile", "core-machine", "data-core", "law-profile",
              "link-model", "observation-profile"]:
        add_m("r07-core", f"experiments/{e}", ["verify.py"])
    return m


KNOWN: dict[str, str] = {}   # разобранные расхождения моделей (сейчас нет; E-T3 снято)


def python_and_env():
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    py = str(VENV_PY) if VENV_PY.is_file() else sys.executable
    paths = [str(d) for d in (LOCAL_DEPS,) if (d / "jsonschema").is_dir()]
    if paths:
        env["PYTHONPATH"] = os.pathsep.join(paths + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    have = subprocess.run([py, "-c", "import jsonschema"], env=env, capture_output=True).returncode == 0
    return py, env, have


def run_models(timeout: int, keep: bool, evidence: bool = False):
    py, env, have_deps = python_and_env()
    work = Path(tempfile.mkdtemp(prefix="bagaev-models-"))
    rep = work / "reports"
    rep.mkdir()
    try:
        for ch in model_checks(rep):
            if ch["deps"] and not have_deps:
                add(ch["name"], "SKIP", "нет pinned jsonschema: bash tools/setup.sh")
                continue
            base = work / ch["model"]
            if not base.exists():
                shutil.copytree(ROOT / "models" / ch["model"], base)
            if ch["prepare"] and ch["prepare"].startswith("mkdir:"):
                (base / ch["prepare"][6:]).mkdir(parents=True, exist_ok=True)
            elif ch["prepare"]:
                (base / ch["prepare"]).unlink(missing_ok=True)
            t0 = time.monotonic()
            try:
                r = subprocess.run([py, *ch["argv"]], cwd=base / ch["cwd"], env=env, capture_output=True,
                                   text=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                add(ch["name"], "ERROR", f"timeout {timeout}s")
                continue
            tail = " | ".join((r.stdout + r.stderr).strip().splitlines()[-2:])[-240:]
            if r.returncode == 0:
                add(ch["name"], "PASS", tail, seconds=round(time.monotonic() - t0, 1))
            elif ch["name"] in KNOWN:
                add(ch["name"], "KNOWN", KNOWN[ch["name"]])
            else:
                add(ch["name"], "FAIL", f"exit {r.returncode}: {tail}")
    finally:
        if evidence:
            dest = ROOT / "evidence" / time.strftime("%Y%m%dT%H%M%S")
            shutil.copytree(rep, dest)
            print(f"отчёты моделей сохранены: {dest.relative_to(ROOT)}", file=sys.stderr)
        if keep:
            print(f"копия моделей сохранена: {work}", file=sys.stderr)
        else:
            shutil.rmtree(work, ignore_errors=True)


# --------------------------------------------------------------------------- история
def git(*a, **kw):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, **kw)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exec", action="store_true", help="тесты эталона, conformance-корпус и EXEC-1")
    ap.add_argument("--models", action="store_true", help="запустить исследовательские модели")
    ap.add_argument("--all", action="store_true", help="--exec --models")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--keep", action="store_true", help="не удалять временные копии")
    ap.add_argument("--evidence", action="store_true",
                    help="с --models: сохранить отчёты моделей в evidence/<время>/ (каталог вне git)")
    ap.add_argument("--json", type=Path, help="записать сводку в файл (вне репозитория)")
    a = ap.parse_args()
    if a.all:
        a.exec = a.models = True

    check_links()
    check_json()
    check_no_model_copies()
    check_track()
    check_ledger_views()
    check_diagnostics()
    check_conformance()
    check_case_schema()
    check_grammar()
    check_ref_codes()
    check_pilot_freeze()
    if a.exec:
        run_exec()
    if a.models:
        run_models(a.timeout, a.keep, a.evidence)

    summary = {s: sum(1 for r in results if r["status"] == s) for s in ("PASS", "FAIL", "ERROR", "SKIP", "KNOWN", "INFO")}
    out = {"root": str(ROOT), "summary": summary, "results": results}
    if a.json:
        a.json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["FAIL"] == summary["ERROR"] == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(2)
