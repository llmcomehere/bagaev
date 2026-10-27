#!/usr/bin/env python3
"""Мутационная проверка корпуса связей (Ф5): заведомая порча правила LINKS-1 должна давать FAIL хотя бы одного
случая conformance/cases/{graph,impact,context}. Мутант — копия пакета эталона во временном каталоге с одной
текстовой заменой; файлы репозитория не меняются.

  python3 conformance/bridges/links_mutants.py
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
AREAS = ("graph", "impact", "context")
_spec = importlib.util.spec_from_file_location("bagaev_conformance_lm", ROOT / "conformance" / "run.py")
_conf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_conf)

# (имя, правило, файл пакета, заменяемый фрагмент, замена)
MUTANTS = [
    ("references_dropped", "LNK-08-04", "links/extract.py",
     'self.edge("calls" if callee else "references", src,', 'callee and self.edge("calls", src,'),
    ("canon_keeps_positions", "LNK-08-02", "links/extract.py", '"op_start", "brace"}', '"brace"}'),
    ("seed_ignores_edges", "LNK-08-13", "links/impact.py", "    for kind, src, dst in sorted(kb ^ kc):",
     "    for kind, src, dst in []:"),
    ("budget_ignored", "LNK-08-14", "links/impact.py", "if budget is not None and steps >= budget:", "if False:"),
    ("blocked_treated_affected", "LNK-08-14", "links/impact.py", "            mode = UNKNOWN", "            mode = AFFECTED"),
    ("test_store_propagates", "LNK-08-12", "links/graph.py",
     'return not (src_kind == "test" and e["kind"] in ("reads", "writes", "emits"))', "return True"),
    ("certificate_without_passing_tests", "LNK-08-15", "links/certs.py",
     'if evidence.get(ct["name"]) != "PASS":', "if False:"),
    ("obligations_candidate_only", "LNK-08-17", "links/impact.py",
     "    pairs = base.declared_pairs() | cand.declared_pairs()", "    pairs = cand.declared_pairs()"),
    ("excluded_without_closure", "LNK-08-16", "links/certs.py",
     'changed = sorted(k for k in ("rev", "closure", "extractor_rev") if basis["premises"].get(k) != now[k])',
     'changed = sorted(k for k in ("rev", "extractor_rev") if basis["premises"].get(k) != now[k])'),
    ("std_edges_dropped", "LNK-08-03", "links/extract.py",
     'dst = "std:" + info.qname if info.module.is_std else self.fn_id(info)', 'dst = None if info.module.is_std else self.fn_id(info)'),
    ("migrates_not_propagating", "LNK-08-12", "links/graph.py", '"migrates": "dst", ', ""),
    ("certificate_ignores_sig", "LNK-08-15", "links/certs.py",
     'if bx is None or cx is None or bx.get("sig") != cx.get("sig") or', 'if bx is None or cx is None or'),
    ("certificate_trusts_candidate_tests", "LNK-08-15", "links/certs.py",
     'if ct is None or ct["rev"] != bt["rev"] or t in seeds or', 'if ct is None or'),
    ("unavailable_not_seeded", "LNK-08-14", "links/impact.py",
     'for eid in sorted(blocked & known)]', 'for eid in []]'),
    ("unknown_never_upgraded", "LNK-08-14", "links/impact.py",
     'if eid in state and (state[eid] <= mode or eid in blocked):', 'if eid in state:'),
    ("context_boundary_first", "LNK-08-20", "links/context.py",
     'out += [(3, 1, b, "boundary") for b in sorted(boundary)]', 'out += [(1, 0, b, "boundary") for b in sorted(boundary)]'),
    ("envelope_drops_obligations", "LNK-08-19", "links/context.py",
     '"obligations": [[o["target"], o["source"], o["kind"], o["status"]] for o in report["obligations"]',
     '"obligations": [[o["target"], o["source"], o["kind"], o["status"]] for o in []'),
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
