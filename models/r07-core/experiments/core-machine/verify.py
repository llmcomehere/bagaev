#!/usr/bin/env python3
"""Hash-bound finite CORE verification: authored traces + independent derivations.

The frozen CEK engine and the independent oracle are both executed.  Equality
between them alone is insufficient: finite stopping outcomes are also derived
from manually authored full traces.  No bagaev program, host effect, universal
proof, source compiler or V1 acceptance test is executed by this script.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys
import time
import types

import engine
import oracle


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_REF = "fixtures/core-machine.json"
SOURCE_REFS = (
    "experiments/core-machine/engine.py", "experiments/core-machine/API.md",
    "experiments/core-machine/README.md", "experiments/core-machine/oracle.py",
    "experiments/core-machine/verify.py", FIXTURE_REF,
)
FORMS = {"const", "var", "let", "if", "lambda", "call", "letrec", "prim", "result", "match_result"}
RULES = {"CONST", "VAR", "LAMBDA", "LET_ENTER", "LET_BIND", "IF_ENTER", "IF_THEN",
         "IF_ELSE", "LETREC", "CALL_ENTER", "CALL_ARGS", "CALL_NEXT", "CALL_BODY",
         "PRIM_ENTER", "PRIM_NEXT", "PRIM_APPLY", "RESULT_ENTER", "RESULT_WRAP",
         "MATCH_ENTER", "MATCH_OK", "MATCH_ERR"}
PRIMITIVES = {"i64.eq", "i64.lt", "i64.add", "i64.sub", "i64.div", "i64.rem"}
OBSERVATION_FIELDS = {"profile_revision", "content_digest", "termination", "code",
                      "value", "steps", "remaining", "trace", "cancel_request_id"}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def digest(value):
    return sha256(encoded(value).encode("utf-8")).hexdigest()


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def equal(actual, expected, detail=""):
    if encoded(actual) != encoded(expected):
        raise AssertionError(f"{detail}: actual={actual!r}; expected={expected!r}")


def model_program(raw):
    return engine.decode_program(raw)


def model_run(raw, budget, cancel_at=None, cancel_request_id="cancel", module=engine):
    result = module.run(module.decode_program(raw), budget,
                        cancel_at=cancel_at, cancel_request_id=cancel_request_id)
    return module.execution_json(result)


def full_trace(pairs):
    return [{"step_index": i + 1, "rule": rule, "node_id": node}
            for i, (rule, node) in enumerate(pairs)]


def authored_value(row):
    raw = json.dumps(row["expected"]["value"], ensure_ascii=False)
    return json.loads(raw.replace("$content_digest", oracle.artifact_digest(row["program"])))


def authored_cut(row, budget, cancel_at=None, cancel_request_id="cancel"):
    """Apply the published stopping precedence to a manually written full trace."""
    cost = row["expected"]["steps"]
    pairs = row["expected"]["trace"]
    require(cost == len(pairs), "authored cost must equal authored full trace length")
    if cost <= budget and (cancel_at is None or cost <= cancel_at):
        steps, termination, code = cost, "RETURNED", "RETURNED"
        value, cancellation = authored_value(row), None
    else:
        steps = budget if cancel_at is None else min(budget, cancel_at)
        cancelled = cancel_at is not None and cancel_at <= budget
        termination = "SEMANTIC_STOP"
        code = "CANCELLED" if cancelled else "BUDGET_EXCEEDED"
        value, cancellation = None, cancel_request_id if cancelled else None
    return {"profile_revision": oracle.PROFILE_REVISION,
            "content_digest": oracle.artifact_digest(row["program"]),
            "termination": termination, "code": code, "value": value,
            "steps": steps, "remaining": budget - steps,
            "trace": full_trace(pairs[:steps]), "cancel_request_id": cancellation}


def compare_three(row, budget, cancel_at=None, cancel_request_id="cancel"):
    actual = model_run(row["program"], budget, cancel_at, cancel_request_id)
    independent = oracle.run(row["program"], budget, cancel_at=cancel_at,
                             cancel_request_id=cancel_request_id)
    expected = authored_cut(row, budget, cancel_at, cancel_request_id)
    equal(sorted(actual), sorted(OBSERVATION_FIELDS), "complete public field set")
    equal(actual, independent, "CEK versus independent derivation, whole observation")
    equal(actual, expected, "whole observation versus independently authored trace/outcome")
    equal(independent, expected, "independent derivation versus authored trace/outcome")
    return actual, independent, expected


def diagnostic(action, code, kind="PrelaunchDiagnostic"):
    try:
        action()
    except engine.CoreError as error:
        equal(error.code, code, "diagnostic code")
        equal(error.kind, kind, "diagnostic category")
        return {"code": error.code, "kind": error.kind, "path": list(error.path),
                "detail": error.detail}
    raise AssertionError("expected diagnostic " + code)


def checked(identifier, action):
    try:
        return {"id": identifier, "status": "PASS", "details": action()}
    except Exception as error:
        return {"id": identifier, "status": "FAIL", "error": repr(error)}


def section(rows):
    return {"checks": len(rows), "passed": sum(r["status"] == "PASS" for r in rows),
            "failed": sum(r["status"] != "PASS" for r in rows), "rows": rows}


def authored_programs(fixtures):
    def one(row):
        prepared = engine.prepare(model_program(row["program"]))
        equal(engine.type_json(prepared.result_type), row["program"]["result_type"],
              "whole-program declared result type")
        actual, independent, expected = compare_three(row, row["expected"]["steps"])
        return {"focus": row["focus"], "expected": expected, "actual": actual,
                "independent_oracle": independent,
                "whole_observation_sha256": digest(actual)}
    return section([checked(row["id"], lambda row=row: one(row)) for row in fixtures["programs"]])


def negative_programs(fixtures):
    return section([checked(row["id"], lambda row=row: {
        "focus": row["focus"], "expected_code": row["expected_code"],
        "actual": diagnostic(lambda: engine.prepare(model_program(row["program"])),
                             row["expected_code"], row["expected_kind"]),
        "semantic_execution_started": False,
    }) for row in fixtures["negative_programs"]])


def matrix_case(row, budget, cancel_at, request):
    actual, independent, expected = compare_three(row, budget, cancel_at, request)
    return {"program_id": row["id"], "budget": budget, "cancel_at": cancel_at,
            "cancel_request_id": request, "code": actual["code"],
            "steps": actual["steps"], "remaining": actual["remaining"],
            "actual_sha256": digest(actual), "oracle_sha256": digest(independent),
            "authored_sha256": digest(expected), "whole_fields_equal": True}


def bounded_matrix(fixtures):
    domain = fixtures["bounded_matrix"]
    programs = {r["id"]: r for r in fixtures["programs"]}
    require(len(programs) == len(fixtures["programs"]), "duplicate authored program ID")
    for values in (domain["program_ids"], domain["budgets"], domain["cancel_at"]):
        require(len(values) == len({encoded(v) for v in values}), "duplicate finite domain input")
    expected_count = len(domain["program_ids"]) * len(domain["budgets"]) * len(domain["cancel_at"])
    rows, failures = [], []
    for identifier in domain["program_ids"]:
        for budget in domain["budgets"]:
            for cancel_at in domain["cancel_at"]:
                try:
                    rows.append(matrix_case(programs[identifier], budget, cancel_at,
                                             domain["cancel_request_id"]))
                except Exception as error:
                    failures.append({"program_id": identifier, "budget": budget,
                                     "cancel_at": cancel_at, "error": repr(error)})
    require(len(rows) + len(failures) == expected_count, "finite product not fully enumerated")
    return {"status": "PASS" if not failures else "FAIL", "domain": domain,
            "case_count": expected_count, "whole_field_matches": len(rows),
            "mismatches": len(failures), "outcomes": dict(sorted(Counter(r["code"] for r in rows).items())),
            "rows": rows, "failures": failures}


def boundary_cuts(fixtures):
    rows = []
    for row in fixtures["programs"]:
        n = row["expected"]["steps"]
        inputs = {(n, None), (n - 1, None), (n + 1, None), (n, 0), (n, n - 1),
                  (n, n), (n, n + 1), (n - 1, n - 1), (0, 0)}
        for budget, cancellation in sorted(inputs, key=lambda p: (p[0], -1 if p[1] is None else p[1])):
            rows.append(matrix_case(row, budget, cancellation, "boundary-cancel"))
    return {"case_count": len(rows), "rows": rows,
            "meaning": "Each manually authored terminating cost N is checked at N-1/N/N+1 and both sides of the cancellation/terminal boundary. Inputs overlap the other finite section and are not counted as unique global runs."}


def prefix_trace(prefix, period, length):
    pairs = list(prefix)
    while len(pairs) < length:
        pairs.extend(period)
    return full_trace(pairs[:length])


def divergent(fixtures):
    fixture = fixtures["divergence"]
    rows = []
    for budget in fixture["budgets"]:
        for cancellation in fixture["cancel_at"]:
            actual = model_run(fixture["program"], budget, cancellation, "divergent-cancel")
            independent = oracle.run(fixture["program"], budget, cancel_at=cancellation,
                                     cancel_request_id="divergent-cancel")
            steps = budget if cancellation is None else min(budget, cancellation)
            cancelled = cancellation is not None and cancellation <= budget
            expected = {"profile_revision": oracle.PROFILE_REVISION,
                        "content_digest": oracle.artifact_digest(fixture["program"]),
                        "termination": "SEMANTIC_STOP", "code": "CANCELLED" if cancelled else "BUDGET_EXCEEDED",
                        "value": None, "steps": steps, "remaining": budget - steps,
                        "trace": prefix_trace(fixture["prefix"], fixture["period"], steps),
                        "cancel_request_id": "divergent-cancel" if cancelled else None}
            equal(actual, independent, "divergent independent oracle")
            equal(actual, expected, "authored recursive periodic trace")
            rows.append({"budget": budget, "cancel_at": cancellation, "code": actual["code"],
                         "steps": steps, "actual_sha256": digest(actual),
                         "oracle_sha256": digest(independent), "authored_sha256": digest(expected)})
    return {"case_count": len(rows), "domain": {"budgets": fixture["budgets"], "cancel_at": fixture["cancel_at"]},
            "rows": rows, "host_recursion_used": False,
            "claim": "Only the declared finite prefixes are executed; divergence of arbitrary programs is not decided."}


def step_api(fixtures):
    row = next(r for r in fixtures["programs"] if r["id"] == "C06")
    program = model_program(row["program"])
    m = engine.launch(program, row["expected"]["steps"], cancel_at=row["expected"]["steps"])
    snapshots = []
    while m.termination is None:
        old = (m.steps, m.remaining, m.trace, m.control, m.environment, m.continuation, m.heap)
        nxt = engine.step(m)
        equal([m.steps, m.remaining, engine.canonical(m.trace)],
              [old[0], old[1], engine.canonical(old[2])], "step retains its immutable prior snapshot")
        require((m.control, m.environment, m.continuation, m.heap) == old[3:], "immutable internal state")
        require(nxt.steps == m.steps + 1, "one charge per actual semantic transition")
        require(nxt.remaining == m.remaining - 1, "one unit per charged transition")
        snapshots.append({"steps": nxt.steps, "remaining": nxt.remaining,
                          "last_rule": engine.canonical(nxt.trace[-1]), "termination": nxt.termination})
        m = nxt
    actual = engine.execution_json(engine.execution(m))
    equal(actual, authored_cut(row, row["expected"]["steps"], row["expected"]["steps"]), "terminal is free")
    require(engine.step(m) is m, "returned terminal step is identity")
    stopped = []
    for cancellation in (None, 0):
        initial = engine.launch(program, 0, cancel_at=cancellation)
        final = engine.step(initial)
        require(final.steps == 0 and not final.trace, "stopping observation adds no transition")
        require(engine.step(final) is final, "semantic stop step is identity")
        stopped.append(engine.execution_json(engine.execution(final)))
    return {"charged_steps": snapshots, "final": actual, "zero_budget_stops": stopped}


def input_integrity(fixtures):
    row = next(r for r in fixtures["programs"] if r["id"] == "C01")
    raw = deepcopy(row["program"])
    p = model_program(raw)
    prepared = engine.prepare(p)
    raw["entry"]["value"] = 99
    equal(engine.execution_json(engine.run(p, 1)), authored_cut(row, 1), "Program deep freeze")
    replacement = deepcopy(row["program"]["entry"])
    replacement["value"] = 99
    forged = replace(prepared, nodes={"n": replacement}, content_digest="0" * 64,
                     node_types={"n": engine.BOOL})
    actual = engine.execution_json(engine.run(forged, 1))
    equal(actual, authored_cut(row, 1), "Prepared indexes are rebuilt from exact immutable Program")
    changed = deepcopy(row["program"])
    changed["entry"]["value"] = 8
    changed_prepared = engine.prepare(model_program(changed))
    require(changed_prepared.content_digest != prepared.content_digest,
            "same source labels cannot substitute content identity")
    equal(changed_prepared.content_digest, oracle.artifact_digest(changed), "independent artifact preimage")
    return {"immutable_program_digest": prepared.content_digest,
            "changed_program_digest": changed_prepared.content_digest,
            "forged_prepared_ignored": True, "actual": actual}


def api_diagnostics(fixtures):
    raw = deepcopy(fixtures["programs"][0]["program"])
    p = model_program(raw)
    outcomes = []
    for budget, code in ((True, "INVALID_BUDGET"), (-1, "INVALID_BUDGET"), (65537, "PROFILE_LIMIT")):
        outcomes.append({"input": {"budget": budget}, "actual": diagnostic(lambda budget=budget: engine.run(p, budget), code)})
    for cancel, code in ((True, "INVALID_CANCELLATION"), (-1, "INVALID_CANCELLATION"), (65537, "PROFILE_LIMIT")):
        outcomes.append({"input": {"cancel_at": cancel}, "actual": diagnostic(lambda cancel=cancel: engine.run(p, 1, cancel_at=cancel), code)})
    extra = deepcopy(raw); extra["trusted"] = True
    missing = deepcopy(raw); del missing["result_type"]
    outcomes.append({"input": "unknown top-level field", "actual": diagnostic(lambda: engine.decode_program(extra), "UNKNOWN_FIELD")})
    outcomes.append({"input": "missing top-level field", "actual": diagnostic(lambda: engine.decode_program(missing), "MISSING_FIELD")})
    outcomes.append({"input": "observe nonterminal machine", "actual": diagnostic(lambda: engine.execution(engine.launch(p, 1)), "MACHINE_NOT_TERMINAL", "HostAPIDiagnostic")})
    return {"cases": outcomes, "runtime_trace_not_started_for_prelaunch_failures": True}


def codec_boundary(fixtures):
    rows = []
    function_row = next(r for r in fixtures["programs"] if r["id"] == "C17")
    for row in [function_row] + fixtures["codec_cases"]:
        actual, independent, expected = compare_three(row, row["expected"]["steps"])
        execution = engine.run(model_program(row["program"]), row["expected"]["steps"])
        rejection = diagnostic(lambda: engine.encode_data(execution.value),
                               "NON_PERSISTABLE_VALUE", "CodecDiagnostic")
        rows.append({"id": row["id"], "program": row["program"], "actual": actual,
                     "independent_oracle": independent, "authored": expected,
                     "codec_rejection": rejection})
    ordinary = next(r for r in fixtures["programs"] if r["id"] == "C16")
    execution = engine.run(model_program(ordinary["program"]), ordinary["expected"]["steps"])
    equal(engine.encode_data(execution.value), authored_value(ordinary), "nested ordinary Result persists structurally")
    return {"cases": rows, "ordinary_data_codec": engine.encode_data(execution.value),
            "function_code_view_is_capture_equality": False,
            "err_result_with_function_ok_type_rejected": True}


def physical_boundary(fixtures):
    fixture = fixtures["physical_boundary"]
    actual = model_run(fixture["program"], fixture["budget"])
    expected_steps = fixture["expected_steps"]
    equal(actual["termination"], fixture["expected_termination"], "physical guard category")
    equal(actual["code"], fixture["expected_code"], "physical guard code")
    equal(actual["steps"], expected_steps, "published continuation guard boundary")
    equal(actual["remaining"], fixture["budget"] - expected_steps, "guard not a semantic charge")
    equal(actual["value"], None, "physical refusal is not a returned value")
    equal(actual["cancel_request_id"], None, "physical refusal is not cancellation")
    expected_trace = prefix_trace(fixture["prefix"], fixture["period"], expected_steps)
    equal(actual["trace"], expected_trace, "authored trace prefix before allocation refusal")
    independent = oracle.run(fixture["program"], expected_steps)
    equal(actual["trace"], independent["trace"], "independent semantic prefix through physical boundary")
    equal(independent["code"], "BUDGET_EXCEEDED", "oracle has no implementation allocation policy")
    return {"input": {"program_id": fixture["id"], "budget": fixture["budget"]},
            "expected_steps": expected_steps, "expected_code": fixture["expected_code"],
            "actual": {k: v for k, v in actual.items() if k != "trace"},
            "charged_trace_sha256": digest(actual["trace"]),
            "independent_prefix_sha256": digest(independent["trace"]),
            "authored_prefix_sha256": digest(expected_trace),
            "whole_oracle_outcome_equality_claimed": False,
            "reason": "Physical continuation refusal differs intentionally from the semantic-only oracle; only the full preceding trace is compared."}


def boundary_checks(fixtures):
    actions = [
        ("B01", lambda: boundary_cuts(fixtures)),
        ("B02", lambda: step_api(fixtures)),
        ("B03", lambda: input_integrity(fixtures)),
        ("B04", lambda: api_diagnostics(fixtures)),
        ("B05", lambda: codec_boundary(fixtures)),
        ("B06", lambda: divergent(fixtures)),
        ("B07", lambda: physical_boundary(fixtures)),
    ]
    return section([checked(identifier, action) for identifier, action in actions])


def mutated_module(identifier, patches):
    """Execute an exact isolated source mutation; never edit the frozen engine."""
    path = ROOT / "experiments/core-machine/engine.py"
    original = path.read_text(encoding="utf-8")
    source = original
    applied = []
    for before, after in patches:
        require(source.count(before) == 1, "mutation preimage must occur exactly once: " + identifier)
        source = source.replace(before, after)
        applied.append({"before": before, "after": after, "matched_occurrences": 1})
    name = "_core_mutant_" + identifier
    module = types.ModuleType(name)
    module.__file__ = str(path) + ":" + identifier
    sys.modules[name] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module, {"original_source_sha256": sha256(original.encode()).hexdigest(),
                    "mutated_source_sha256": sha256(source.encode()).hexdigest(), "patches": applied}


def mutations(fixtures):
    rows = {r["id"]: r for r in fixtures["programs"]}
    cancellation = ('    if machine.cancel_at is not None and machine.steps >= machine.cancel_at:\n'
                    '        return replace(machine, termination="SEMANTIC_STOP", code="CANCELLED")\n'
                    '    if machine.remaining == 0:\n'
                    '        return replace(machine, termination="SEMANTIC_STOP", code="BUDGET_EXCEEDED")')
    budget_first = ('    if machine.remaining == 0:\n'
                    '        return replace(machine, termination="SEMANTIC_STOP", code="BUDGET_EXCEEDED")\n'
                    '    if machine.cancel_at is not None and machine.steps >= machine.cancel_at:\n'
                    '        return replace(machine, termination="SEMANTIC_STOP", code="CANCELLED")')
    patches = {
        "M01": [('        env, tenv = capture.environment, capture.type_environment',
                 '        env, tenv = machine.environment, capture.type_environment')],
        "M02": [(cancellation, budget_first)],
        "M03": [
            ('control=node["args"][0]["nid"], continuation=rest + (new_frame,),',
             'control=node["args"][-1]["nid"], continuation=rest + (new_frame,),'),
            ('control=node["args"][index]["nid"], continuation=rest + (new_frame,),',
             'control=node["args"][len(node["args"])-1-index if frame.kind == "CALL_ARGS" else index]["nid"], continuation=rest + (new_frame,),'),
            ('return _enter_body(machine, frame.function, values, rest), "CALL_BODY", nid',
             'return _enter_body(machine, frame.function, tuple(reversed(values)), rest), "CALL_BODY", nid'),
        ],
    }
    def one(fixture):
        row = rows[fixture["program_id"]]
        budget = fixture.get("budget", row["expected"]["steps"])
        cancellation = fixture.get("cancel_at")
        baseline, independent, expected = compare_three(row, budget, cancellation, "mutant-cancel")
        module, source = mutated_module(fixture["id"], patches[fixture["id"]])
        try:
            actual = model_run(row["program"], budget, cancellation, "mutant-cancel", module)
        finally:
            sys.modules.pop(module.__name__, None)
        differences = [key for key in sorted(OBSERVATION_FIELDS)
                       if encoded(actual[key]) != encoded(expected[key])]
        require(differences, "mutation was not distinguished by a real execution")
        if fixture["id"] == "M03":
            equal(actual["value"], baseline["value"], "order mutant preserves argument positions and value")
            equal(actual["steps"], baseline["steps"], "order mutant preserves count")
            require("trace" in differences, "only outcome/count comparison would miss argument reordering")
        return {"defect": fixture["defect"], "source": source,
                "program_id": row["id"], "budget": budget, "cancel_at": cancellation,
                "baseline": baseline, "independent_oracle": independent,
                "authored": expected, "mutant": actual, "different_fields": differences,
                "actual_execution": True, "distinguished": True,
                "frozen_source_edited": False}
    result = section([checked(f["id"], lambda f=f: one(f)) for f in fixtures["mutants"]])
    result["distinguished"] = sum(r.get("details", {}).get("distinguished", False) for r in result["rows"])
    result["method"] = "Exact isolated in-memory mutations of the frozen engine; not declared or simulated failures."
    return result


def coverage(fixtures, authored, negatives):
    forms, primitives, types_seen = set(), set(), set()
    pending = [r["program"] for r in fixtures["programs"]]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            if "op" in value:
                forms.add(value["op"])
                if value["op"] == "prim":
                    primitives.add(value["name"])
            if value.get("tag") in {"var", "fn", "result"}:
                types_seen.add(value["tag"])
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    executed_rules = {entry["rule"] for row in authored["rows"] if row["status"] == "PASS"
                      for entry in row["details"]["actual"]["trace"]}
    equal(sorted(forms), sorted(FORMS), "all ten forms in authored positive programs")
    equal(sorted(primitives), sorted(PRIMITIVES), "all six primitives in authored positive programs")
    equal(sorted(executed_rules), sorted(RULES), "all published charged rule labels actually executed")
    equal(sorted(types_seen), ["fn", "result", "var"], "three declared type constructors")
    return {"positive_ast_forms": sorted(forms), "executed_rule_ids": sorted(executed_rules),
            "executed_primitives": sorted(primitives), "annotation_type_constructors": sorted(types_seen),
            "negative_diagnostic_codes": sorted({r["details"]["actual"]["code"] for r in negatives["rows"] if r["status"] == "PASS"}),
            "coverage_of_all_programs_or_contexts_claimed": False}


def source_hashes():
    return {ref: sha256((ROOT / ref).read_bytes()).hexdigest() for ref in SOURCE_REFS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="results/core-machine/report.json")
    args = parser.parse_args()
    before = source_hashes()
    started = time.perf_counter()
    fixtures = json.loads((ROOT / FIXTURE_REF).read_text(encoding="utf-8"))
    authored = authored_programs(fixtures)
    negatives = negative_programs(fixtures)
    boundaries = boundary_checks(fixtures)
    matrix = bounded_matrix(fixtures)
    mutants = mutations(fixtures)
    coverage_result = checked("COVERAGE", lambda: coverage(fixtures, authored, negatives))
    after = source_hashes()
    stable = before == after
    sections = (authored, negatives, boundaries, mutants)
    named_total = sum(s["checks"] for s in sections) + 1
    named_passed = sum(s["passed"] for s in sections) + (coverage_result["status"] == "PASS")
    passed = named_total == named_passed and matrix["status"] == "PASS" and stable
    boundary_lookup = {r["id"]: r for r in boundaries["rows"]}
    report = {
        "schema": "bagaev-core-report/0.1", "iteration": "R06",
        "status": "PASS" if passed else "FAIL", "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime": {"implementation": platform.python_implementation(), "python": platform.python_version()},
        "source_sha256": before, "sources_unchanged_during_run": stable,
        "scope": {
            "bagaev_execution": False, "research_core_execution": True,
            "annotated_ir_only": True, "independent_oracle_imports_engine": False,
            "semantic_execution_uses_host_recursion": False,
            "hypothesis_tested": False, "universal_proof": False,
            "machine_checked_universal_proof": False, "full_v1_conformance": False,
            "source_type_elaboration_implemented": False, "host_effects_executed": False,
            "physical_db_or_concurrency_tested": False, "performance_speedup_claimed": False,
            "function_code_descriptor_is_closure_equality": False,
            "historical_profiles_reinterpreted": False,
        },
        "observation_contract": {
            "compared_fields": sorted(OBSERVATION_FIELDS),
            "trace_fields": ["step_index", "rule", "node_id"],
            "comparison_scope": "Equality of the declared diagnostic observation. A returned Function view hides captures and is not extensional closure equality; C09/C10 exercise captures by calling functions to ground data results.",
            "oracle": "Independent pending derivation goals with value slots and immutable lexical mappings; no engine/OBS/CALL import or lowering.",
            "manual_grounding": "Every finite matrix execution is additionally compared to an authored full trace/outcome cut at the declared budget and cancellation boundary.",
            "physical_guard_exception": "The semantic oracle has no implementation allocation limits. B07 compares the whole pre-refusal trace; it explicitly does not claim equality of terminal categories.",
        },
        "summary": {
            "named_checks": named_total, "named_passed": named_passed,
            "authored_programs": authored["checks"], "negative_programs": negatives["checks"],
            "boundary_groups": boundaries["checks"], "bounded_matrix_cases": matrix["case_count"],
            "whole_field_matrix_matches": matrix["whole_field_matches"], "matrix_mismatches": matrix["mismatches"],
            "terminal_boundary_cases": boundary_lookup["B01"].get("details", {}).get("case_count", 0),
            "divergent_prefix_cases": boundary_lookup["B06"].get("details", {}).get("case_count", 0),
            "mutants_executed": mutants["checks"], "mutants_distinguished": mutants["distinguished"],
            "counts_are_not_disjoint_global_execution_totals": True,
        },
        "authored_programs": authored, "negative_programs": negatives,
        "boundary_checks": boundaries, "bounded_matrix": matrix, "mutations": mutants,
        "coverage": coverage_result, "elapsed_seconds": round(time.perf_counter() - started, 6),
        "elapsed_time_is_benchmark": False,
        "reproduce": "python -B experiments/core-machine/verify.py --output results/core-machine/report.json",
    }
    target = Path(args.output)
    if not target.is_absolute():
        target = ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "summary": report["summary"],
                      "source_stable": stable, "report": str(target),
                      "report_sha256": sha256(target.read_bytes()).hexdigest()}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
