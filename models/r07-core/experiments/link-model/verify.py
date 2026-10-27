#!/usr/bin/env python3
"""Run finite fixtures; never imports or executes the bagaev implementation."""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from itertools import combinations, product
import json
from pathlib import Path
import platform
import sys
import time

from model import (Certificate, FacetClaim, Fact, Graph, Guard, HeadStore, IndexPair,
                   ModelError, Node, REGISTRY, ReturnedItemsOnlyCache, ReverseCache,
                   build_indexes, canonical, certified, digest, full_query,
                   guard_state, impact, indexed_query, membership_key)


def graph(facts=(), *, generation="g0", config=(), pinned=True, complete=True,
          extractor="synthetic-extractor-v1", extra_nodes=()):
    facts = tuple(facts)
    operations = ("A", "B", "C") + tuple(extra_nodes)
    nodes = [Node("R", kind="resource"), Node("Other", kind="resource")]
    for entity in operations:
        revision = digest(sorted((f for f in facts if f.source == entity),
                                 key=lambda f: f.fact_id))[:16]
        nodes.append(Node(entity, revision, alias=entity.lower()))
    return Graph(generation, tuple(nodes), facts, tuple(config), pinned, extractor, complete)


def fact(source="A", target="R", *, facets=("values",), guard=Guard(),
         footprint=None, kind="reads", fact_id=None):
    return Fact(fact_id or f"{source}_{kind}_{target}", source, target, kind, guard,
                footprint if footprint is not None else certified(*facets))


def equal(actual, expected):
    if actual != expected:
        raise AssertionError(f"actual={actual!r}; expected={expected!r}")


def rejects(code, callback):
    try:
        callback()
    except ModelError as error:
        equal(str(error), code)
        return
    raise AssertionError("expected rejection: " + code)


def decisions(base, candidate=None, delta=None, **kwargs):
    result = impact(base, candidate or base, "R", delta or certified("values"), **kwargs)
    return dict(result.decisions), result


