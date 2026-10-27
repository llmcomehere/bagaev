"""Случаи conformance фаз graph, impact, context (conformance/README.md §Связи).

`run.links` задаёт операцию над программой корня случая и, для влияния, кандидатом из подкаталога. Наблюдение —
проекция отчёта по именам сущностей (не по дайджестам), форма — spec/links/08-bagaev-extraction.md §7.
"""
from __future__ import annotations

from bagaev_ref.links.context import context_pack
from bagaev_ref.links.extract import extract
from bagaev_ref.links.graph import Graph, relations, resolve
from bagaev_ref.links import certs
from bagaev_ref.links.impact import impact, why_affected, why_not


def program(files, prefix: str, others: set):
    from bagaev_ref.machine.runner import prepare
    pre = prefix.rstrip("/") + "/" if prefix else ""
    sub = [(f[len(pre):], b) for f, b in files if f.startswith(pre) and f.endswith(".bag")
           and not (not prefix and f.split("/", 1)[0] in others)]
    project, prog, obs = prepare(sub)
    return (None, None, obs) if obs is not None else (project, prog, sub)


def name(g: Graph, eid):
    return g.nodes[eid]["name"] if eid in g.nodes else eid


def run_links_case(files, case: dict) -> dict:
    spec = case.get("run", {}).get("links", {})
    phase = case["expect"]["phase"]
    others = {p for p in (spec.get("candidate"), spec.get("recheck")) if p}
    project, prog, sub = program(files, "", others)
    if project is None:
        return {"phase": phase, "outcome": "PRELAUNCH", "diagnostics": sub.get("diagnostics", [])}
    base = Graph(extract(project, prog, sub), "base")
    op = spec.get("op", phase)
    if op == "graph":
        e_kinds = None if spec.get("include_defines") else {k for k in base.coverage["kinds"] if k != "defines"}
        edges = sorted({(e["kind"], name(base, e["src"]), name(base, e["dst"]) if e["dst"] else None)
                        for e in base.data["edges"] if e_kinds is None or e["kind"] in e_kinds},
                       key=lambda x: tuple("" if v is None else v for v in x))
        return {"phase": phase, "outcome": "GRAPH", "value": {
            "nodes": sorted([n["name"], n["kind"]] for n in base.data["nodes"]),
            "edges": [list(x) for x in edges],
            "coverage": {k: v["status"] for k, v in sorted(base.coverage["kinds"].items())},
            "gaps": sorted([name(base, g["entity"]), g["reason"]] for g in base.data["gaps"]),
            "unused_atoms": sorted([name(base, u["entity"]), u["atom"]] for u in base.data["unused_atoms"])}}
    if op == "relations":
        r = relations(base, resolve(base, spec["entity"]), spec.get("direction", "both"))
        return {"phase": phase, "outcome": "RELATIONS", "value": {
            "outgoing": sorted({(e["kind"], name(base, e["dst"])) for e in r.get("outgoing", [])}),
            "incoming": sorted({(e["kind"], name(base, e["src"])) for e in r.get("incoming", [])})}}
    cproject, cprog, csub = program(files, spec["candidate"], set())
    if cproject is None:
        return {"phase": phase, "outcome": "PRELAUNCH", "diagnostics": csub.get("diagnostics", [])}
    cand = Graph(extract(cproject, cprog, csub), "candidate")
    ids = lambda names: [resolve(cand, n) or resolve(base, n) for n in names]
    evidence = None
    if spec.get("with_tests"):
        from bagaev_ref.machine.runner import run_tests
        evidence = {t["test"]: t["status"] for t in run_tests(csub).get("tests", [])}
    r = impact(base, cand, spec.get("budget"), ids(spec.get("unavailable", [])), evidence)
    if op == "impact":
        return {"phase": phase, "outcome": "IMPACT", "value": project_report(r, base, cand, spec)}
    if op == "why":
        eid = ids([spec["entity"]])[0]
        out = why_affected(r, eid) if spec.get("affected") else why_not(r, eid)
        v = {"outcome": out["outcome"]}
        if "path" in out:
            v["path"] = [[p["name"], (p["via"] or {}).get("kind"), (p["via"] or {}).get("side")] for p in out["path"]]
            v["status"] = out["status"]
        if "basis" in out:
            v["basis"] = [b["certificate"] for b in out["basis"]]
            if spec.get("recheck"):
                rp, rg, rs = program(files, spec["recheck"], set())
                g2 = Graph(extract(rp, rg, rs), "recheck")
                v["recheck"] = [certs.revalidate(b, g2, eid)["applicability"] for b in out["basis"]]
        if "cause" in out:
            v["cause"] = out["cause"]
        return {"phase": phase, "outcome": "WHY", "value": v}
    if op == "context":
        bf, cf = dict(sub), dict(csub)
        p = context_pack(r, base, cand, bf, cf, spec["context_budget"], spec.get("cursor", 0))
        if p["outcome"] != "CONTEXT":
            return {"phase": phase, "outcome": p["outcome"], "code": p["code"]}
        return {"phase": phase, "outcome": "CONTEXT", "value": {
            "ready_for_step": p["ready_for_step"], "blockers": p["blockers"], "next_cursor": p["next_cursor"],
            "within_budget": p["used"] <= p["budget"],
            "coverage": [[c["name"], c["coverage"]] + ([c["reason"]] if "reason" in c else []) for c in p["coverage"]],
            "obligations": len(p["envelope"]["obligations"])}}
    raise ValueError(op)


def project_report(r: dict, base: Graph, cand: Graph, spec: dict) -> dict:
    watch = {}
    for n in spec.get("watch", []):
        eid = resolve(cand, n) or resolve(base, n)
        st = ("in_scope" if any(x["id"] == eid for x in r["in_scope"]) else
              "frontier" if any(x["id"] == eid for x in r["frontier"]) else
              "unknown" if any(x["id"] == eid for x in r["unknown"]) else "excluded_with_basis")
        if st == "excluded_with_basis":
            st = [st] + [b["certificate"] for x in r["excluded_with_basis"] if x["id"] == eid for b in x["basis"]]
        watch[n] = st
    return {
        "status": r["status"], "readiness": r["readiness"],
        "seeds": [[s["name"], s["seed"]] for s in r["seeds"]],
        "in_scope": sorted([x["name"], x["distance"]] for x in r["in_scope"]),
        "unknown": sorted([x["name"], x["cause"]] for x in r["unknown"] if x["cause"] != "ANALYSIS_INCOMPLETE"),
        "unknown_incomplete": sum(1 for x in r["unknown"] if x["cause"] == "ANALYSIS_INCOMPLETE"),
        "frontier": sorted(x["name"] for x in r["frontier"]),
        "obligations": sorted([o["target_name"], o["source_name"], o["kind"], o["status"], o["sides"]]
                              for o in r["obligations"] if o["status"] != "excluded_with_basis"),
        "closed": sorted([o["target_name"], o["source_name"], o["kind"], o["reason"]]
                         for o in r["obligations"] if o.get("reason") == "D83a-interface-contract"),
        "tests_to_run": r["tests_to_run"],
        "gaps": sorted([g["name"], g["reason"]] for g in r["gaps"]),
        "watch": watch}
