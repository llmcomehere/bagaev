#!/usr/bin/env python3
"""Execute a finite R02 corpus against an independent interpreter.

No bagaev source is imported or executed. EXCLUDED decisions are checked
against concrete value/error/effect observations produced by oracle.py.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from itertools import permutations, product
import json
from pathlib import Path
import platform
import sys
import time

import engine
import oracle


PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def encoded(value):
    return json.dumps(oracle.json_value(value), ensure_ascii=False,
                      sort_keys=True, separators=(",", ":"), allow_nan=False)


def equal(actual, expected, label=""):
    if encoded(actual) != encoded(expected):
        raise AssertionError(f"{label}: actual={actual!r}; expected={expected!r}")


def require(value, detail):
    if not value:
        raise AssertionError(detail)


def rejects(code, action):
    try:
        action()
    except engine.ProfileError as error:
        equal(error.code, code)
        return {"diagnostic": error.code}
    raise AssertionError("Expected profile rejection: " + code)


def resource(spec):
    return None if spec is None else engine.ResourceState(tuple(spec["members"]), spec.get("read_error"))


def engine_observations(result):
    return {"status": result.status, "value": oracle.json_value(result.value),
            "error": result.error,
            "trace": [{"label": event.label, "value": oracle.json_value(event.value)}
                      for event in result.trace], "complete": result.complete}


def changed_execution_observations(before, after):
    return [name for name in ("status", "value", "error", "trace", "complete")
            if encoded(before[name]) != encoded(after[name])]


def type_data(typ):
    return {"tuple": [type_data(x) for x in typ.args]} if typ.name == "tuple" else typ.name


def consumer(program, identifier="worker", **overrides):
    values = {"stable_id": identifier, "program": program["ast"],
              "compile_config": program["compile_config"]}
    values.update(overrides)
    return engine.Consumer(**values)


def run_cases(actions):
    records = []
    for identifier, action in actions:
        try:
            details = action()
            records.append({"id": identifier, "status": "PASS", "details": details})
        except Exception as error:
            records.append({"id": identifier, "status": "FAIL", "error": repr(error)})
    return records


def program_checks(programs):
    actions = []
    for row in programs.values():
        def check(row=row):
            actual_type = engine.validate_program(row["ast"], row["compile_config"])
            equal(type_data(actual_type), row["expected_type"], "type")
            use = engine.infer_use(row["ast"], row["compile_config"])
            equal(sorted(use.required_observations), row["expected_required_observations"], "inferred use")
            equal(use.complete, row["expected_complete"], "use completeness")
            return {"type": type_data(actual_type), "automatically_inferred_use": engine.to_data(use)}
        actions.append((row["id"], check))
    return run_cases(actions)


def manual_checks(fixtures, programs):
    actions = []
    for case in fixtures["manual_cases"]:
        def check(case=case):
            row = programs[case["program"]]
            observations = []
            for side in ("before", "after"):
                independent = oracle.observations(oracle.execute(row["ast"], case[side], row["compile_config"]))
                actual = engine_observations(engine.execute(row["ast"], resource(case[side]), row["compile_config"]))
                equal(independent, case["expected_" + side], "manual independent " + side)
                equal(actual, case["expected_" + side], "manual engine " + side)
                observations.append(independent)
            delta = engine.exact_delta(resource(case["before"]), resource(case["after"]))
            expected_delta = case["expected_resource_changed_observations"]
            equal(sorted(delta.changed), expected_delta, "manual resource delta")
            equal(sorted(oracle.changed_observations(case["before"], case["after"])), expected_delta,
                  "independent resource delta")
            item = consumer(row)
            assessment = engine.assess(item, item, resource(case["before"]), resource(case["after"]))
            equal(assessment.decision, case["expected_decision"], "manual decision")
            changed = changed_execution_observations(*observations)
            if assessment.decision == "EXCLUDED":
                require(observations[0]["complete"] and observations[1]["complete"],
                        "Unknown execution cannot justify exclusion")
                equal(changed, [], "excluded concrete observations")
            return {"program": case["program"], "assessment": engine.to_data(assessment),
                    "resource_changed_observations": sorted(delta.changed),
                    "executed_before": observations[0], "executed_after": observations[1],
                    "actual_changed_execution_observations": changed}
        actions.append((case["id"], check))
    return run_cases(actions)


def finite_resources(domain):
    rows = []
    for length in range(domain["maximum_length"] + 1):
        for members in permutations(domain["author_ids"], length):
            rows.append({"id": "members:" + (",".join(members) or "empty"),
                         "value": {"members": list(members)}})
    if domain["include_missing"]:
        rows.append({"id": "missing", "value": None})
    for error in domain["additional_read_errors"]:
        rows.append({"id": "read_error:" + error,
                     "value": {"members": [], "read_error": error}})
    return rows


def bounded_observation_checks(fixtures, programs):
    resources = finite_resources(fixtures["domain"])
    resource_pairs = []
    for before, after in product(resources, repeat=2):
        expected = oracle.changed_observations(before["value"], after["value"])
        actual = engine.exact_delta(resource(before["value"]), resource(after["value"]))
        equal(sorted(actual.changed), sorted(expected), "bounded exact observation delta")
        resource_pairs.append({"before": before["id"], "after": after["id"],
                               "changed_observations": sorted(expected)})
    summaries = []
    execution_cases = assessment_cases = excluded_count = conservative_count = unknown_count = 0
    for row in programs.values():
        executed = {}
        for state in resources:
            independent = oracle.observations(oracle.execute(row["ast"], state["value"], row["compile_config"]))
            actual = engine_observations(engine.execute(row["ast"], resource(state["value"]), row["compile_config"]))
            equal(actual, independent, "bounded execution " + row["id"] + "/" + state["id"])
            executed[state["id"]] = independent
            execution_cases += 1
        item = consumer(row)
        decisions, patterns, excluded = Counter(), Counter(), []
        for before, after in product(resources, repeat=2):
            assessment = engine.assess(item, item, resource(before["value"]), resource(after["value"]))
            old, new = executed[before["id"]], executed[after["id"]]
            changed = changed_execution_observations(old, new)
            decisions[assessment.decision] += 1
            patterns[(assessment.decision, tuple(changed))] += 1
            assessment_cases += 1
            if assessment.decision == "EXCLUDED":
                require(old["complete"] and new["complete"], "EXCLUDED on incomplete oracle execution")
                equal(old, new, f"False exclusion {row['id']} {before['id']} -> {after['id']}")
                excluded.append([before["id"], after["id"]])
                excluded_count += 1
            elif assessment.decision == "RECHECK" and not changed:
                conservative_count += 1
            elif assessment.decision == "UNKNOWN":
                unknown_count += 1
        summaries.append({"program": row["id"], "decisions": dict(sorted(decisions.items())),
                          "actual_change_patterns": [
                              {"decision": decision, "actual_changed_execution_observations": list(changed),
                               "case_count": count}
                              for (decision, changed), count in sorted(patterns.items())],
                          "excluded_resource_pairs": excluded,
                          "all_excluded_pairs_have_equal_complete_oracle_observations": True})
    return {"status": "PASS", "resource_states": resources,
            "program_count": len(programs), "resource_count": len(resources),
            "ordered_resource_pair_count": len(resources) ** 2,
            "exact_delta_cases": len(resource_pairs), "execution_cases_per_interpreter": execution_cases,
            "assessment_cases": assessment_cases, "excluded_cases_checked": excluded_count,
            "false_exclusions": 0, "conservative_rechecks_with_equal_observations": conservative_count,
            "unknown_cases": unknown_count,
            "resource_pair_deltas": resource_pairs, "program_results": summaries,
            "scope": "All ordered pairs of these resources for these fixed AST fixtures only; no universal proof."}


def revision_checks(programs):
    same_resource = engine.ResourceState(("a",))
    actions = []

    def changed(label, before, after, required_reason, requirement_status=None):
        assessment = engine.assess(before, after, same_resource, same_resource)
        require(assessment.decision != "EXCLUDED", label + " was falsely excluded")
        require(any(reason.startswith(required_reason) for reason in assessment.reasons), label + " reason lost")
        if requirement_status:
            equal([(r.requirement_id, r.status) for r in assessment.requirements],
                  [("nonempty", requirement_status)])
        return {"assessment": engine.to_data(assessment), "same_resource_pair": True,
                "resource_changed_observations": []}

    old = consumer(programs["constant"])
    new = consumer({**programs["constant"], "ast": {"op": "const", "value": "different"}})
    actions.append(("R01_code_revision_with_unchanged_data",
                    lambda: changed("code", old, new, "PROGRAM_REVISION_CHANGED")))
    actions.append(("R02_equivalent_current_value_is_not_code_equivalence",
                    lambda: changed("code rewrite", consumer(programs["size_ordered"]),
                                    consumer(programs["count"]), "PROGRAM_REVISION_CHANGED")))
    actions.append(("R03_compile_config_invalidation",
                    lambda: changed("config", consumer(programs["config_disabled"]),
                                    consumer(programs["config_enabled"]), "COMPILE_CONFIG_CHANGED")))
    actions.append(("R04_provider_invalidation",
                    lambda: changed("provider", consumer(programs["count"]),
                                    consumer(programs["count"], provider_revision="provider/v2"),
                                    "PROVIDER_REVISION_CHANGED")))
    actions.append(("R05_new_requirement_remains_open",
                    lambda: changed("new requirement", consumer(programs["constant"]),
                                    consumer(programs["constant"], requirements={"nonempty": "r1"}),
                                    "REQUIREMENTS_CHANGED", "OPEN")))
    actions.append(("R06_changed_requirement_remains_open",
                    lambda: changed("requirement revision", consumer(programs["constant"], requirements={"nonempty": "r1"}),
                                    consumer(programs["constant"], requirements={"nonempty": "r2"}),
                                    "REQUIREMENTS_CHANGED", "OPEN")))
    actions.append(("R07_removed_requirement_is_an_open_removal",
                    lambda: changed("requirement removal", consumer(programs["constant"], requirements={"nonempty": "r1"}),
                                    consumer(programs["constant"]), "REQUIREMENTS_CHANGED", "REMOVAL_OPEN")))

    def unchanged_requirement():
        item = consumer(programs["count"], requirements={"nonempty": "r1"})
        answer = engine.assess(item, item, engine.ResourceState(("a", "b")), engine.ResourceState(("b", "a")))
        equal(answer.decision, "EXCLUDED")
        equal([r.status for r in answer.requirements], ["UNCHANGED_UNASSESSED"])
        return {"assessment": engine.to_data(answer), "requirement_satisfaction_established": False}
    actions.append(("R08_no_new_impact_does_not_prove_requirement", unchanged_requirement))

    def removed_consumer_requirement():
        item = consumer(programs["count"], requirements={"nonempty": "r1"})
        answer = engine.assess(item, None, same_resource, same_resource)
        equal(answer.decision, "RECHECK")
        equal([r.status for r in answer.requirements], ["REMOVAL_OPEN"])
        return engine.to_data(answer)
    actions.append(("R09_removed_consumer_keeps_requirement_review", removed_consumer_requirement))

    def alias():
        answer = engine.assess(consumer(programs["count"], alias="old"),
                               consumer(programs["count"], alias="new"), same_resource, same_resource)
        equal(answer.decision, "EXCLUDED")
        return {"assessment": engine.to_data(answer), "assumption": "aliases are nonreflective in this profile"}
    actions.append(("R10_nonreflective_alias", alias))
    return run_cases(actions)


def invalid_input_checks(programs):
    invalid_programs = [
        ("T01_integer_condition", {"op": "if", "condition": {"op": "const", "value": 1},
                                   "then": {"op": "const", "value": 0}, "else": {"op": "const", "value": 0}}, "TYPE_MISMATCH"),
        ("T02_different_branch_types", {"op": "if", "condition": {"op": "const", "value": True},
                                        "then": {"op": "const", "value": 0}, "else": {"op": "const", "value": "zero"}}, "TYPE_MISMATCH"),
        ("T03_bool_is_not_int", {"op": "eq", "left": {"op": "const", "value": True},
                                "right": {"op": "const", "value": 1}}, "TYPE_MISMATCH"),
        ("T04_unbound_variable", {"op": "var", "name": "missing"}, "UNBOUND_VARIABLE"),
        ("T05_unsupported_op_is_not_silent", {"op": "eval_host_code", "value": "ignored"}, "UNSUPPORTED_AST_OPERATION"),
        ("T06_declared_deps_cannot_override_closed_AST", {"op": "read", "view": "count", "declared_observations": []}, "UNKNOWN_AST_FIELD"),
        ("T07_unknown_resource_view", {"op": "read", "view": "secret"}, "UNSUPPORTED_RESOURCE_VIEW"),
        ("T08_head_requires_sequence", {"op": "head", "value": {"op": "read", "view": "count"}}, "TYPE_MISMATCH"),
    ]
    actions = [(identifier, lambda ast=ast, code=code: rejects(code, lambda: engine.validate_program(ast)))
               for identifier, ast, code in invalid_programs]
    actions.extend([
        ("T09_config_requires_bool", lambda: rejects("INVALID_COMPILE_CONFIG", lambda: engine.infer_use(programs["config_enabled"]["ast"], {"enabled": "false"}))),
        ("T10_missing_config_is_explicit", lambda: rejects("MISSING_COMPILE_CONFIG", lambda: engine.validate_program(programs["config_enabled"]["ast"]))),
        ("T11_unique_author_domain", lambda: rejects("DUPLICATE_AUTHOR_ID", lambda: engine.ResourceState(("a", "a")))),
    ])
    def invalid_unicode():
        ast = {"op": "const", "value": "\ud800"}
        rejects("INVALID_UNICODE_SCALAR", lambda: engine.validate_program(ast))
        rejects("INVALID_UNICODE_SCALAR", lambda: engine.Consumer("invalid", ast))
        return {"diagnostic": "INVALID_UNICODE_SCALAR", "invalid_consumer_blocked_before_assessment": True}
    def invalid_integer():
        for number in (2**63, -(2**63)-1, 10**5000):
            ast = {"op": "const", "value": number}
            rejects("INTEGER_OUT_OF_RANGE", lambda: engine.validate_program(ast))
            rejects("INTEGER_OUT_OF_RANGE", lambda: engine.Consumer("invalid", ast))
        return {"diagnostic": "INTEGER_OUT_OF_RANGE", "invalid_consumer_blocked_before_assessment": True,
                "cases": ["above_signed64", "below_signed64", "5001_digit_integer"]}
    actions.extend([("T12_unicode_scalar_boundary", invalid_unicode),
                    ("T13_signed64_and_large_integer_boundary", invalid_integer)])
    return run_cases(actions)


def project_checks(programs):
    c = consumer(programs["constant"], "C")
    n = consumer(programs["count"], "N")
    empty = engine.extract_project({"C": c})
    added = engine.incremental_extract(empty, {"C": c, "N": n})
    changed = engine.incremental_extract(empty, {"C": consumer(programs["ordered"], "C")})
    actions = []

    def empty_reuse():
        query = engine.reverse_query(empty)
        equal(query.consumers, ())
        equal(query.complete, True)
        again = engine.incremental_extract(empty, {"C": c})
        equal(again.reused, ("C",))
        equal(engine.graph_content(again), engine.graph_content(engine.extract_project({"C": c})))
        return {"negative_query": engine.to_data(query), "reused": list(again.reused)}
    actions.append(("G01_empty_query_with_unchanged_AST_reuse", empty_reuse))

    def new_consumer():
        query = engine.reverse_query(added)
        equal(query.consumers, ("N",))
        equal(query.complete, True)
        require(query.manifest_stamp != engine.reverse_query(empty).manifest_stamp, "new root kept stale stamp")
        equal(added.reused, ("C",))
        equal(added.reextracted, ("N",))
        return {"before": engine.to_data(engine.reverse_query(empty)), "after": engine.to_data(query)}
    actions.append(("G02_new_consumer_after_empty_query", new_consumer))

    def nonconsumer():
        equal(engine.reverse_query(changed).consumers, ("C",))
        equal(changed.reextracted, ("C",))
        return {"query": engine.to_data(engine.reverse_query(changed)), "changed_ast": True}
    actions.append(("G03_existing_nonconsumer_becomes_reader", nonconsumer))

    def removed():
        new = engine.incremental_extract(added, {"C": c})
        equal(engine.reverse_query(new).consumers, ())
        delta = engine.graph_delta(added, new)
        require(any(edge.source == "N" for edge in delta.removed), "removed edges lost")
        require(any(edge.source == "N" for edge in delta.union), "old/new union lost old reader")
        assessments = {a.consumer_id: a for a in engine.assess_project(added, new, engine.ResourceState(("a",)), engine.ResourceState(("a",)))}
        equal(assessments["N"].decision, "RECHECK")
        return {"delta": engine.to_data(delta), "removed_consumer_assessment": engine.to_data(assessments["N"])}
    actions.append(("G04_removed_reader_retained_in_old_new_union", removed))

    def unknown():
        item = consumer(programs["opaque_external"], "X")
        result = engine.reverse_query(engine.incremental_extract(empty, {"C": c, "X": item}))
        equal(result.consumers, ("X",))
        equal(result.complete, False)
        return engine.to_data(result)
    actions.append(("G05_opaque_consumer_is_possible_and_incomplete", unknown))

    def cache_change(kind):
        row = programs["config_disabled"] if kind == "config" else programs["count"]
        before = consumer(row)
        overrides = {"compile_config": {"enabled": True}} if kind == "config" else (
            {"provider_revision": "provider/v2"} if kind == "provider" else {"requirements": {"nonempty": "r1"}})
        after = consumer(row, **overrides)
        old_graph = engine.extract_project({before.stable_id: before})
        new_graph = engine.incremental_extract(old_graph, {after.stable_id: after})
        equal(new_graph.reextracted, ("worker",))
        equal(new_graph.reused, ())
        require(new_graph.manifest_stamp != old_graph.manifest_stamp, "changed conditions kept manifest")
        equal(engine.graph_content(new_graph), engine.graph_content(engine.extract_project({after.stable_id: after})))
        return {"condition": kind, "reextracted": list(new_graph.reextracted)}
    for identifier, kind in (("G06_config_cache_invalidation", "config"),
                             ("G07_provider_cache_invalidation", "provider"),
                             ("G08_requirement_cache_invalidation", "requirements")):
        actions.append((identifier, lambda kind=kind: cache_change(kind)))
    actions.append(("G09_corrupted_edges_rejected", lambda: rejects("GRAPH_CONTENT_MISMATCH", lambda: engine.reverse_query(replace(added, edges=())))))
    actions.append(("G10_foreign_extractor_rejected", lambda: rejects("EXTRACTOR_REVISION_MISMATCH", lambda: engine.reverse_query(replace(added, extractor_revision="foreign")))))

    def order():
        equal(engine.graph_content(engine.extract_project({"C": c, "N": n})),
              engine.graph_content(engine.extract_project({"N": n, "C": c})))
        return {"canonical_project_order": True}
    actions.append(("G11_registry_order_does_not_change_graph", order))
    return run_cases(actions)


def bounded_project_checks(programs):
    modes = ("absent", "constant", "count", "ordered", "opaque_external")
    states = []
    for combination in product(modes, repeat=2):
        description = dict(zip(("P", "Q"), combination))
        project = {identifier: consumer(programs[mode], identifier)
                   for identifier, mode in description.items() if mode != "absent"}
        expected_consumers = tuple(sorted(identifier for identifier, mode in description.items()
                                          if mode not in {"absent", "constant"}))
        expected_complete = "opaque_external" not in combination
        graph = engine.extract_project(project)
        query = engine.reverse_query(graph)
        equal(query.consumers, expected_consumers, "manual project query meaning")
        equal(query.complete, expected_complete)
        states.append((description, project, graph, expected_consumers, expected_complete))
    transitions = 0
    for old, new in product(states, repeat=2):
        result = engine.incremental_extract(old[2], new[1])
        equal(engine.graph_content(result), engine.graph_content(new[2]), "incremental versus full graph")
        query = engine.reverse_query(result)
        equal(query.consumers, new[3], "independent mode table query")
        equal(query.complete, new[4])
        expected_reused = tuple(sorted(identifier for identifier in new[1]
                                       if identifier in old[1] and old[0][identifier] == new[0][identifier]))
        equal(result.reused, expected_reused, "exact stable consumer inputs")
        delta = engine.graph_delta(old[2], result)
        equal(engine.to_data(delta.union), engine.to_data(tuple(sorted(set(old[2].edges) | set(result.edges),
                   key=lambda e: (e.source, e.target or "", e.observation)))))
        transitions += 1
    return {"status": "PASS", "project_states": len(states), "ordered_transition_cases": transitions,
            "domain": {"consumer_ids": ["P", "Q"], "modes": list(modes)},
            "meaning": "Full/incremental graph and reverse-query consistency in this fixed finite registry domain; no speed claim."}


def mutation_checks(programs):
    def merge_bad(*uses):
        return engine.UseSummary(
            required_observations=frozenset().union(*(u.required_observations for u in uses)),
            complete=all(u.complete for u in uses),
            may_errors=frozenset().union(*(u.may_errors for u in uses)),
            effects=frozenset().union(*(u.effects for u in uses)),
            config_keys=frozenset().union(*(u.config_keys for u in uses)))

    def ignore_condition(ast, config):
        if ast["op"] == "if":
            return merge_bad(engine.infer_use(ast["then"], config), engine.infer_use(ast["else"], config))
        return engine.infer_use(ast, config)

    def drop_strict_initializer(ast, config):
        if ast["op"] == "let" and ast["body"]["op"] == "const":
            return engine.infer_use(ast["body"], config)
        return engine.infer_use(ast, config)

    def declared_override(ast, config):
        original = engine.infer_use(ast, config)
        return replace(original, required_observations=frozenset())

    definitions = [
        ("M1_IGNORE_IF_CONDITION", "conditional_count", {"members": ["a"]}, {"members": ["a", "b"]}, ignore_condition,
         "Incorrect analysis uses only the two constant branches and drops the count-dependent condition."),
        ("M2_DROP_STRICT_UNUSED_INITIALIZER", "unused_let_head", {"members": []}, {"members": ["a"]}, drop_strict_initializer,
         "Incorrect analysis drops an unused strict initializer; EMPTY_HEAD is observable despite an unused bound value."),
        ("M3_DECLARED_USE_OVERRIDES_INFERRED", "ordered", {"members": ["a"]}, {"members": ["b"]}, declared_override,
         "Incorrect analysis treats an empty declaration as authority to erase automatically inferred reads."),
    ]
    results = []
    for identifier, name, before, after, infer_bad, explanation in definitions:
        row = programs[name]
        item = consumer(row)
        correct = engine.assess(item, item, resource(before), resource(after))
        bad = engine.assess_with_test_analyzer(item, item, resource(before), resource(after), infer_fn=infer_bad)
        old_obs = oracle.observations(oracle.execute(row["ast"], before, row["compile_config"]))
        new_obs = oracle.observations(oracle.execute(row["ast"], after, row["compile_config"]))
        actual_changed = changed_execution_observations(old_obs, new_obs)
        killed = (correct.decision != "EXCLUDED" and bad.decision == "EXCLUDED"
                  and old_obs["complete"] and new_obs["complete"] and bool(actual_changed)
                  and bad.basis == "TEST_ONLY_UNTRUSTED")
        results.append({"id": identifier, "program": name, "fault": explanation,
                        "before_resource": before, "after_resource": after,
                        "normal_assessment": engine.to_data(correct), "mutant_assessment": engine.to_data(bad),
                        "independent_before": old_obs, "independent_after": new_obs,
                        "actual_changed_execution_observations": actual_changed, "killed": killed})
    return results


def source_hashes(fixture_path):
    files = [Path(__file__).with_name(name) for name in ("engine.py", "oracle.py", "verify.py", "README.md", "API.md")]
    files.append(fixture_path)
    return {str(path.relative_to(PACKAGE_ROOT)): sha256(path.read_bytes()).hexdigest() for path in files}


def guarded_section(action):
    try:
        return action()
    except Exception as error:
        return {"status": "FAIL", "error": repr(error)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(PACKAGE_ROOT / "results/observation-profile/report.json"))
    parser.add_argument("--fixtures", default=str(PACKAGE_ROOT / "fixtures/programs.json"))
    arguments = parser.parse_args()
    fixture_path = Path(arguments.fixtures).resolve()
    started = time.monotonic()
    initial_hashes = source_hashes(fixture_path)
    fixtures = json.loads(fixture_path.read_text())
    programs = {row["id"]: row for row in fixtures["programs"]}
    require(len(programs) == len(fixtures["programs"]), "Duplicate fixture program ID")
    sections = {
        "program_contracts": program_checks(programs),
        "manual_execution_cases": manual_checks(fixtures, programs),
        "revision_and_requirement_cases": revision_checks(programs),
        "invalid_input_cases": invalid_input_checks(programs),
        "project_cases": project_checks(programs),
    }
    bounded = guarded_section(lambda: bounded_observation_checks(fixtures, programs))
    project_bounded = guarded_section(lambda: bounded_project_checks(programs))
    mutants = guarded_section(lambda: mutation_checks(programs))
    final_hashes = source_hashes(fixture_path)
    case_rows = [row for section in sections.values() for row in section]
    mutant_success = isinstance(mutants, list) and all(row["killed"] for row in mutants)
    success = (all(row["status"] == "PASS" for row in case_rows) and bounded["status"] == "PASS"
               and project_bounded["status"] == "PASS" and mutant_success and initial_hashes == final_hashes)
    report = {
        "report_format": "bagaev-r02-finite-observation-profile/1", "status": "PASS" if success else "FAIL",
        "generated_utc": datetime.now(timezone.utc).isoformat(), "python_version": platform.python_version(),
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "bagaev_execution": False, "research_ast_execution": True, "hypothesis_tested": False,
        "requirement_predicate_satisfaction_tested": False, "tasks_closed": [],
        "T08_status": "NOT_CLOSED", "T09_status": "NOT_CLOSED",
        "source_sha256": final_hashes, "sources_unchanged_during_run": initial_hashes == final_hashes,
        "reproducible_command": "python -B experiments/observation-profile/verify.py --output results/observation-profile/report.json",
        "command_working_directory": "package root", "profile_revision": engine.PROFILE_REVISION,
        "extractor_revision": engine.EXTRACTOR_REVISION,
        "ordinary_use_source": "automatic conservative analysis of the closed research AST; no supplied use certificate",
        "oracle_independence": "oracle.py does not import engine.py; authored manual expectations are checked against each interpreter",
        "case_counts": {name: {"passed": sum(row["status"] == "PASS" for row in rows),
                                "failed": sum(row["status"] != "PASS" for row in rows)} for name, rows in sections.items()},
        **sections, "bounded_observation_checks": bounded, "bounded_project_checks": project_bounded,
        "mutants": mutants,
        "scope_limits": [
            "Only the declared fixed AST fixtures and all pairs of the finite resource domain are exhaustively checked.",
            "The research AST is not parsed from, compiled from, or executed by existing bagaev.",
            "Resource observations are correlated functions; equality is computed on exact concrete resource pairs.",
            "UNKNOWN executions never justify EXCLUDED; RECHECK can be conservative when actual observations are equal.",
            "Use summarizes all syntactic children, including both branches and strict unused initializers; no size/to_set narrowing.",
            "Requirements are revision metadata in this engine, not executable requirement predicates; unchanged requirements remain unassessed.",
            "No arbitrary provider/code equivalence, general extraction completeness, durable protocol, or real external effects are established.",
            "Graph refresh validates with full extraction and makes no incremental speed claim.",
            "The product hypothesis and A/B/C cost comparison have not been tested; no universal soundness proof is claimed.",
        ],
    }
    output = Path(arguments.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "case_counts": report["case_counts"],
                      "resource_count": bounded.get("resource_count"),
                      "assessment_cases": bounded.get("assessment_cases"),
                      "excluded_cases_checked": bounded.get("excluded_cases_checked"),
                      "false_exclusions": bounded.get("false_exclusions"),
                      "project_transitions": project_bounded.get("ordered_transition_cases"),
                      "mutants_killed": sum(row["killed"] for row in mutants) if isinstance(mutants, list) else 0,
                      "sources_unchanged_during_run": report["sources_unchanged_during_run"], "report": str(output)}, ensure_ascii=False))
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