def manual_cases():
    cases = []
    def run(name, fn):
        try:
            note = fn()
            cases.append({"id": name, "status": "PASS", "observation": note})
        except Exception as error:
            cases.append({"id": name, "status": "FAIL", "error": repr(error)})

    def new_after_empty():
        cache = ReverseCache()
        equal(cache.query(graph(), "R")[0].items, ())
        result, hit = cache.query(graph([fact("N")], generation="g1", extra_nodes=("N",)), "R")
        equal((result.items, hit), (("N",), False))
    run("H01_new_consumer_after_empty_result", new_after_empty)

    def nonconsumer_changes():
        cache = ReverseCache()
        base = graph([fact("A"), fact("B", "Other")])
        new = graph([fact("A"), fact("B")], generation="g1")
        equal(cache.query(base, "R")[0].items, ("A",))
        result, hit = cache.query(new, "R")
        equal((result.items, hit), (("A", "B"), False))
    run("H02_existing_nonconsumer_becomes_consumer", nonconsumer_changes)

    def removed_reader():
        base, new = graph([fact()]), graph(generation="g1")
        ds, report = decisions(base, new)
        equal(ds["A"], "IN_SCOPE")
        assert ("base", "A_reads_R", "R") in report.inspected_edges
        equal(full_query(new, "R").items, ())
    run("H03_removed_reader_seen_in_old_graph", removed_reader)

    def config_flip():
        facts = [fact(guard=Guard("compile", "watermark"))]
        old = graph(facts, config=(("watermark", False),))
        new = graph(facts, generation="g1", config=(("watermark", True),))
        equal(old.nodes, new.nodes)
        equal(old.facts, new.facts)
        cache = ReverseCache()
        equal(cache.query(old, "R")[0].items, ())
        result, hit = cache.query(new, "R")
        equal((result.items, hit), (("A",), False))
    run("H04_same_source_facts_changed_compile_config", config_flip)

    def runtime_false():
        g = graph([fact(guard=Guard("runtime", runtime_observation=False))])
        equal(full_query(g, "R").items, ("A",))
        equal(decisions(g)[0]["A"], "IN_SCOPE")
    run("H05_runtime_false_is_not_global_false", runtime_false)

    def unknown_guard():
        guard = Guard("compile", "missing")
        g = graph([fact(guard=guard)])
        equal(guard_state(guard, g), "UNKNOWN")
        equal(full_query(g, "R").items, ("A",))
        equal(decisions(g)[0]["A"], "IN_SCOPE")
    run("H06_unknown_guard_retains_may_edge", unknown_guard)

    def pinned_false():
        g = graph([fact(guard=Guard("compile", "x"))], config=(("x", False),))
        equal(full_query(g, "R").items, ())
        equal(decisions(g)[0]["A"], "EXCLUDED")
    run("H07_exact_pinned_false_can_exclude", pinned_false)

    def unpinned_false():
        g = graph([fact(guard=Guard("compile", "x"))], config=(("x", False),), pinned=False)
        equal(full_query(g, "R").items, ("A",))
    run("H08_unpinned_false_retains_may_edge", unpinned_false)

    def unknown_target():
        g = graph([fact(target=None)])
        result = indexed_query(g, build_indexes(g), "R")
        equal(result.items, ("A",))
        equal(result.complete_in_declared_scope, False)
        equal(result.unknown_targets, ("A_reads_None",))
        equal(decisions(g)[0]["A"], "UNKNOWN")
    run("H09_dynamic_unknown_target_is_not_absence", unknown_target)

    def incomplete_scope():
        g = graph(complete=False)
        result = full_query(g, "R")
        equal(result.items, ())
        equal(result.complete_in_declared_scope, False)
        equal(decisions(g)[1].complete_in_declared_scope, False)
    run("H10_empty_query_in_incomplete_scope_is_incomplete", incomplete_scope)

    def underdeclared_delta():
        delta = FacetClaim(frozenset({"order"}), Certificate(frozenset({"order", "values"})))
        rejects("UNDERDECLARED_FACETS", lambda: decisions(graph([fact()]), delta=delta))
    run("H11_underdeclared_delta_rejected", underdeclared_delta)

    def underdeclared_footprint():
        footprint = FacetClaim(frozenset({"order"}), Certificate(frozenset({"order", "values"})))
        rejects("UNDERDECLARED_FACETS", lambda: decisions(graph([fact(footprint=footprint)])))
    run("H12_underdeclared_consumer_footprint_rejected", underdeclared_footprint)

    def unknown_delta():
        delta = FacetClaim(frozenset({"order"}))
        ds, report = decisions(graph([fact()]), delta=delta)
        equal(ds["A"], "UNKNOWN")
        equal(report.complete_in_declared_scope, False)
    run("H13_unverified_delta_propagates_TOP", unknown_delta)

    def incomplete_footprint():
        g = graph([fact(footprint=certified("order", complete=False))])
        equal(decisions(g)[0]["A"], "UNKNOWN")
    run("H14_incomplete_footprint_propagates_TOP", incomplete_footprint)

    def registry_mismatch():
        fp = FacetClaim(frozenset({"order"}), Certificate(frozenset({"order"}), registry_id="foreign"))
        equal(decisions(graph([fact(footprint=fp)]))[0]["A"], "UNKNOWN")
    run("H15_facet_registry_mismatch_is_unknown", registry_mismatch)

    def mixed_generation():
        old = graph([fact()], generation="g0")
        new = replace(old, generation="g1")
        pair = IndexPair(build_indexes(old).forward, build_indexes(new).reverse)
        rejects("GENERATION_MISMATCH", lambda: indexed_query(new, pair, "R"))
    run("H16_mixed_index_generations_rejected", mixed_generation)

    def historical_views():
        old = graph([fact()], generation="g0")
        new = graph([fact("B")], generation="g1")
        equal(indexed_query(old, build_indexes(old), "R").items, ("A",))
        equal(indexed_query(new, build_indexes(new), "R").items, ("B",))
    run("H17_consistent_historical_generations_remain_readable", historical_views)

    def unchanged_extraction():
        g = graph([fact()])
        cache = ReverseCache()
        first, _ = cache.query(g, "R")
        second, hit = cache.query(replace(g, generation="g1"), "R")
        equal((first, hit), (second, True))
    run("H18_unchanged_declared_extraction_reuses", unchanged_extraction)

    def changed_extractor():
        g = graph([fact()])
        cache = ReverseCache()
        cache.query(g, "R")
        result, hit = cache.query(replace(g, extractor_version="extractor-v2"), "R")
        equal((result.items, hit), (("A",), False))
    run("H19_different_extractor_invalidates", changed_extractor)

    def stable_rename():
        g = graph([fact()])
        renamed = replace(g, generation="g1", nodes=tuple(
            replace(n, alias="display_name_changed") if n.entity_id == "A" else n
            for n in g.nodes))
        cache = ReverseCache()
        first, _ = cache.query(g, "R")
        second, hit = cache.query(renamed, "R")
        equal((first.items, second.items, hit), (("A",), ("A",), True))
    run("H20_nonreflective_alias_preserves_identity", stable_rename)

    def index_equals_scan():
        g = graph([fact("A"), fact("B", "Other"), fact("C", None)])
        equal(indexed_query(g, build_indexes(g), "R"), full_query(g, "R"))
    run("H21_indexed_query_equals_full_scan", index_equals_scan)

    def safe_stop():
        ds, report = decisions(graph([fact()]), delta=certified("order"))
        equal(ds["A"], "EXCLUDED")
        equal(report.complete_in_declared_scope, True)
    run("H22_two_complete_disjoint_bounds_allow_stop", safe_stop)

    def overlap():
        ds, report = decisions(graph([fact()]))
        equal(ds["A"], "IN_SCOPE")
        equal(report.complete_in_declared_scope, True)
    run("H23_verified_overlap_requires_review", overlap)

    def downstream_unknown():
        g = graph([fact("A"), fact("B", "A", kind="calls")])
        ds, report = decisions(g)
        equal(ds["A"], "IN_SCOPE")
        equal(ds["B"], "UNKNOWN")
        equal(report.complete_in_declared_scope, False)
    run("H24_missing_output_transfer_propagates_TOP", downstream_unknown)

    def two_candidates(order):
        store = HeadStore("S0")
        equal(store.accept("S0", order[0]), "ACCEPTED")
        equal(store.accept("S0", order[1]), "STALE_BASE")
        equal(store.head, order[0])
        equal(store.accepted, [order[0]])
    run("H25_concurrent_revisions_order_AB", lambda: two_candidates(("SA", "SB")))
    run("H26_concurrent_revisions_order_BA", lambda: two_candidates(("SB", "SA")))

    def same_generation_wrong_content():
        old = graph([fact()])
        new = graph([fact("B")])
        rejects("INDEX_CONTENT_MISMATCH", lambda: indexed_query(new, build_indexes(old), "R"))
    run("H27_same_generation_wrong_index_content_rejected", same_generation_wrong_content)

    def corrupted_rows():
        g = graph([fact()])
        pair = build_indexes(g)
        damaged_reverse = replace(pair, reverse=replace(pair.reverse, rows=()))
        rejects("INDEX_ROWS_MISMATCH", lambda: indexed_query(g, damaged_reverse, "R"))
        damaged_forward = replace(pair, forward=replace(pair.forward, rows=()))
        rejects("INDEX_ROWS_MISMATCH", lambda: indexed_query(g, damaged_forward, "R"))
    run("H28_corrupted_rows_with_valid_metadata_rejected", corrupted_rows)

    def missing_unknown_targets():
        g = graph([fact(target=None)])
        pair = build_indexes(g)
        damaged = replace(pair, reverse=replace(pair.reverse, unknown_fact_ids=()))
        rejects("INDEX_ROWS_MISMATCH", lambda: indexed_query(g, damaged, "R"))
    run("H29_dropped_unknown_fact_ids_rejected", missing_unknown_targets)

    def invalid_boolean_inputs():
        guarded = [fact(guard=Guard("compile", "x"))]
        for value in ("true", "false", 0, 1, None):
            rejects("INVALID_CONFIG_VALUE", lambda: graph(guarded, config=(("x", value),)))
            rejects("INVALID_GUARD_VALUE", lambda: graph([fact(guard=Guard("compile", "x", value))]))
            rejects("INVALID_GRAPH_COMPLETENESS", lambda: graph(pinned=value))
            rejects("INVALID_GRAPH_COMPLETENESS", lambda: graph(complete=value))
            rejects("INVALID_CERTIFICATE_COMPLETENESS",
                    lambda: Certificate(frozenset({"values"}), complete=value))
    run("H30_nonboolean_config_guard_or_completeness_rejected", invalid_boolean_inputs)

    def one_shot_scope():
        g = graph([fact()])
        cache = ReverseCache()
        expected = full_query(g, "R", ("A",))
        result, hit = cache.query(g, "R", iter(("A",)))
        equal(result, expected)
        equal((result.items, result.complete_in_declared_scope, hit), (("A",), True, False))
        result, hit = cache.query(g, "R", (member for member in ("A",)))
        equal(result, expected)
        equal(hit, True)
    run("H31_single_use_scope_iterator_is_preserved", one_shot_scope)
    return cases


