#!/usr/bin/env python3
"""Finite independent verification of R03 checked, analysis-only rewrites.

The R02 oracle is imported unchanged and never imports either engine or laws.
This verifier does not establish a machine-checked universal law proof.
"""
from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from itertools import permutations, product
import json
from pathlib import Path
import platform
import sys
import time

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
R02_ROOT = PACKAGE_ROOT / 'experiments/observation-profile'
sys.path.insert(0, str(R02_ROOT))
import oracle
import laws
engine = laws.engine

EXECUTION_FIELDS = ('status', 'value', 'error', 'trace', 'complete')


def plain(value):
    if isinstance(value, Mapping):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return {'$set': sorted(plain(item) for item in value)}
    return value


def encoded(value):
    return json.dumps(plain(value), ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def equal(actual, expected, label=''):
    if encoded(actual) != encoded(expected):
        raise AssertionError(f'{label}: actual={actual!r}; expected={expected!r}')


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def dump(value):
    return engine.to_data(value)


def resource(spec):
    return None if spec is None else engine.ResourceState(tuple(spec['members']), spec.get('read_error'))


def engine_observations(result):
    return {'status': result.status, 'value': plain(result.value), 'error': result.error,
            'trace': [{'label': item.label, 'value': plain(item.value)} for item in result.trace],
            'complete': result.complete}


def changed_execution(before, after):
    return [key for key in EXECUTION_FIELDS if encoded(before[key]) != encoded(after[key])]


def require_exclusion_sound(assessment, before, after, label):
    if assessment.decision == 'EXCLUDED':
        require(before['complete'] is True and after['complete'] is True,
                'Unknown execution cannot justify exclusion: ' + label)
        equal(before, after, 'false exclusion: ' + label)


def consumer(row, identifier='article.consumer', **overrides):
    values = {'stable_id': identifier, 'program': row['ast'],
              'compile_config': row.get('compile_config', {})}
    values.update(overrides)
    return engine.Consumer(**values)


def program_registry(base_fixtures, fixtures):
    registry = {}
    for cohort, rows in (('r02', base_fixtures['programs']), ('law', fixtures['programs'])):
        for row in rows:
            ref = cohort + ':' + row['id']
            require(ref not in registry, 'Duplicate program reference: ' + ref)
            registry[ref] = {**row, 'ref': ref, 'cohort': cohort}
    return registry


def finite_resources(domain):
    rows = []
    for length in range(domain['maximum_length'] + 1):
        for members in permutations(domain['author_ids'], length):
            rows.append({'id': 'members:' + (','.join(members) or 'empty'),
                         'value': {'members': list(members)}})
    if domain['include_missing']:
        rows.append({'id': 'missing', 'value': None})
    for error in domain['additional_read_errors']:
        rows.append({'id': 'read_error:' + error, 'value': {'members': [], 'read_error': error}})
    return rows


def intermediate_trees(proof):
    """Reconstruct exact whole-tree substitutions without using the law kernel."""
    current = plain(proof.original_ast)
    results = []
    for step in proof.steps:
        tree = json.loads(encoded(current))
        selected = tree
        for token in step.path:
            selected = selected[token]
        equal(selected, step.before, 'independent intermediate before subtree')
        if step.path:
            parent = tree
            for token in step.path[:-1]:
                parent = parent[token]
            parent[step.path[-1]] = plain(step.after)
        else:
            tree = plain(step.after)
        current = tree
        results.append(current)
    equal(current, proof.normalized_ast, 'independent reconstructed final tree')
    return results


def run_cases(actions):
    results = []
    for identifier, action in actions:
        try:
            result = action()
            results.append({'id': identifier, 'status': 'PASS', 'details': result})
        except Exception as error:
            results.append({'id': identifier, 'status': 'FAIL', 'error': repr(error)})
    return results


def rejects(action, expected=None):
    try:
        action()
    except (laws.LawError, engine.ProfileError) as error:
        if expected is not None:
            accepted = {expected} if isinstance(expected, str) else set(expected)
            require(error.code in accepted, f'wrong diagnostic {error.code!r}, expected {accepted!r}')
        return {'diagnostic': error.code, 'exception': type(error).__name__}
    raise AssertionError('The invalid proof or input was accepted')


def normalization_contract_checks(fixtures, programs):
    actions = []
    for case in fixtures['normalization_expectations']:
        def check(case=case):
            row = programs[case['program_ref']]
            item = consumer(row)
            original = encoded(item.program)
            proof = laws.normalize(item)
            checked = laws.replay(item, proof)
            refined = laws.refined_use(item, derivation=proof)
            equal(proof.normalized_ast, case['expected_normalized_ast'], 'authored normalized AST')
            equal([step.rule_id for step in proof.steps], case['expected_rule_ids'], 'authored rule sequence')
            equal([step.path for step in proof.steps], case['expected_paths'], 'authored rewrite paths')
            equal(sorted(refined.summary.required_observations), case['expected_refined_observations'])
            equal(refined.summary.complete, case['expected_complete'])
            require(checked.saturated is True and refined.saturated is True, 'normalize did not saturate')
            equal(dump(checked.summary), dump(refined.summary))
            equal(dump(engine.validate_program(item.program, item.compile_config)),
                  dump(engine.validate_program(proof.normalized_ast, item.compile_config)),
                  'whole AST type is preserved')
            require(encoded(item.program) == original, 'analysis-only normalization changed the original consumer')
            return {'program_ref': case['program_ref'], 'derivation': dump(proof),
                    'refined_use': dump(refined.summary), 'saturated': True,
                    'original_consumer_unchanged': True}
        actions.append((case['program_ref'], check))
    return run_cases(actions)


def manual_checks(fixtures, programs):
    actions = []
    for case in fixtures['manual_cases']:
        def check(case=case):
            row = programs[case['program_ref']]; item = consumer(row)
            proof = laws.normalize(item)
            executed = []
            for side in ('before', 'after'):
                expected = case['expected_' + side]
                original = oracle.observations(oracle.execute(row['ast'], case[side], row['compile_config']))
                normalized = oracle.observations(oracle.execute(plain(proof.normalized_ast), case[side], row['compile_config']))
                main_original = engine_observations(engine.execute(item.program, resource(case[side]), item.compile_config))
                main_normalized = engine_observations(engine.execute(proof.normalized_ast, resource(case[side]), item.compile_config))
                for label, actual in (('oracle original', original), ('oracle normalized', normalized),
                                      ('engine original', main_original), ('engine normalized', main_normalized)):
                    equal(actual, expected, 'authored ' + label + '/' + side)
                executed.append(original)
            base = engine.assess(item, item, resource(case['before']), resource(case['after']))
            refined = laws.assess(item, item, resource(case['before']), resource(case['after']),
                                  before_derivation=proof, after_derivation=proof)
            equal(base.decision, case['expected_r02_decision'], 'R02 manual decision')
            equal(refined.decision, case['expected_refined_decision'], 'refined manual decision')
            require_exclusion_sound(refined, *executed, case['id'])
            return {'program_ref': case['program_ref'], 'purpose': case['purpose'],
                    'r02_assessment': dump(base), 'refined_assessment': dump(refined),
                    'executed_before': executed[0], 'executed_after': executed[1],
                    'actual_changed_execution_observations': changed_execution(*executed),
                    'normalization_preserved_authored_observations': True}
        actions.append((case['id'], check))
    return run_cases(actions)


def bounded_checks(programs, base_fixtures, base_report):
    resources = finite_resources(base_fixtures['domain'])
    cohort_totals = {'r02': Counter(), 'law': Counter()}
    results = []
    for ref, row in programs.items():
        item = consumer(row); proof = laws.normalize(item)
        checked = laws.replay(item, proof)
        require(checked.saturated is True, 'default normalization is not saturated')
        intermediates = intermediate_trees(proof)
        executed = {}; complete_states = 0
        for state in resources:
            original = oracle.observations(oracle.execute(row['ast'], state['value'], row['compile_config']))
            normalized = oracle.observations(oracle.execute(plain(proof.normalized_ast), state['value'], row['compile_config']))
            equal(original, normalized, 'independent original/normalized outcome: ' + ref + '/' + state['id'])
            equal(engine_observations(engine.execute(item.program, resource(state['value']), item.compile_config)),
                  original, 'original engine/oracle: ' + ref)
            equal(engine_observations(engine.execute(proof.normalized_ast, resource(state['value']), item.compile_config)),
                  normalized, 'normalized engine/oracle: ' + ref)
            preceding = original
            for index, intermediate in enumerate(intermediates):
                observed = normalized if index == len(intermediates)-1 else oracle.observations(
                    oracle.execute(intermediate, state['value'], row['compile_config']))
                equal(preceding, observed, 'independent single-step outcome: ' + ref + '/' + str(index))
                preceding = observed
            executed[state['id']] = original
            complete_states += original['complete'] is True
        transitions = Counter(); patterns = Counter(); exclusions = []; new_exclusions = []
        counts = Counter(program_cases=1, execution_cases_per_variant_per_interpreter=len(resources),
                         complete_resource_executions=complete_states,
                         incomplete_resource_executions=len(resources)-complete_states,
                         single_step_transition_cases=len(proof.steps)*len(resources),
                         additional_oracle_intermediate_execution_cases=max(len(proof.steps)-1,0)*len(resources))
        for before, after in product(resources, repeat=2):
            base = engine.assess(item, item, resource(before['value']), resource(after['value']))
            refined = laws.assess(item, item, resource(before['value']), resource(after['value']),
                                  before_derivation=proof, after_derivation=proof)
            old, new = executed[before['id']], executed[after['id']]
            changed = changed_execution(old, new)
            complete = old['complete'] is True and new['complete'] is True
            require_exclusion_sound(base, old, new, 'R02/' + ref)
            require_exclusion_sound(refined, old, new, 'R03/' + ref)
            if base.decision == 'EXCLUDED':
                equal(refined.decision, 'EXCLUDED', 'sound old exclusions must be retained')
            if base.decision == 'UNKNOWN':
                equal(refined.decision, 'UNKNOWN', 'catalog must not erase unknown behavior')
            transitions[(base.decision, refined.decision)] += 1
            patterns[(base.decision, refined.decision, tuple(changed))] += 1
            counts['assessment_pairs'] += 1
            counts['r02_' + base.decision.lower()] += 1
            counts['refined_' + refined.decision.lower()] += 1
            if complete and not changed:
                counts['equal_complete_original_outcomes'] += 1
                if base.decision == 'RECHECK': counts['r02_conservative_rechecks'] += 1
                if refined.decision == 'RECHECK': counts['remaining_conservative_rechecks'] += 1
            if refined.decision == 'EXCLUDED':
                exclusions.append([before['id'], after['id']])
                if base.decision != 'EXCLUDED':
                    equal(base.decision, 'RECHECK', 'unknown execution was promoted')
                    new_exclusions.append([before['id'], after['id']])
                    counts['newly_excluded_pairs'] += 1
        cohort_totals[row['cohort']].update(counts)
        results.append({'program_ref': ref, 'cohort': row['cohort'], 'normalization_step_count': len(proof.steps),
                        'original_required_observations': sorted(engine.infer_use(item.program, item.compile_config).required_observations),
                        'refined_required_observations': sorted(checked.summary.required_observations),
                        'counts': dict(counts),
                        'decision_transitions': [{'r02': a, 'refined': b, 'pair_count': count}
                                                 for (a,b),count in sorted(transitions.items())],
                        'actual_change_patterns': [{'r02': a, 'refined': b,
                                                    'actual_changed_execution_observations': list(changed),
                                                    'pair_count': count}
                                                   for (a,b,changed),count in sorted(patterns.items())],
                        'refined_excluded_resource_pairs': exclusions,
                        'newly_excluded_resource_pairs': new_exclusions,
                        'all_refined_exclusions_have_equal_complete_independent_original_outcomes': True})
    inherited = base_report['bounded_observation_checks']; old = cohort_totals['r02']
    for actual, expected in ((old['program_cases'], inherited['program_count']),
                             (old['assessment_pairs'], inherited['assessment_cases']),
                             (old['r02_excluded'], inherited['excluded_cases_checked']),
                             (old['r02_unknown'], inherited['unknown_cases']),
                             (old['r02_conservative_rechecks'], inherited['conservative_rechecks_with_equal_observations'])):
        equal(actual, expected, 'unchanged R02 corpus/decision baseline')
    total = cohort_totals['r02'] + cohort_totals['law']
    return {'status': 'PASS', 'resource_domain_ref': 'fixtures/programs.json#/domain',
            'resources': resources, 'resource_count': len(resources),
            'ordered_resource_pair_count_per_program': len(resources)**2,
            'cohorts': {name: dict(counts) for name,counts in cohort_totals.items()},
            'totals': dict(total), 'false_refined_exclusions': 0,
            'original_normalized_mismatches_in_corpus': 0,
            'r02_baseline_counts_reproduced_on_identical_programs_and_resources': True,
            'program_results': results,
            'scope': 'All ordered resource pairs for these fixed program/configuration cases only. Incomplete execution prefix equality is not a semantic certificate.',
            'performance_benchmark_performed': False,
            'precision_comparison_is_not_a_speedup_measurement': True}


def source_hashes(base_report):
    references = set(base_report['source_sha256']) | {
        'results/observation-profile/report.json',
        'experiments/law-profile/laws.py', 'experiments/law-profile/verify.py',
        'experiments/law-profile/API.md', 'experiments/law-profile/README.md',
        'fixtures/law-programs.json'}
    return {ref: sha256((PACKAGE_ROOT/ref).read_bytes()).hexdigest() for ref in sorted(references)}


def inherited_source_check(base_report):
    results = {ref: sha256((PACKAGE_ROOT/ref).read_bytes()).hexdigest() == digest
               for ref,digest in base_report['source_sha256'].items()}
    require(results and all(results.values()), 'An inherited frozen R02 source/fixture was changed')
    return {'status': 'PASS', 'source_report_ref': 'results/observation-profile/report.json',
            'recorded_R02_source_hashes_match': results,
            'oracle_imports_engine_or_laws': False}


def guarded(action):
    try:
        return action()
    except Exception as error:
        return {'status': 'FAIL', 'error': repr(error)}


def proof_boundary_checks(programs):
    row = programs['r02:size_ordered']; item = consumer(row); proof = laws.normalize(item)
    step = proof.steps[0]
    actions = []

    def context_fields(names):
        records = []
        for name in names:
            current = getattr(proof.context, name)
            forged = replace(proof, context=replace(proof.context, **{name: str(current) + '/stale'}))
            records.append({'field': name, **rejects(lambda: laws.replay(item, forged), 'PROOF_CONTEXT_MISMATCH')})
        return records
    actions.append(('N01_exact_consumer_context', lambda: context_fields(
        ('stable_id','program_revision','config_stamp','provider_revision','requirements_stamp'))))
    actions.append(('N02_exact_semantics_and_catalog_context', lambda: context_fields(
        ('profile_revision','semantics_id','engine_sha256','law_kernel_sha256','catalog_revision','catalog_sha256'))))
    actions.append(('N03_original_AST_mismatch', lambda: rejects(
        lambda: laws.replay(item, replace(proof, original_ast={'op':'const','value':0})), 'ORIGINAL_AST_MISMATCH')))
    actions.append(('N04_unknown_rule', lambda: rejects(
        lambda: laws.replay(item, replace(proof, steps=(replace(step, rule_id='UNREGISTERED_RULE'),))), 'UNKNOWN_RULE')))

    def invalid_paths():
        return [{'path': list(path), **rejects(
            lambda path=path: laws.replay(item, replace(proof, steps=(replace(step,path=path),))),
            'INVALID_REWRITE_PATH')} for path in (('not_a_child',), ('value','view'), ('op',))]
    actions.append(('N05_paths_must_select_AST_children', invalid_paths))

    def boolean_index():
        tuple_item = consumer(programs['law:tuple_three_laws'])
        tuple_proof = laws.normalize(tuple_item)
        steps = (replace(tuple_proof.steps[0],path=('items',True)),) + tuple_proof.steps[1:]
        return rejects(lambda: laws.replay(tuple_item,replace(tuple_proof,steps=steps)), 'INVALID_REWRITE_PATH')
    actions.append(('N06_bool_is_not_a_path_index', boolean_index))
    actions.append(('N07_step_before_is_exact', lambda: rejects(
        lambda: laws.replay(item, replace(proof, steps=(replace(step,before={'op':'const','value':0}),))),
        'STEP_BEFORE_MISMATCH')))

    def wrong_redex():
        head_item = consumer(programs['r02:head']); head_proof = laws.normalize(head_item)
        bad_step = replace(step, before=head_item.program)
        forged = replace(head_proof, normalized_ast=step.after, steps=(bad_step,))
        return rejects(lambda: laws.replay(head_item,forged), 'RULE_NOT_APPLICABLE')
    actions.append(('N08_head_does_not_match_size_rule', wrong_redex))
    actions.append(('N09_step_after_is_computed_by_kernel', lambda: rejects(
        lambda: laws.replay(item,replace(proof,steps=(replace(step,after={'op':'const','value':0}),))),
        'STEP_AFTER_MISMATCH')))
    actions.append(('N10_guard_stamp_is_not_a_promise', lambda: rejects(
        lambda: laws.replay(item,replace(proof,steps=(replace(step,guard_stamp='forged-guard'),))),
        'GUARD_STAMP_MISMATCH')))
    actions.append(('N11_final_tree_must_match_replayed_chain', lambda: rejects(
        lambda: laws.replay(item,replace(proof,normalized_ast={'op':'const','value':0})),
        'NORMAL_FORM_MISMATCH')))

    def invalid_whole_program():
        invalid = {'op':'if','condition':{'op':'const','value':False},
                   'then':{'op':'head','value':{'op':'read','view':'member_set'}},
                   'else':{'op':'const','value':'ok'}}
        records = [rejects(lambda: engine.Consumer('bad',invalid), 'TYPE_MISMATCH')]
        invalid_normal = {'op':'head','value':{'op':'read','view':'member_set'}}
        records.append(rejects(lambda: laws.replay(item,replace(proof,normalized_ast=invalid_normal))))
        return {'diagnostics': records,
                'invalid_unexecuted_branch_rejected_before_any_rewrite': True,
                'invalid_claimed_final_tree_not_accepted': True}
    actions.append(('N12_whole_AST_typing_is_not_replaced_by_local_matching', invalid_whole_program))

    def unsupported_provider():
        other = consumer(row,provider_revision='provider/v2')
        failure = rejects(lambda: laws.normalize(other), 'UNSUPPORTED_PROVIDER_REVISION')
        before, after = engine.ResourceState(('a','b')), engine.ResourceState(('b','a'))
        assessment = laws.assess(other,other,before,after)
        require(assessment.decision != 'EXCLUDED', 'unsupported provider received size/order refinement')
        return {'normalization':failure,'fallback':dump(assessment)}
    actions.append(('N13_unproved_provider_gets_no_law_refinement', unsupported_provider))

    def unique_domain():
        failure = rejects(lambda: engine.ResourceState(('a','a')), 'DUPLICATE_AUTHOR_ID')
        try:
            oracle.execute(programs['r02:size_set']['ast'],{'members':['a','a']})
        except oracle.OracleInputError:
            return {'engine':failure,'independent_oracle_rejected_out_of_domain_resource':True}
        raise AssertionError('The independent oracle accepted an out-of-domain duplicate resource')
    actions.append(('N14_uniqueness_is_an_input_domain_guard', unique_domain))

    def stale_config():
        config_row = programs['law:config_same_count']
        configured = consumer(config_row); old_proof = laws.normalize(configured)
        modified = consumer(config_row,compile_config={'enabled':False})
        return rejects(lambda: laws.assess(configured,modified,engine.ResourceState(('a',)),
                                          engine.ResourceState(('a',)),before_derivation=old_proof,
                                          after_derivation=old_proof), 'PROOF_CONTEXT_MISMATCH')
    actions.append(('N15_assessment_does_not_accept_stale_provided_proof', stale_config))

    def empty_partial():
        partial = replace(proof, normalized_ast=item.program, steps=())
        checked = laws.replay(item,partial)
        refined = laws.refined_use(item,derivation=partial)
        require(checked.saturated is False and refined.saturated is False, 'partial proof was mislabeled saturated')
        equal(sorted(checked.summary.required_observations),['ordered_members','read_status'])
        return {'saturated':False,'summary':dump(checked.summary),'valid_zero_step_chain':True}
    actions.append(('P01_valid_unsaturated_zero_step_chain', empty_partial))

    def nested_partial():
        nested = consumer(programs['law:nested_count']); full = laws.normalize(nested)
        intermediate = {'op':'size','value':{'op':'read','view':'member_set'}}
        partial = replace(full,normalized_ast=intermediate,steps=full.steps[:1])
        checked = laws.replay(nested,partial)
        require(checked.saturated is False, 'partial nested proof was mislabeled saturated')
        equal(sorted(checked.summary.required_observations),['member_set','read_status'])
        before,after=engine.ResourceState(('a',)),engine.ResourceState(('b',))
        partial_assessment=laws.assess(nested,nested,before,after,before_derivation=partial,after_derivation=partial)
        full_assessment=laws.assess(nested,nested,before,after,before_derivation=full,after_derivation=full)
        equal(partial_assessment.decision,'RECHECK'); equal(full_assessment.decision,'EXCLUDED')
        return {'partial_derivation':dump(partial),'partial_assessment':dump(partial_assessment),
                'saturated_assessment':dump(full_assessment),'saturated':False}
    actions.append(('P02_valid_partial_chain_keeps_conservative_use', nested_partial))
    return run_cases(actions)


def equivalence_checks(fixtures, programs):
    goldens = {row['program_ref']:row for row in fixtures['normalization_expectations']}
    lhs = consumer(programs['r02:size_ordered'])
    rhs = engine.Consumer(lhs.stable_id,{'op':'read','view':'count'})
    same = {'members':['a','b']}
    actions = []

    def observed_pair(before,after,before_data,after_data):
        return (oracle.observations(oracle.execute(plain(before.program),before_data,plain(before.compile_config))),
                oracle.observations(oracle.execute(plain(after.program),after_data,plain(after.compile_config))))

    def supported_pair(ref,before_data,after_data,expected):
        before = consumer(programs[ref])
        after = engine.Consumer(before.stable_id,goldens[ref]['expected_normalized_ast'],
                                compile_config=plain(before.compile_config))
        equivalence=laws.derive_equivalence(before,after)
        equal(equivalence.status,'PROVED'); require(equivalence.certificate is not None,'missing certificate')
        verified=laws.verify_equivalence(before,after,equivalence.certificate)
        ordinary=laws.assess(before,after,resource(before_data),resource(after_data))
        explicit=laws.assess_equivalent_edit(before,after,resource(before_data),resource(after_data),
                                            certificate=equivalence.certificate)
        equal(ordinary.decision,'RECHECK','ordinary source revision guard')
        equal(explicit.decision,expected,'explicit equivalent edit decision')
        equal(explicit.basis,'r03_common_normal_form')
        original_outcomes=observed_pair(before,after,before_data,after_data)
        require_exclusion_sound(explicit,*original_outcomes,ref+'/equivalent edit')
        return {'program_ref':ref,'certificate':dump(equivalence.certificate),
                'ordinary_assessment':dump(ordinary),'equivalent_edit_assessment':dump(explicit),
                'independent_before':original_outcomes[0],'independent_after':original_outcomes[1],
                'actual_changed_execution_observations':changed_execution(*original_outcomes),
                'saturated':verified.saturated}

    for identifier,ref in (('E01_size_ordered_edit','r02:size_ordered'),
                           ('E02_to_set_ordered_edit','r02:to_set_ordered'),
                           ('E03_size_member_set_edit','r02:size_set'),
                           ('E04_set_identity_edit','law:set_identity')):
        actions.append((identifier,lambda ref=ref:supported_pair(ref,same,same,'EXCLUDED')))
    actions.append(('E05_supported_edit_and_permutation',lambda:supported_pair(
        'r02:size_ordered',{'members':['a','b']},{'members':['b','a']},'EXCLUDED')))
    actions.append(('E06_supported_edit_and_insertion',lambda:supported_pair(
        'r02:size_ordered',{'members':['a']},{'members':['a','b']},'RECHECK')))
    actions.append(('E07_supported_edit_and_read_error_transition',lambda:supported_pair(
        'r02:size_ordered',None,{'members':['a']},'RECHECK')))

    def coincidental_equality():
        constant = engine.Consumer(lhs.stable_id,{'op':'const','value':1})
        result=laws.derive_equivalence(lhs,constant)
        equal(result.status,'UNPROVED'); require(result.certificate is None,'different forms received certificate')
        data={'members':['a']}; observations=observed_pair(lhs,constant,data,data)
        equal(*observations,'equal current output is not a law')
        assessment=laws.assess_equivalent_edit(lhs,constant,resource(data),resource(data))
        equal(assessment.decision,'RECHECK')
        return {'status':result.status,'reasons':list(result.reasons),'same_current_observations':observations[0],
                'assessment':dump(assessment),'inequivalence_claimed':False}
    actions.append(('E08_equal_current_output_with_different_forms_is_unproved',coincidental_equality))

    def unknown_equivalence():
        item=consumer(programs['r02:opaque_external'])
        result=laws.derive_equivalence(item,item)
        equal(result.status,'UNPROVED'); require(result.certificate is None,'unknown got a certificate')
        assessment=laws.assess_equivalent_edit(item,item,resource(same),resource(same))
        equal(assessment.decision,'UNKNOWN')
        proof=laws.normalize(item)
        certificate=laws.EquivalenceCertificate(proof,proof,proof.normalized_ast)
        rejected=rejects(lambda:laws.verify_equivalence(item,item,certificate),'INCOMPLETE_EQUIVALENCE')
        return {'status':result.status,'assessment':dump(assessment),'forged_unknown_certificate':rejected}
    actions.append(('E09_identical_unknown_forms_do_not_prove_equivalence',unknown_equivalence))

    def changed_context(kind):
        if kind=='config':
            row=programs['law:config_same_count']; before=consumer(row)
            after=engine.Consumer(before.stable_id,goldens[row['ref']]['expected_normalized_ast'],
                                  compile_config={'enabled':False})
        elif kind=='provider':
            before=lhs; after=engine.Consumer(lhs.stable_id,rhs.program,provider_revision='provider/v2')
        elif kind=='new_requirement':
            before=lhs; after=engine.Consumer(lhs.stable_id,rhs.program,requirements={'nonempty':'r1'})
        else:
            before=engine.Consumer(lhs.stable_id,lhs.program,requirements={'nonempty':'r1'}); after=rhs
        result=laws.derive_equivalence(before,after)
        equal(result.status,'UNPROVED'); require(result.certificate is None,'changed context got a certificate')
        assessment=laws.assess_equivalent_edit(before,after,resource(same),resource(same))
        require(assessment.decision in {'RECHECK','UNKNOWN'},'context/requirement change was excluded')
        if kind=='new_requirement':equal([r.status for r in assessment.requirements],['OPEN'])
        if kind=='removed_requirement':equal([r.status for r in assessment.requirements],['REMOVAL_OPEN'])
        return {'condition':kind,'status':result.status,'reasons':list(result.reasons),'assessment':dump(assessment)}
    for identifier,kind in (('E10_changed_config','config'),('E11_changed_provider','provider'),
                            ('E12_new_requirement_remains_open','new_requirement'),
                            ('E13_removed_requirement_remains_open','removed_requirement')):
        actions.append((identifier,lambda kind=kind:changed_context(kind)))

    def unchanged_requirement():
        before=engine.Consumer(lhs.stable_id,lhs.program,requirements={'nonempty':'r1'})
        after=engine.Consumer(lhs.stable_id,rhs.program,requirements={'nonempty':'r1'})
        result=laws.derive_equivalence(before,after); equal(result.status,'PROVED')
        assessment=laws.assess_equivalent_edit(before,after,resource(same),resource(same),certificate=result.certificate)
        equal(assessment.decision,'EXCLUDED')
        equal([r.status for r in assessment.requirements],['UNCHANGED_UNASSESSED'])
        return {'assessment':dump(assessment),'requirement_satisfaction_established':False}
    actions.append(('E14_semantic_equivalence_does_not_accept_requirements',unchanged_requirement))

    def stale_and_forged_certificate():
        certificate=laws.derive_equivalence(lhs,rhs).certificate
        altered=engine.Consumer(rhs.stable_id,{'op':'const','value':2})
        stale=rejects(lambda:laws.verify_equivalence(lhs,altered,certificate),'PROOF_CONTEXT_MISMATCH')
        forged=rejects(lambda:laws.verify_equivalence(lhs,rhs,replace(certificate,common_form={'op':'const','value':2})),
                       'COMMON_FORM_MISMATCH')
        domain=rejects(lambda:laws.verify_equivalence(lhs,rhs,replace(certificate,observation_domain='value_only')),
                       'OBSERVATION_DOMAIN_MISMATCH')
        return {'stale_program':stale,'forged_common_form':forged,'wrong_observation_domain':domain}
    actions.append(('E15_certificate_binds_both_originals_form_and_observation_domain',stale_and_forged_certificate))

    def partial_common_form():
        before=consumer(programs['law:nested_count']); after=consumer(programs['r02:size_set'])
        full=laws.normalize(before); after_full=laws.normalize(after)
        partial=replace(full,normalized_ast=after.program,steps=full.steps[:1])
        zero=replace(after_full,normalized_ast=after.program,steps=())
        result=laws.derive_equivalence(before,after,before_derivation=partial,after_derivation=zero)
        equal(result.status,'PROVED')
        verified=laws.verify_equivalence(before,after,result.certificate)
        require(verified.saturated is False,'partial common form was called saturated')
        perm=laws.assess_equivalent_edit(before,after,engine.ResourceState(('a','b')),
                                         engine.ResourceState(('b','a')),certificate=result.certificate)
        replacement=laws.assess_equivalent_edit(before,after,engine.ResourceState(('a',)),
                                                engine.ResourceState(('b',)),certificate=result.certificate)
        equal(perm.decision,'EXCLUDED'); equal(replacement.decision,'RECHECK')
        observations=observed_pair(before,after,{'members':['a','b']},{'members':['b','a']})
        require_exclusion_sound(perm,*observations,'partial common form')
        return {'certificate':dump(result.certificate),'saturated':False,
                'permutation':dump(perm),'identity_replacement':dump(replacement)}
    actions.append(('E16_partial_verified_common_form_is_sufficient_but_conservative',partial_common_form))
    return run_cases(actions)


def mutation_checks(programs):
    definitions = [
        ('M1_DROP_ORDER_DEPENDENT_GUARD','law:conditional_head_count',
         {'members':['a','b']},{'members':['b','a']},{'op':'read','view':'count'},
         'An invalid contextual rewrite discards the order-dependent branch condition and keeps only count.'),
        ('M2_DROP_STRICT_UNUSED_INITIALIZER','r02:unused_let_head',
         {'members':[]},{'members':['a']},{'op':'const','value':'ok'},
         'An invalid contextual rewrite discards a strict unused initializer that can raise EMPTY_HEAD.'),
        ('M3_DROP_ORDERED_EFFECT','law:emit_ordered_then_count',
         {'members':['a','b']},{'members':['b','a']},{'op':'read','view':'count'},
         'An invalid contextual rewrite erases an ordered emit while preserving the ordinary return value.'),
    ]
    results=[]
    for identifier,ref,before,after,bad_ast,fault in definitions:
        row=programs[ref]; item=consumer(row); proof=laws.normalize(item)
        forged=replace(proof,normalized_ast=bad_ast)
        rejection=rejects(lambda:laws.replay(item,forged))
        correct=laws.assess(item,item,resource(before),resource(after),before_derivation=proof,after_derivation=proof)
        def bad_analyzer(_original_ast,config,bad_ast=bad_ast):
            return engine.infer_use(bad_ast,config)
        mutant=engine.assess_with_test_analyzer(item,item,resource(before),resource(after),infer_fn=bad_analyzer)
        old=oracle.observations(oracle.execute(row['ast'],before,row['compile_config']))
        new=oracle.observations(oracle.execute(row['ast'],after,row['compile_config']))
        bad_old=oracle.observations(oracle.execute(bad_ast,before,row['compile_config']))
        bad_new=oracle.observations(oracle.execute(bad_ast,after,row['compile_config']))
        changed=changed_execution(old,new)
        witness=[side for side,actual,bad in (('before',old,bad_old),('after',new,bad_new)) if encoded(actual)!=encoded(bad)]
        killed=(correct.decision!='EXCLUDED' and mutant.decision=='EXCLUDED'
                and mutant.basis=='TEST_ONLY_UNTRUSTED' and old['complete'] and new['complete']
                and bool(changed) and bool(witness) and bad_old['complete'] and bad_new['complete']
                and encoded(bad_old)==encoded(bad_new))
        results.append({'id':identifier,'program_ref':ref,'fault':fault,'before_resource':before,'after_resource':after,
                        'invalid_normalized_ast':bad_ast,'normal_kernel_rejection':rejection,
                        'correct_refined_assessment':dump(correct),'actual_mutant_assessment':dump(mutant),
                        'independent_original_before':old,'independent_original_after':new,
                        'independent_invalid_normalized_before':bad_old,'independent_invalid_normalized_after':bad_new,
                        'actual_changed_original_observations':changed,'rewrite_mismatch_witness_sides':witness,
                        'mutation_execution_is_test_only_untrusted':True,'killed':bool(killed)})
    return results


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default=str(PACKAGE_ROOT/'results/law-profile/report.json'))
    arguments=parser.parse_args()
    started=time.monotonic()
    base_fixtures=json.loads((PACKAGE_ROOT/'fixtures/programs.json').read_text(encoding='utf-8'))
    fixtures=json.loads((PACKAGE_ROOT/'fixtures/law-programs.json').read_text(encoding='utf-8'))
    base_report=json.loads((PACKAGE_ROOT/'results/observation-profile/report.json').read_text(encoding='utf-8'))
    initial_hashes=source_hashes(base_report)
    programs=program_registry(base_fixtures,fixtures)
    inherited=guarded(lambda:inherited_source_check(base_report))
    sections={
        'normalization_contracts':normalization_contract_checks(fixtures,programs),
        'manual_execution_cases':manual_checks(fixtures,programs),
        'proof_boundary_and_partial_cases':proof_boundary_checks(programs),
        'equivalent_edit_cases':equivalence_checks(fixtures,programs),
    }
    bounded=guarded(lambda:bounded_checks(programs,base_fixtures,base_report))
    mutants=guarded(lambda:mutation_checks(programs))
    final_hashes=source_hashes(base_report)
    case_rows=[row for section in sections.values() for row in section]
    success=(case_rows and all(row['status']=='PASS' for row in case_rows)
             and inherited['status']=='PASS' and bounded['status']=='PASS'
             and isinstance(mutants,list) and len(mutants)==3 and all(row['killed'] for row in mutants)
             and initial_hashes==final_hashes)
    counts={name:{'passed':sum(row['status']=='PASS' for row in rows),
                  'failed':sum(row['status']!='PASS' for row in rows)} for name,rows in sections.items()}
    report={
        'report_format':'bagaev-r03-finite-checked-law-profile/1','status':'PASS' if success else 'FAIL',
        'generated_utc':datetime.now(timezone.utc).isoformat(),'python_version':platform.python_version(),
        'elapsed_seconds':round(time.monotonic()-started,6),
        'bagaev_execution':False,'research_ast_execution':True,'hypothesis_tested':False,
        'machine_checked_universal_proof':False,'requirement_predicate_satisfaction_tested':False,
        'performance_benchmark_performed':False,'tasks_closed':[],
        'T08_status':'NOT_CLOSED','T09_status':'NOT_CLOSED',
        'source_sha256':final_hashes,'sources_unchanged_during_run':initial_hashes==final_hashes,
        'reproducible_command':'python -B experiments/law-profile/verify.py --output results/law-profile/report.json',
        'command_working_directory':'package root',
        'base_profile_revision':engine.PROFILE_REVISION,'law_catalog_revision':laws.CATALOG_REVISION,
        'law_catalog_sha256':laws.CATALOG_SHA256,'observation_domain':laws.OBSERVATION_DOMAIN,
        'analysis_only_normalization':True,'ordinary_code_revision_guards_retained':True,
        'equivalent_edit_api_scope':'Explicitly replay-verified common form, equal fixed semantic context, complete use, and fresh concrete resource observations; source revisions and requirement reviews remain distinct.',
        'oracle_independence':'Unmodified R02 oracle.py imports neither engine nor laws. Each interpreter is checked against authored manual expectations; exclusion soundness uses independent execution of original ASTs.',
        'inherited_R02':inherited,'case_counts':counts,'named_case_count':len(case_rows),
        **sections,'bounded_comparison':bounded,'mutants':mutants,
        'scope_limits':[
            'Only these fixed program/configuration fixtures and all ordered pairs of the finite resource domain are exhaustively checked.',
            'The four rewrite schemas and guards are trusted stated assumptions of the fixed research semantics, not laws discovered or universally proved by finite tests.',
            'The unchanged R02 oracle checks original and normalized whole-program outcomes and every intermediate approved step on this finite domain.',
            'An incomplete execution can expose a matching known trace prefix; it never establishes complete equivalence or justifies EXCLUDED.',
            'Comparison uses exactly the same original programs, configurations and resource pairs for R02 and refined analysis. Fewer RECHECK decisions are not a runtime or toolchain speedup measurement.',
            'Partial derivations are allowed only after replay; they may retain additional conservative dependencies.',
            'Ordinary assessment keeps source changes conservative; the separate equivalent-edit API requires a checked common form and never proves different forms inequivalent.',
            'Requirement metadata remains OPEN, REMOVAL_OPEN or UNCHANGED_UNASSESSED. Requirement satisfaction, source-sensitive contracts, and normative acceptance are not established.',
            'This is not parsing, compilation, execution or verification of existing bagaev, and it does not rerun or replace the product A/B/C experiment.',
            'No new project graph, persistence protocol, provider implementation, arbitrary code equivalence, unknown external effects, or universal completeness proof is supplied.',
        ],
    }
    output=Path(arguments.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'case_counts':counts,'named_case_count':len(case_rows),
                      'bounded_totals':bounded.get('totals'),'bounded_cohorts':bounded.get('cohorts'),
                      'false_refined_exclusions':bounded.get('false_refined_exclusions'),
                      'mutants_killed':sum(row['killed'] for row in mutants) if isinstance(mutants,list) else 0,
                      'sources_unchanged_during_run':report['sources_unchanged_during_run'],
                      'report':str(output)},ensure_ascii=False))
    return 0 if success else 1


if __name__=='__main__':
    sys.exit(main())
