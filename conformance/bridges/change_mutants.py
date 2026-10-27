#!/usr/bin/env python3
"""Мутационная проверка корпуса изменения (Ф6): заведомая порча правила CHANGE-1 должна давать FAIL хотя бы одного
случая conformance/cases/{edit,accept,protocol}. Мутант — копия пакета эталона во временном каталоге с одной
текстовой заменой; файлы репозитория не меняются.

  python3 conformance/bridges/change_mutants.py
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
AREAS = ("edit", "accept", "protocol")
_spec = importlib.util.spec_from_file_location("bagaev_conformance_cm", ROOT / "conformance" / "run.py")
_conf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_conf)

# (имя, правило, файл пакета, заменяемый фрагмент, замена)
MUTANTS = [
    ("stale_source_ignored", "CHG-04", "change/sourceedit.py",
     'elif f["base_sha256"] != hashlib.sha256(files[path]).hexdigest():', "elif False:"),
    ("old_text_first_match", "CHG-04", "change/sourceedit.py", "            if len(found) != 1:", "            if len(found) == 0:"),
    ("overlapping_occurrences_missed", "CHG-04", "change/sourceedit.py",
     "        i = data.find(sub, i + 1)", "        i = data.find(sub, i + len(sub))"),
    ("path_aliases_allowed", "CHG-03", "change/sourceedit.py",
     '    return all(SEGMENT_RE.fullmatch(x) for x in path.split("/"))', "    return True"),
    ("overlap_allowed", "CHG-04", "change/sourceedit.py",
     "            raise EditError(\"OVERLAPPING_EDITS\", path=path, edits=[a[3], b[3]])", "            pass"),
    ("utf8_boundary_ignored", "CHG-04", "change/sourceedit.py",
     "if not (0 <= s <= t <= len(data)) or not _boundary(data, s) or not _boundary(data, t):",
     "if not (0 <= s <= t <= len(data)):"),
    ("silent_removal_allowed", "CHG-06", "change/identity.py", "    if silent:", "    if False:"),
    ("duplicate_id_allowed", "CHG-06", "change/identity.py", "    if dup:", "    if False:"),
    ("retired_id_allowed", "CHG-06", "change/identity.py", "    if retired:", "    if False:"),
    ("kind_change_allowed", "CHG-06", "change/identity.py", "    if kinds:", "    if False:"),
    ("changed_tests_count", "CHG-13", "change/verify.py",
     'if c is not None and c["rev"] == base_g.nodes[t]["rev"] and target in cand_g.linked(t, "checks"):',
     "if c is not None:"),
    ("weakened_test_ignored", "CHG-13", "change/verify.py", "    if undeclared:", "    if False:"),
    ("new_rule_clause_ignored", "CHG-13", "change/verify.py",
     '    new = sorted(t for t in cand_g.checkers(target) if t not in unchanged and cand_g.nodes[t]["name"] in named)',
     "    new = []"),
    ("d83a_policy_ignored", "CHG-10", "change/verify.py",
     'if not pair["reason"].startswith("D83a") or "D83a" in allowed:', "if True:"),
    ("evidence_always_applicable", "CHG-12", "change/verify.py",
     '        applicability, basis = "stale", None', '        applicability, basis = "applicable", "any"'),
    ("fail_not_contradiction", "CHG-12", "change/verify.py",
     'if any(a["verdict"] in ("FAIL", "ERROR") for a in good):', "if False:"),
    ("scope_ignored", "CHG-09", "change/workstate.py", "        if outside:", "        if False:"),
    ("scope_by_any_name", "CHG-09", "change/workstate.py",
     '            return i in contract["allowed"] or all(g.nodes[i]["name"] in contract["allowed"]',
     '            return i in contract["allowed"] or any(g.nodes[i]["name"] in contract["allowed"]'),
    ("unlinked_fail_ignored", "CHG-13", "change/workstate.py",
     '        if verdict in ("FAIL", "ERROR"):\n            blockers.append({"kind": "EVIDENCE_CONTRADICTED"',
     '        if False:\n            blockers.append({"kind": "EVIDENCE_CONTRADICTED"'),
    ("tests_not_run_ignored", "CHG-13", "change/workstate.py", "    if not_run:", "    if False:"),
    ("policy_not_pinned", "CHG-10", "change/workstate.py", '    if contract.get("policy") != out["policy"]:', "    if False:"),
    ("policy_obligations_crash", "CHG-10", "change/workstate.py",
     '    rest = {k: v for k, v in pol.items() if k != "obligations"}', "    rest = pol"),
    ("clause_removal_without_reason", "CHG-09", "change/contract.py",
     'if not isinstance(cid, str) or cid not in by_id or not isinstance(reason, str) or not reason:',
     "if not isinstance(cid, str) or cid not in by_id:"),
    ("replace_test_without_reason", "CHG-09", "change/contract.py",
     'test, reason = op.get("test"), _reason(op, k)', 'test, reason = op.get("test"), op.get("reason")'),
    ("accept_ignores_head", "CHG-16", "change/accept.py", "    if head != w[\"base\"]:\n        raise OpError(\"STALE_BASE\"",
     "    if False:\n        raise OpError(\"STALE_BASE\""),
    ("accept_ignores_blockers", "CHG-16", "change/accept.py", "    if blockers:", "    if False:"),
    ("receipt_after_guards", "CHG-15", "protocol/ops.py",
     "            if r is not None:                            # квитанция ищется до guard'ов (R16 §7)",
     "            if r is not None and False:"),
    ("digest_without_revision", "CHG-15", "protocol/ops.py",
     '"expected_work_revision": str(req.get("expected_work_revision")),', ""),
    ("work_revision_unchecked", "CHG-15", "protocol/ops.py",
     'if w["work_revision"] != req["expected_work_revision"]:', "if False:"),
    ("authority_ignored", "CHG-14", "protocol/ops.py", "    if ps is None:\n        return True", "    if True:\n        return True"),
    ("rebase_spans_allowed", "CHG-18", "change/accept.py",
     'elif cur is not None and "edits" in f and all("old_text" in e for e in f["edits"]):',
     'elif cur is not None and "edits" in f:'),
    ("search_selects", "CHG-19", "protocol/search.py", '"selection": "none",\n', '"selection": "top",\n'),
    ("rebase_drops_assigned_ids", "CHG-18", "change/accept.py",
     "                files[path] = I.place_ids(files[path], path, ids)", "                files[path] = files[path]"),
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