def mutation_checks():
    bad_cache = ReturnedItemsOnlyCache()
    base = graph()
    changed = graph([fact("B")], generation="g1")
    bad_cache.query(base, "R")
    bad_result, bad_hit = bad_cache.query(changed, "R")
    expected = ("B",)
    first = {"id": "M1_returned_items_only_cache", "distinguishing_case": "empty result then B reads R",
             "expected_items": list(expected), "mutant_items": list(bad_result.items),
             "mutant_reported_cache_hit": bad_hit, "killed": bad_result.items != expected}
    g = graph([fact()])
    delta = FacetClaim(frozenset({"order"}), Certificate(frozenset({"order", "values"}), complete=False))
    safe = dict(impact(g, g, "R", delta).decisions)["A"]
    bad = dict(impact(g, g, "R", delta, unsafe_declared_facets=True).decisions)["A"]
    second = {"id": "M2_declared_facets_treated_as_verified",
              "distinguishing_case": "incomplete delta declaration hides values",
              "expected_decision": "UNKNOWN", "correct_decision": safe,
              "mutant_decision": bad, "killed": safe == "UNKNOWN" and bad == "EXCLUDED"}
    return [first, second]


def bounded_checks():
    states = []
    # Exhaustive only within this explicitly listed finite domain.
    for modes in product(range(4), repeat=2):
        for cfg in ("false", "true", "unpinned_false"):
            for complete in (False, True):
                facts = []
                for source, mode in zip(("A", "B"), modes):
                    if mode == 1:
                        facts.append(fact(source))
                    elif mode == 2:
                        facts.append(fact(source, "Other"))
                    elif mode == 3:
                        facts.append(fact(source, guard=Guard("compile", "x")))
                states.append(graph(facts, generation=f"bounded_{len(states)}",
                                    config=(("x", cfg == "true"),),
                                    pinned=cfg != "unpinned_false", complete=complete))
    indexed_count = 0
    for g in states:
        equal(indexed_query(g, build_indexes(g), "R"), full_query(g, "R"))
        indexed_count += 1
    transition_count = 0
    for old, new in product(states, repeat=2):
        cache = ReverseCache()
        cache.query(old, "R")
        result, hit = cache.query(new, "R")
        equal(result, full_query(new, "R"))
        equal(hit, membership_key(old, "R") == membership_key(new, "R"))
        transition_count += 1
    facet_domain = ("values", "order", "errors")
    subsets = [frozenset(c) for length in range(4) for c in combinations(facet_domain, length)]
    facet_count = 0
    for changed, used, delta_complete, footprint_complete in product(subsets, subsets, (False, True), (False, True)):
        delta = certified(*changed, complete=delta_complete)
        footprint = certified(*used, complete=footprint_complete)
        g = graph([fact(footprint=footprint)])
        actual = dict(impact(g, g, "R", delta).decisions)["A"]
        expected = ("UNKNOWN" if not (delta_complete and footprint_complete)
                    else "EXCLUDED" if not (changed & used) else "IN_SCOPE")
        equal(actual, expected)
        facet_count += 1
    return {"status": "PASS", "graph_states": len(states),
            "indexed_equals_full_cases": indexed_count,
            "all_ordered_graph_transition_cases": transition_count,
            "facet_bound_cases": facet_count,
            "total_assertion_cases": indexed_count + transition_count + facet_count,
            "domain": {"operation_nodes": ["A", "B"],
                       "edge_modes": ["none", "reads_R", "reads_Other", "reads_R_if_config_x"],
                       "config_modes": ["pinned_false", "pinned_true", "unpinned_false"],
                       "scope_complete": [False, True], "facet_subset_domain": list(facet_domain)},
            "meaning": "finite cache consistency and synthetic facet-rule checks, not semantic completeness"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="results/link-model/report.json")
    args = parser.parse_args()
    started = time.monotonic()
    manual = manual_cases()
    mutants = mutation_checks()
    try:
        bounded = bounded_checks()
    except Exception as error:
        bounded = {"status": "FAIL", "error": repr(error)}
    source_dir = Path(__file__).resolve().parent
    hashes = {name: sha256((source_dir/name).read_bytes()).hexdigest()
              for name in ("model.py", "verify.py", "README.md")}
    success = all(x["status"] == "PASS" for x in manual) and all(x["killed"] for x in mutants) and bounded["status"] == "PASS"
    report = {"report_format": "bagaev-finite-link-model/1", "status": "PASS" if success else "FAIL",
              "generated_utc": datetime.now(timezone.utc).isoformat(),
              "python_version": platform.python_version(), "elapsed_seconds": round(time.monotonic()-started, 6),
              "bagaev_execution": False, "hypothesis_tested": False,
              "tasks_closed": [], "T08_status": "NOT_CLOSED", "T09_status": "NOT_CLOSED",
              "reproducible_command": "python -B experiments/link-model/verify.py --output results/link-model/report.json",
              "command_working_directory": "package root", "source_sha256": hashes,
              "synthetic_assumptions": ["manually supplied finite typed facts, not real compiler extraction",
                                        "trusted fixture completeness certificates, not real proofs",
                                        "shared synthetic registry with independent observation coordinates",
                                        "nonreflective aliases", "sequential CAS model, not durable concurrent storage"],
              "scope_limits": ["does not execute bagaev", "does not validate natural-language intent",
                               "does not establish arbitrary-project completeness", "does not compare A/B/C product cost",
                               "HeadStore assumes prevalidated candidates; it models only pointer CAS, not acceptance eligibility",
                               "full-versus-incremental comparison only establishes cache consistency on this domain"],
              "manual_cases": manual, "manual_passed": sum(x["status"]=="PASS" for x in manual),
              "manual_failed": sum(x["status"]!="PASS" for x in manual),
              "mutants": mutants, "bounded": bounded}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({"status": report["status"], "manual_passed": report["manual_passed"],
                      "manual_failed": report["manual_failed"], "mutants_killed": sum(x["killed"] for x in mutants),
                      "bounded": bounded, "report": str(output)}, ensure_ascii=False))
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
