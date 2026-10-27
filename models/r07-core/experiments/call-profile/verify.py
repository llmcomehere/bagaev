#!/usr/bin/env python3
"""Finite independent verification of strict static calls in CALL-0.1.

The direct call oracle does not import this engine or use its expansion. The
second oracle is the unchanged R02 interpreter executing checked strict lets.
The resulting finite evidence is not a proof about an implemented language.
"""
from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
from itertools import permutations
import json
from pathlib import Path
import platform
import sys
import time

import engine
import oracle

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
OBS_ROOT = PACKAGE_ROOT / 'experiments/observation-profile'
_spec = importlib.util.spec_from_file_location('call_profile_frozen_obs_oracle', OBS_ROOT / 'oracle.py')
obs_oracle = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = obs_oracle
_spec.loader.exec_module(obs_oracle)
obs = engine.obs

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
    return obs.to_data(value)


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


def type_annotation(value):
    return {'tuple': [type_annotation(item) for item in value.args]} if value.name == 'tuple' else value.name


def functions(rows):
    return [engine.Function(stable_id=row['stable_id'],
                            params=tuple(engine.Param(item['name'], item['type']) for item in row['params']),
                            return_type=row['return_type'], body=row['body'], alias=row.get('alias', ''))
            for row in rows]


def program(row, identifier=None, **entry_overrides):
    values = {'stable_id': identifier or 'consumer:' + row['id'], 'program': row['entry'],
              'compile_config': row.get('compile_config', {})}
    values.update(entry_overrides)
    return engine.Program(entry=engine.Consumer(**values), registry=engine.Registry(functions(row['functions'])))


def direct(row, spec):
    return oracle.observations(oracle.execute(row['entry'], row['functions'], spec,
                                              row.get('compile_config', {})))


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
    require(len({encoded(row['value']) for row in rows}) == len(rows), 'Duplicate finite resource state')
    return rows


def run_cases(actions):
    results = []
    for identifier, action in actions:
        try:
            results.append({'id': identifier, 'status': 'PASS', 'details': action()})
        except Exception as error:
            results.append({'id': identifier, 'status': 'FAIL', 'error': repr(error)})
    return results


def rejects(action, expected=None):
    try:
        action()
    except (engine.CallError, obs.ProfileError, engine.laws.LawError) as error:
        if expected is not None:
            allowed = {expected} if isinstance(expected, str) else set(expected)
            require(error.code in allowed, f'wrong diagnostic {error.code!r}, expected {allowed!r}')
        return {'diagnostic': error.code, 'exception': type(error).__name__}
    raise AssertionError('The invalid input or stale certificate was accepted')


def contract_checks(fixtures):
    actions = []
    for row in fixtures['programs']:
        def check(row=row):
            item = program(row)
            analysis = engine.analyze(item)
            equal(type_annotation(analysis.result_type), row['expected_type'], 'authored result type')
            equal(sorted(analysis.use.required_observations), row['expected_required_observations'],
                  'authored composed observations')
            equal(analysis.use.complete, row['expected_complete'], 'authored static completeness')
            equal(type_annotation(engine.validate_program(item)), row['expected_type'])
            details = {'analysis': dump(analysis), 'expected_type': row['expected_type']}
            if analysis.use.complete:
                expansion = engine.expand(item)
                verified = engine.verify_expansion(item, expansion)
                refined = engine.refined_bridge_use(item, expansion=expansion)
                same = engine.expand(item)
                equal(dump(expansion), dump(same), 'deterministic hygienic expansion')
                expanded_use = obs.infer_use(expansion.expanded_ast, item.entry.compile_config)
                for field in ('required_observations', 'complete', 'may_errors', 'effects', 'config_keys'):
                    equal(dump(getattr(analysis.use, field)), dump(getattr(expanded_use, field)),
                          'modular composition versus strict-let summary/' + field)
                equal(type_annotation(obs.validate_program(expansion.expanded_ast, item.entry.compile_config)),
                      row['expected_type'], 'expanded whole-tree type')
                equal(dump(verified.summary), dump(expanded_use))
                details.update({'expansion': dump(expansion), 'refined_summary': dump(refined.summary),
                                'saturated': refined.saturated, 'composition_matches_checked_expansion': True})
            else:
                details['bridge_rejection'] = rejects(lambda: engine.expand(item), 'BRIDGE_UNSUPPORTED')
            return details
        actions.append((row['id'], check))
    return run_cases(actions)


def manual_checks(fixtures, programs):
    actions = []
    for case in fixtures['manual_cases']:
        def check(case=case):
            row = programs[case['program']]
            item = program(row)
            analysis = engine.analyze(item)
            expansion = engine.expand(item) if analysis.use.complete else None
            if expansion is not None:
                engine.verify_expansion(item, expansion)
            outcomes = []
            for side in ('before', 'after'):
                expected = case['expected_' + side]
                actual = direct(row, case[side])
                equal(actual, expected, 'authored independent call outcome/' + side)
                equal(engine_observations(engine.execute(item, resource(case[side]))), expected,
                      'authored engine call outcome/' + side)
                if expansion is not None:
                    equal(obs_oracle.observations(obs_oracle.execute(plain(expansion.expanded_ast),
                                                                   case[side], row['compile_config'])),
                          expected, 'authored independent strict-let outcome/' + side)
                    equal(engine_observations(obs.execute(expansion.expanded_ast, resource(case[side]),
                                                          row['compile_config'])), expected,
                          'authored frozen-engine strict-let outcome/' + side)
                outcomes.append(actual)
            assessment = engine.assess(item, item, resource(case['before']), resource(case['after']))
            equal(assessment.decision, case['expected_decision'], 'authored baseline decision')
            require_exclusion_sound(assessment, *outcomes, case['id'])
            return {'program': case['program'], 'purpose': case['purpose'],
                    'assessment': dump(assessment), 'executed_before': outcomes[0],
                    'executed_after': outcomes[1], 'checked_strict_let_execution': expansion is not None,
                    'actual_changed_execution_observations': changed_execution(*outcomes)}
        actions.append((case['id'], check))
    return run_cases(actions)


def bounded_checks(fixtures):
    resources = finite_resources(fixtures['domain'])
    resource_values = [resource(row['value']) for row in resources]
    total = Counter()
    results = []
    for row in fixtures['programs']:
        item = program(row)
        analysis = engine.analyze(item)
        expansion = engine.expand(item) if analysis.use.complete else None
        refined = engine.refined_bridge_use(item, expansion=expansion) if expansion is not None else None
        if expansion is not None:
            engine.verify_expansion(item, expansion)
        outcomes = []
        counts = Counter()
        for state, value in zip(resources, resource_values):
            actual = direct(row, state['value'])
            equal(engine_observations(engine.execute(item, value)), actual, 'direct engine/oracle/' + row['id'])
            counts['direct_call_executions_per_interpreter'] += 1
            counts['complete_resource_outcomes' if actual['complete'] else 'incomplete_resource_outcomes'] += 1
            if expansion is not None:
                lowered_oracle = obs_oracle.observations(obs_oracle.execute(plain(expansion.expanded_ast),
                                                                          state['value'], row['compile_config']))
                equal(lowered_oracle, actual, 'independent call versus strict-let oracle/' + row['id'])
                equal(engine_observations(obs.execute(expansion.expanded_ast, value, row['compile_config'])),
                      actual, 'frozen engine strict-let execution/' + row['id'])
                refined_oracle = obs_oracle.observations(obs_oracle.execute(plain(refined.derivation.normalized_ast),
                                                                          state['value'], row['compile_config']))
                equal(refined_oracle, actual, 'independent refined strict-let oracle/' + row['id'])
                counts['strict_let_executions_per_interpreter'] += 1
                counts['refined_strict_let_oracle_executions'] += 1
            outcomes.append(actual)
        transitions = Counter()
        patterns = Counter()
        exclusions = []
        new_exclusions = []
        for i, left in enumerate(resources):
            for j, right in enumerate(resources):
                base = engine.assess(item, item, resource_values[i], resource_values[j])
                narrowed = engine.assess_refined(item, item, resource_values[i], resource_values[j])
                pair_id = left['id'] + ' -> ' + right['id']
                for label, decision in (('baseline', base), ('refined', narrowed)):
                    require_exclusion_sound(decision, outcomes[i], outcomes[j], row['id'] + '/' + label + '/' + pair_id)
                    counts[label + '_' + decision.decision] += 1
                changed = changed_execution(outcomes[i], outcomes[j])
                patterns[(tuple(changed), base.decision, narrowed.decision)] += 1
                transitions[(base.decision, narrowed.decision)] += 1
                counts['assessment_pairs'] += 1
                if changed:
                    counts['pairs_with_actual_changed_outcome'] += 1
                if base.decision == 'RECHECK' and not changed:
                    counts['baseline_conservative_rechecks'] += 1
                if narrowed.decision == 'RECHECK' and not changed:
                    counts['refined_conservative_rechecks'] += 1
                if narrowed.decision == 'EXCLUDED':
                    exclusions.append(pair_id)
                    if base.decision != 'EXCLUDED':
                        new_exclusions.append(pair_id)
                if base.decision == 'EXCLUDED':
                    equal(narrowed.decision, 'EXCLUDED', 'refinement lost a sound baseline exclusion')
        counts['newly_excluded_pairs'] = len(new_exclusions)
        counts['false_exclusions'] = 0
        counts['execution_mismatches'] = 0
        total.update(counts)
        results.append({'program': row['id'], 'baseline_summary': dump(analysis.use),
                        'refined_summary': dump(refined.summary) if refined is not None else None,
                        'bridge_supported': expansion is not None, 'counts': dict(counts),
                        'decision_transitions': [{'baseline': a, 'refined': b, 'count': n}
                                                 for (a, b), n in sorted(transitions.items())],
                        'actual_outcome_patterns': [{'changed_observations': list(changed),
                                                    'baseline': a, 'refined': b, 'count': n}
                                                   for (changed, a, b), n in sorted(patterns.items())],
                        'refined_excluded_pair_ids': exclusions,
                        'newly_excluded_pair_ids': new_exclusions})
    return {'status': 'PASS', 'domain': fixtures['domain'], 'resource_states': resources,
            'program_cases': len(fixtures['programs']), 'resource_state_count': len(resources),
            'ordered_resource_pairs_per_program': len(resources) ** 2,
            'counts': dict(total), 'program_results': results,
            'same_program_config_resource_corpus_for_both_analyses': True,
            'universal_proof': False, 'performance_benchmark': False}


def constant(value):
    return {'op': 'const', 'value': value}


def call_node(target, arguments=(), result='int'):
    return {'op': 'call', 'target': target, 'args': list(arguments), 'type': result}


def function_row(identifier, body, params=(), result='int'):
    return {'stable_id': identifier, 'params': [{'name': name, 'type': kind} for name, kind in params],
            'return_type': result, 'body': body}


def row_for(identifier, entry, declarations=(), config=None):
    return {'id': identifier, 'entry': entry, 'functions': list(declarations),
            'compile_config': dict(config or {})}


def clone(value):
    return json.loads(encoded(value))


def outcome(value=None, error=None, trace=(), unknown=False):
    return {'status': 'unknown' if unknown else 'error' if error else 'ok',
            'value': None if unknown or error else value, 'error': error,
            'trace': list(trace), 'complete': not unknown}


def revision_and_unknown_checks(programs):
    actions = []
    data = {'members': ['a', 'b']}
    old_row = programs['C12_transitive_size']

    def transitive_revision():
        new_row = clone(old_row)
        new_row['functions'][-1]['body'] = constant(0)
        before, after = program(old_row), program(new_row)
        old_analysis, new_analysis = engine.analyze(before), engine.analyze(after)
        equal(before.entry.program_revision, after.entry.program_revision)
        require(old_analysis.closure_stamp != new_analysis.closure_stamp, 'Leaf edit did not invalidate closure')
        require(old_analysis.semantic_stamp != new_analysis.semantic_stamp, 'Leaf edit did not invalidate semantic input')
        result = engine.assess(before, after, resource(data), resource(data))
        equal(result.decision, 'RECHECK')
        equal(direct(old_row, data), outcome(2))
        equal(direct(new_row, data), outcome(0))
        return {'same_entry_revision': True, 'before_closure': dump(old_analysis.closure),
                'after_closure': dump(new_analysis.closure), 'assessment': dump(result),
                'executed_before': direct(old_row, data), 'executed_after': direct(new_row, data)}
    actions.append(('R01_transitive_leaf_revision', transitive_revision))

    def unrelated_and_alias():
        base_row = programs['C01_nested_same_target']
        unrelated = clone(base_row)
        unrelated['functions'].append(function_row('unused', constant(42)))
        a, b = program(base_row), program(unrelated)
        aa, bb = engine.analyze(a), engine.analyze(b)
        require(aa.registry_stamp != bb.registry_stamp, 'Whole registry provenance did not change')
        equal(aa.semantic_stamp, bb.semantic_stamp, 'Unrelated valid definition changed the entry closure')
        equal(engine.assess(a, b, resource(data), resource(data)).decision, 'EXCLUDED')
        aliased = clone(base_row)
        aliased['functions'][0]['alias'] = 'display-only name'
        c = program(aliased, alias='consumer display')
        equal(engine.analyze(c).semantic_stamp, aa.semantic_stamp)
        equal(engine.assess(a, c, resource(data), resource(data)).decision, 'EXCLUDED')
        return {'unrelated_registry_changed': True, 'entry_semantics_preserved': True,
                'alias_metadata_does_not_change_function_or_entry_semantics': True}
    actions.append(('R02_unrelated_and_alias_metadata', unrelated_and_alias))

    def missing_transitions():
        missing = row_for('missing', call_node('later'))
        present = row_for('missing', call_node('later'), [function_row('later', constant(7))])
        a, b = program(missing), program(present)
        left, right = engine.analyze(a), engine.analyze(b)
        require(left.semantic_stamp != right.semantic_stamp, 'Resolving a lookup miss retained the old semantic stamp')
        equal([(x.target_id, x.state) for x in left.closure], [('later', 'MISSING')])
        equal([(x.target_id, x.state) for x in right.closure], [('later', 'PRESENT')])
        results = [engine.assess(a, b, resource(data), resource(data)),
                   engine.assess(b, a, resource(data), resource(data))]
        require(all(x.decision != 'EXCLUDED' for x in results), 'Missing/present transition was excluded')
        equal(direct(missing, data), outcome(unknown=True))
        equal(direct(present, data), outcome(7))
        return {'add_definition': dump(results[0]), 'delete_definition': dump(results[1]),
                'lookup_before': dump(left.closure), 'lookup_after': dump(right.closure)}
    actions.append(('R03_negative_lookup_resolution_and_deletion', missing_transitions))

    def metadata_revisions():
        item = program(old_row, requirements={'result': 'r1'})
        changes = {
            'entry': program(old_row, program=constant(2), requirements={'result': 'r1'}),
            'config': program(old_row, compile_config={'unused_key': True}, requirements={'result': 'r1'}),
            'new_requirement': program(old_row, requirements={'result': 'r1', 'new': 'r1'}),
            'changed_requirement': program(old_row, requirements={'result': 'r2'}),
            'removed_requirement': program(old_row, requirements={}),
        }
        results = {}
        for label, changed in changes.items():
            result = engine.assess(item, changed, resource(data), resource(data))
            equal(result.decision, 'RECHECK', label)
            results[label] = dump(result)
        statuses = {x.requirement_id: x.status for x in engine.assess(item, changes['new_requirement'],
                                                                                    resource(data), resource(data)).requirements}
        equal(statuses, {'result': 'UNCHANGED_UNASSESSED', 'new': 'OPEN'})
        removed = engine.assess(item, changes['removed_requirement'], resource(data), resource(data))
        equal({x.requirement_id: x.status for x in removed.requirements}, {'result': 'REMOVAL_OPEN'})
        return {'assessments': results, 'requirements_satisfaction_tested': False}
    actions.append(('R04_entry_config_and_requirements_revisions', metadata_revisions))

    def unsupported_provider():
        item = program(programs['C07_left_to_right_effects'], provider_revision='provider/v2')
        analysis = engine.analyze(item)
        require(analysis.use.complete is False, 'Unknown provider marked complete')
        result = engine.execute(item, resource(data))
        equal(engine_observations(result), outcome(unknown=True), 'Unsupported provider must run no body effects')
        equal(engine.assess(item, item, resource(data), resource(data)).decision, 'UNKNOWN')
        equal(engine.assess_refined(item, item, resource(data), resource(data)).decision, 'UNKNOWN')
        return {'analysis': dump(analysis), 'execution': dump(result),
                'bridge': rejects(lambda: engine.expand(item), 'BRIDGE_UNSUPPORTED')}
    actions.append(('R05_same_unsupported_provider_is_unknown', unsupported_provider))

    prefix = {'label': 'arg', 'value': 1}
    emitting_argument = {'op': 'emit', 'label': 'arg', 'value': constant(1), 'then': constant(1)}
    missing = row_for('missing_execution', call_node('absent', [emitting_argument]))
    missing_error = row_for('missing_error', call_node('absent', [
        {'op': 'emit', 'label': 'arg', 'value': constant(1),
         'then': {'op': 'fail', 'code': 'BEFORE_LOOKUP', 'type': 'int'}}]))
    unreachable = row_for('unreachable_missing', {'op': 'if', 'condition': constant(True),
                                                  'then': constant(7), 'else': call_node('absent')})
    external = row_for('external_execution', call_node('external', [emitting_argument]),
                       [function_row('external', None, [('x', 'int')])])
    self_cycle = row_for('self_cycle', call_node('f'), [function_row('f', call_node('f'))])
    mutual_cycle = row_for('mutual_cycle', call_node('f'),
                           [function_row('f', call_node('g')), function_row('g', call_node('f'))])
    cycle_argument_error = row_for('cycle_arg_error', call_node('f', [constant(0)]), [
        function_row('f', call_node('f', [{'op': 'fail', 'code': 'RECURSIVE_ARGUMENT', 'type': 'int'}]), [('x', 'int')])])
    cycle_with_other_lookup = row_for('cycle_other_lookup', call_node('f'), [function_row('f',
        {'op': 'seq', 'items': [call_node('f'), call_node('tail_missing')]})])
    unknown_cases = [
        ('R06_missing_after_strict_argument', missing, outcome(trace=[prefix], unknown=True), 'MISSING_CALLEE:absent'),
        ('R07_error_precedes_missing_lookup', missing_error, outcome(error='BEFORE_LOOKUP', trace=[prefix]), None),
        ('R08_unreachable_missing_keeps_static_gap', unreachable, outcome(7), None),
        ('R09_external_after_strict_argument', external, outcome(trace=[prefix], unknown=True), 'EXTERNAL_CALLEE:external'),
        ('R10_direct_cycle_guard', self_cycle, outcome(unknown=True), 'CALL_CYCLE:f'),
        ('R11_mutual_cycle_guard', mutual_cycle, outcome(unknown=True), 'CALL_CYCLE:f'),
        ('R12_recursive_argument_error_precedes_guard', cycle_argument_error, outcome(error='RECURSIVE_ARGUMENT'), None),
        ('R13_cycle_does_not_truncate_closure', cycle_with_other_lookup, outcome(unknown=True), 'CALL_CYCLE:f'),
    ]
    for identifier, row, expected, reason in unknown_cases:
        def check(row=row, expected=expected, reason=reason):
            item = program(row)
            analysis = engine.analyze(item)
            equal(analysis.use.complete, False)
            actual = engine.execute(item, resource(data))
            equal(engine_observations(actual), expected, 'authored unsupported-boundary runtime outcome')
            equal(direct(row, data), expected, 'independent unsupported-boundary runtime outcome')
            if reason is not None:
                equal(actual.unknown_reason, reason)
            equal(engine.assess(item, item, resource(data), resource(data)).decision, 'UNKNOWN')
            if row['id'] == 'cycle_other_lookup':
                equal({x.target_id for x in analysis.closure}, {'f', 'tail_missing'}, 'Complete finite lookup closure')
            return {'analysis': dump(analysis), 'execution': dump(actual),
                    'bridge': rejects(lambda: engine.expand(item), 'BRIDGE_UNSUPPORTED')}
        actions.append((identifier, check))
    return run_cases(actions)


def type_and_expansion_boundary_checks(programs):
    actions = []
    identity = function_row('identity', {'op': 'var', 'name': 'x'}, [('x', 'int')])
    invalid_rows = [
        ('B01_wrong_arity', row_for('bad_arity', call_node('identity'), [identity]), 'CALL_ARITY_MISMATCH'),
        ('B02_wrong_argument_type', row_for('bad_argument', call_node('identity', [constant(True)]), [identity]),
         'CALL_ARGUMENT_TYPE_MISMATCH'),
        ('B03_wrong_call_result_annotation', row_for('bad_result', call_node('identity', [constant(1)], 'string'), [identity]),
         'CALL_RESULT_TYPE_MISMATCH'),
        ('B04_wrong_function_return', row_for('bad_function', call_node('f'), [function_row('f', constant(True))]),
         'FUNCTION_RETURN_TYPE_MISMATCH'),
        ('B05_duplicate_parameter', row_for('duplicate_parameter', constant(0),
         [function_row('f', constant(0), [('x', 'int'), ('x', 'int')])]), 'DUPLICATE_PARAMETER'),
        ('B06_free_callee_name', row_for('free_name', {'op': 'let', 'name': 'x', 'value': constant(1), 'body': call_node('f')},
         [function_row('f', {'op': 'var', 'name': 'x'})]), 'UNBOUND_VARIABLE'),
        ('B07_invalid_unreferenced_body', row_for('invalid_unrelated', constant(0),
         [function_row('unused', constant(True))]), 'FUNCTION_RETURN_TYPE_MISMATCH'),
        ('B08_missing_call_annotation', row_for('untyped_missing', {'op': 'call', 'target': 'missing', 'args': []}),
         'MISSING_AST_FIELD'),
        ('B09_duplicate_definition', row_for('duplicate_function', constant(0),
         [function_row('f', constant(0)), function_row('f', constant(1))]), 'DUPLICATE_FUNCTION_ID'),
    ]
    for identifier, row, diagnostic in invalid_rows:
        actions.append((identifier, lambda row=row, diagnostic=diagnostic:
                        rejects(lambda: engine.validate_program(program(row)), diagnostic)))

    def forged_ast():
        item = program(programs['C12_transitive_size'])
        cert = engine.expand(item)
        return rejects(lambda: engine.verify_expansion(item, replace(cert, expanded_ast=constant(999))),
                       'EXPANSION_AST_MISMATCH')
    actions.append(('B10_forged_expansion_ast', forged_ast))

    def forged_bindings():
        item = program(programs['C07_left_to_right_effects'])
        cert = engine.expand(item)
        require(bool(cert.bindings), 'Expected at least one expansion binding')
        binding = replace(cert.bindings[0], target_id='different_target')
        return rejects(lambda: engine.verify_expansion(item, replace(cert, bindings=(binding,) + cert.bindings[1:])),
                       'EXPANSION_BINDINGS_MISMATCH')
    actions.append(('B11_forged_expansion_bindings', forged_bindings))

    def forged_context():
        item = program(programs['C12_transitive_size'])
        cert = engine.expand(item)
        checks = {}
        for field in ('entry_stamp', 'registry_stamp', 'closure_stamp', 'profile_revision',
                      'obs_sha256', 'laws_sha256', 'call_engine_sha256'):
            changed = replace(cert, context=replace(cert.context, **{field: 'forged:' + field}))
            checks[field] = rejects(lambda changed=changed: engine.verify_expansion(item, changed),
                                    'EXPANSION_CONTEXT_MISMATCH')
        return {'context_fields_rejected': checks}
    actions.append(('B12_forged_context_fields', forged_context))

    def stale_certificates():
        row = programs['C12_transitive_size']
        item = program(row)
        cert = engine.expand(item)
        leaf_changed = clone(row)
        leaf_changed['functions'][-1]['body'] = constant(2)
        unrelated = clone(row)
        unrelated['functions'].append(function_row('unrelated', constant(0)))
        changed_inputs = {
            'transitive_leaf': program(leaf_changed),
            'unrelated_registry_provenance': program(unrelated),
            'config': program(row, compile_config={'flag': True}),
            'requirements': program(row, requirements={'new': 'v1'}),
            'entry': program(row, program=constant(2)),
        }
        return {label: rejects(lambda changed=changed: engine.verify_expansion(changed, cert),
                               'EXPANSION_CONTEXT_MISMATCH') for label, changed in changed_inputs.items()}
    actions.append(('B13_stale_expansion_inputs', stale_certificates))

    def refinement_proof_boundary():
        item = program(programs['C12_transitive_size'])
        expansion = engine.expand(item)
        refined = engine.refined_bridge_use(item, expansion=expansion)
        equal(sorted(refined.summary.required_observations), ['count', 'read_status'])
        require(refined.saturated is True, 'Default R03 normalization was not saturated')
        require(any(step.rule_id == 'SIZE_ORDERED_TO_COUNT' for step in refined.derivation.steps),
                'Expected the checked local law exposed by expansion')
        bad = replace(refined.derivation, normalized_ast=constant(999))
        rejection = rejects(lambda: engine.refined_bridge_use(item, expansion=expansion, derivation=bad))
        pair_before, pair_after = resource({'members': ['a', 'b']}), resource({'members': ['b', 'a']})
        equal(engine.assess(item, item, pair_before, pair_after).decision, 'RECHECK')
        equal(engine.assess_refined(item, item, pair_before, pair_after).decision, 'EXCLUDED')
        changed_row = clone(programs['C12_transitive_size'])
        changed_row['functions'][-1]['body'] = {'op': 'read', 'view': 'count'}
        changed = program(changed_row)
        equal(engine.assess_refined(item, changed, pair_before, pair_after).decision, 'RECHECK',
              'Equivalent-looking callee edit must retain original revision guard')
        return {'refined_summary': dump(refined.summary), 'derivation': dump(refined.derivation),
                'forged_derivation_rejected': rejection, 'source_edit_equivalence_enabled': False}
    actions.append(('B14_refinement_and_original_revision_guard', refinement_proof_boundary))

    def exponential_expansion_budget():
        declarations = [function_row('f0', constant(0))]
        for index in range(1, 14):
            declarations.append(function_row('f' + str(index),
                {'op': 'seq', 'items': [call_node('f' + str(index - 1)), call_node('f' + str(index - 1))]}))
        item = program(row_for('expansion_budget', call_node('f13'), declarations))
        require(engine.analyze(item).use.complete is True, 'Small source DAG is otherwise supported')
        rejected = rejects(lambda: engine.expand(item), {'EXPANSION_NODE_LIMIT', 'EXPANSION_DEPTH_LIMIT'})
        return {'source_function_count': len(declarations), 'executed': False,
                'finite_preallocation_budget_rejection': rejected}
    actions.append(('B15_exponential_dag_expansion_budget', exponential_expansion_budget))

    def finite_call_depth_and_execution_budget():
        chain = [function_row('f0', constant(0))]
        for index in range(1, 33):
            chain.append(function_row('f' + str(index), call_node('f' + str(index - 1))))
        deep = program(row_for('static_depth', call_node('f32'), chain))
        depth_rejection = rejects(lambda: engine.analyze(deep), 'CALL_DEPTH_LIMIT')
        branching = [function_row('f0', constant(0))]
        for index in range(1, 16):
            branching.append(function_row('f' + str(index),
                {'op': 'seq', 'items': [call_node('f' + str(index - 1)), call_node('f' + str(index - 1))]}))
        costly = program(row_for('execution_budget', call_node('f15'), branching))
        require(engine.analyze(costly).use.complete is True, 'Small bounded-depth source DAG should analyze')
        execution_rejection = rejects(lambda: engine.execute(costly, resource({'members': []})), 'EXECUTION_STEP_LIMIT')
        return {'static_call_depth_rejection': depth_rejection, 'execution_work_rejection': execution_rejection,
                'rejections_are_not_complete_execution_outcomes': True,
                'outside_budget_outcomes_compared_for_equivalence': False}
    actions.append(('B16_explicit_call_depth_and_execution_limits', finite_call_depth_and_execution_budget))
    return run_cases(actions)


def project_checks():
    declarations = [function_row('count', {'op': 'read', 'view': 'count'}), function_row('zero', constant(0))]
    definitions_without_count = [function_row('zero', constant(0))]
    states = [
        {'id': 'P0_empty', 'functions': declarations, 'entries': {}, 'count_readers': [], 'complete': True},
        {'id': 'P1_nonconsumer', 'functions': declarations, 'entries': {'idle': constant(0)}, 'count_readers': [], 'complete': True},
        {'id': 'P2_new_consumer', 'functions': declarations, 'entries': {'idle': constant(0), 'reader': call_node('count')},
         'count_readers': ['reader'], 'complete': True},
        {'id': 'P3_mutated_nonconsumer', 'functions': declarations, 'entries': {'idle': call_node('count'), 'reader': call_node('zero')},
         'count_readers': ['idle'], 'complete': True},
        {'id': 'P4_deleted_definition', 'functions': definitions_without_count, 'entries': {'reader': call_node('count')},
         'count_readers': ['reader'], 'complete': False},
        {'id': 'P5_resolved_definition', 'functions': declarations, 'entries': {'reader': call_node('count')},
         'count_readers': ['reader'], 'complete': True},
    ]
    graphs = []
    for state in states:
        consumers = [engine.Consumer(identifier, entry, requirements={'visible-result': 'v1'})
                     for identifier, entry in state['entries'].items()]
        registry = engine.Registry(functions(state['functions']))
        graphs.append(engine.extract_project(registry, consumers))
    actions = []
    for state, graph in zip(states, graphs):
        def check(state=state, graph=graph):
            query = engine.reverse_query(graph, 'count')
            equal(list(query.items), state['count_readers'], 'authored reverse function query')
            equal(query.complete, state['complete'])
            fresh = engine.extract_project(graph.registry, reversed(graph.consumers))
            equal(fresh.manifest_stamp, graph.manifest_stamp, 'Input iteration order changed project identity')
            equal(dump(engine.reverse_query(fresh, 'count')), dump(query), 'Fresh rebuild disagrees with graph query')
            return {'query': dump(query), 'fresh_rebuild_query_matches': True,
                    'persistent_incremental_engine_exercised': False}
        actions.append((state['id'], check))

    def negative_query_premises():
        empty = engine.reverse_query(graphs[0], 'count')
        nonconsumer = engine.reverse_query(graphs[1], 'count')
        appeared = engine.reverse_query(graphs[2], 'count')
        equal(list(empty.items), [])
        equal(list(nonconsumer.items), [])
        require(empty.premise_stamp != nonconsumer.premise_stamp, 'Even an unchanged empty result lost membership provenance')
        require(nonconsumer.premise_stamp != appeared.premise_stamp, 'New consumer did not invalidate empty-query premise')
        equal(list(appeared.items), ['reader'])
        mutated = engine.reverse_query(graphs[3], 'count')
        equal(list(mutated.items), ['idle'])
        require(mutated.premise_stamp != appeared.premise_stamp, 'Mutated prior nonconsumer lost source-content provenance')
        return {'empty': dump(empty), 'empty_after_nonconsumer_added': dump(nonconsumer),
                'new_consumer': dump(appeared), 'mutated_nonconsumer': dump(mutated)}
    actions.append(('P6_empty_result_membership_and_content', negative_query_premises))

    def unknown_is_not_negative_proof():
        query = engine.reverse_query(graphs[4], 'authorship', kind='resource')
        require(query.complete is False, 'Missing callee promoted to a complete negative resource result')
        lookup = engine.reverse_query(graphs[4], 'count')
        equal(list(lookup.items), ['reader'])
        equal(lookup.complete, False)
        return {'resource_query': dump(query), 'retained_missing_function_edge': dump(lookup)}
    actions.append(('P7_missing_callee_retains_unknown_and_function_link', unknown_is_not_negative_proof))

    def forged_graph():
        bad = replace(graphs[2], analyses=())
        first = rejects(lambda: engine.reverse_query(bad, 'count'), 'PROJECT_GRAPH_MISMATCH')
        bad_stamp = replace(graphs[2], manifest_stamp='forged')
        second = rejects(lambda: engine.reverse_query(bad_stamp, 'count'), 'PROJECT_GRAPH_MISMATCH')
        return {'erased_analyses': first, 'forged_manifest': second}
    actions.append(('P8_saved_graph_is_revalidated', forged_graph))

    def all_state_transitions():
        before_resource, after_resource = {'members': ['a']}, {'members': ['a', 'b']}
        rows = []
        counts = Counter()
        for before_state, before in zip(states, graphs):
            for after_state, after in zip(states, graphs):
                assessments = engine.assess_project(before, after, resource(before_resource), resource(after_resource))
                union = set(before_state['entries']) | set(after_state['entries'])
                equal({item.consumer_id for item in assessments}, union, 'Old/new consumer union')
                for assessment in assessments:
                    identifier = assessment.consumer_id
                    counts[assessment.decision] += 1
                    if identifier not in after_state['entries']:
                        require(assessment.decision != 'EXCLUDED', 'Deleted consumer was excluded')
                        equal({item.status for item in assessment.requirements}, {'REMOVAL_OPEN'})
                    if assessment.decision == 'EXCLUDED':
                        require(identifier in before_state['entries'] and identifier in after_state['entries'],
                                'A nonexistent side was excluded')
                        old_row = row_for(identifier, before_state['entries'][identifier], before_state['functions'])
                        new_row = row_for(identifier, after_state['entries'][identifier], after_state['functions'])
                        require_exclusion_sound(assessment, direct(old_row, before_resource), direct(new_row, after_resource),
                                                before_state['id'] + ' -> ' + after_state['id'] + '/' + identifier)
                rows.append({'before': before_state['id'], 'after': after_state['id'],
                             'consumer_union': sorted(union), 'assessments': dump(assessments)})
        return {'project_states': len(states), 'ordered_state_transitions': len(rows),
                'consumer_assessments': sum(counts.values()), 'decisions': dict(counts),
                'false_exclusions': 0, 'transitions': rows,
                'resource_pair': {'before': before_resource, 'after': after_resource},
                'persistent_incremental_engine_exercised': False}
    actions.append(('P9_full_rebuild_old_new_union_transitions', all_state_transitions))
    return run_cases(actions)


def mutant_checks(programs):
    actions = []

    def drop_unused_strict_argument():
        row = programs['C04_unused_head']
        target = next(function for function in row['functions'] if function['stable_id'] == row['entry']['target'])
        # Actual deliberately bad rewrite: replace an unused-parameter call by
        # its constant body, dropping evaluation of every actual argument.
        require(target['body']['op'] == 'const', 'Mutation witness requires unused parameters')
        mutated = clone(target['body'])
        before, after = {'members': []}, {'members': ['a']}
        original = [direct(row, before), direct(row, after)]
        bad = [obs_oracle.observations(obs_oracle.execute(mutated, state)) for state in (before, after)]
        actual = program(row)
        correct = engine.assess(actual, actual, resource(before), resource(after))
        untrusted = obs.Consumer('mutant:unused', mutated)
        wrong = obs.assess(untrusted, untrusted, resource(before), resource(after))
        equal(correct.decision, 'RECHECK')
        equal(wrong.decision, 'EXCLUDED')
        require(bool(changed_execution(*original)), 'Mutation did not create an actual false exclusion')
        equal(bad[0], bad[1])
        require(original[0] != bad[0], 'Dropped strict error was not observed')
        return {'killed': True, 'test_only_untrusted': True, 'detection': 'FALSE_EXCLUSION',
                'mutated_ast': mutated, 'resource_before': before, 'resource_after': after,
                'correct_assessment': dump(correct), 'mutant_decision': wrong.decision,
                'original_before': original[0], 'original_after': original[1],
                'mutant_before': bad[0], 'mutant_after': bad[1],
                'actual_changed_original_observations': changed_execution(*original)}
    actions.append(('MUTANT_DROP_UNUSED_STRICT_ARGUMENT', drop_unused_strict_argument))

    def duplicate_effectful_substitution():
        row = programs['C03_repeated_parameter']
        target = row['functions'][0]
        substitution = {parameter['name']: argument for parameter, argument in zip(target['params'], row['entry']['args'])}
        def substitute(node):
            if isinstance(node, dict):
                if node.get('op') == 'var' and node['name'] in substitution:
                    return clone(substitution[node['name']])
                return {key: substitute(item) for key, item in node.items()}
            if isinstance(node, list):
                return [substitute(item) for item in node]
            return node
        # Actual deliberately bad call expansion: textual substitution copies
        # the effectful expression at each parameter occurrence, without lets.
        mutated = substitute(target['body'])
        witnesses = []
        for state in ({'members': ['a']}, {'members': ['a', 'b']}):
            correct = direct(row, state)
            bad = obs_oracle.observations(obs_oracle.execute(mutated, state))
            equal(correct['value'], bad['value'], 'Witness isolates effect multiplicity')
            equal(len(correct['trace']), 1)
            equal(len(bad['trace']), 2)
            require(changed_execution(correct, bad) == ['trace'], 'Expected exactly a trace violation')
            witnesses.append({'resource': state, 'original': correct, 'mutant': bad,
                              'actual_changed_observations': changed_execution(correct, bad)})
        return {'killed': True, 'test_only_untrusted': True, 'detection': 'EXPANSION_OUTCOME_MISMATCH',
                'mutated_ast': mutated, 'witnesses': witnesses,
                'false_exclusion_claimed_for_this_mutant': False}
    actions.append(('MUTANT_DUPLICATE_EFFECTFUL_ARGUMENT', duplicate_effectful_substitution))

    def stale_root_only_summary():
        base = clone(programs['C12_transitive_size'])
        base['functions'][-1]['body'] = constant(0)
        updated = clone(base)
        updated['functions'][-1]['body'] = {'op': 'read', 'view': 'count'}
        before_program, after_program = program(base), program(updated)
        before_analysis, after_analysis = engine.analyze(before_program), engine.analyze(after_program)
        # Actual deliberately bad cache: exact entry stamp but no lookup or
        # callee closure revision. The unchanged root therefore hits stale use.
        cache = {before_program.entry.input_stamp: before_analysis.use}
        key = after_program.entry.input_stamp
        require(key in cache, 'Mutation witness did not hit the stale cache')
        cached = cache[key]
        before, after = {'members': ['a']}, {'members': ['a', 'b']}
        changed = oracle.changed_observations(before, after)
        wrong_decision = 'EXCLUDED' if cached.complete and not (cached.required_observations & changed) else 'RECHECK'
        correct = engine.assess(before_program, after_program, resource(before), resource(after))
        actual_before, actual_after = direct(base, before), direct(updated, after)
        equal(wrong_decision, 'EXCLUDED')
        equal(correct.decision, 'RECHECK')
        require(before_analysis.semantic_stamp != after_analysis.semantic_stamp, 'Good closure gate did not change')
        require(bool(changed_execution(actual_before, actual_after)), 'Stale cache mutation did not change the actual outcome')
        return {'killed': True, 'test_only_untrusted': True, 'detection': 'FALSE_EXCLUSION',
                'cache_hit': True, 'cache_key_omits_callee_closure': True,
                'same_entry_stamp': before_program.entry.input_stamp == after_program.entry.input_stamp,
                'cached_summary': dump(cached), 'current_summary': dump(after_analysis.use),
                'resource_before': before, 'resource_after': after,
                'correct_assessment': dump(correct), 'mutant_decision': wrong_decision,
                'original_before': actual_before, 'original_after': actual_after,
                'actual_changed_original_observations': changed_execution(actual_before, actual_after)}
    actions.append(('MUTANT_ROOT_ONLY_CACHE_OMITS_TRANSITIVE_CALLEE', stale_root_only_summary))
    return run_cases(actions)


SOURCE_REFS = (
    'experiments/call-profile/engine.py',
    'experiments/call-profile/API.md',
    'experiments/call-profile/README.md',
    'experiments/call-profile/oracle.py',
    'experiments/call-profile/verify.py',
    'fixtures/call-programs.json',
    'experiments/observation-profile/engine.py',
    'experiments/observation-profile/oracle.py',
    'experiments/observation-profile/API.md',
    'fixtures/programs.json',
    'experiments/law-profile/laws.py',
    'experiments/law-profile/API.md',
)


def source_hashes():
    return {ref: sha256((PACKAGE_ROOT / ref).read_bytes()).hexdigest() for ref in SOURCE_REFS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='results/call-profile/report.json')
    args = parser.parse_args()
    started = time.perf_counter()
    hashes_before = source_hashes()
    fixtures = json.loads((PACKAGE_ROOT / 'fixtures/call-programs.json').read_text())
    base_fixtures = json.loads((PACKAGE_ROOT / 'fixtures/programs.json').read_text())
    equal(fixtures['domain'], base_fixtures['domain'], 'Unchanged finite resource domain')
    programs = {row['id']: row for row in fixtures['programs']}
    require(len(programs) == len(fixtures['programs']), 'Duplicate program ID')
    sections = {
        'composed_summary_contracts': contract_checks(fixtures),
        'manual_execution_cases': manual_checks(fixtures, programs),
        'revision_and_unknown_cases': revision_and_unknown_checks(programs),
        'type_and_expansion_boundary_cases': type_and_expansion_boundary_checks(programs),
        'project_rebuild_cases': project_checks(),
        'actual_mutants': mutant_checks(programs),
    }
    try:
        bounded = bounded_checks(fixtures)
    except Exception as error:
        bounded = {'status': 'FAIL', 'error': repr(error)}
    hashes_after = source_hashes()
    all_cases = [case for rows in sections.values() for case in rows]
    named_passed = sum(case['status'] == 'PASS' for case in all_cases)
    stable_sources = hashes_before == hashes_after
    passed = named_passed == len(all_cases) and bounded['status'] == 'PASS' and stable_sources
    report = {
        'format': 'r04-call-profile-report/1', 'status': 'PASS' if passed else 'FAIL',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'python_version': platform.python_version(), 'elapsed_seconds': round(time.perf_counter() - started, 6),
        'bagaev_execution': False, 'research_ast_execution': True, 'hypothesis_tested': False,
        'machine_checked_universal_proof': False, 'requirements_satisfaction_tested': False,
        'performance_benchmark_performed': False, 'persistent_incremental_engine_exercised': False,
        'tasks_closed': [], 'T08_status': 'NOT_CLOSED', 'T09_status': 'NOT_CLOSED',
        'source_sha256': hashes_after, 'source_bytes_unchanged_during_run': stable_sources,
        'scope': {
            'profile': 'CALL-0.1', 'language': 'separate finite Python research semantics',
            'direct_oracle_does_not_import_engine_or_expander': True,
            'manual_outcomes_are_authored': True,
            'supported_dag_checked_against_frozen_strict_let_execution': True,
            'observation_domain': list(EXECUTION_FIELDS),
            'static_union_is_conservative_not_minimal': True,
            'unknown_not_treated_as_equal_complete_outcome': True,
            'source_or_callee_edit_equivalence_enabled': False,
            'requirements': 'Revision/open-obligation metadata only; no predicate satisfaction.',
            'limits': 'Finite unique-author resources, 18 fixed entry/configuration cases; no full-language or arbitrary-code claim.',
        },
        'named_checks': {'total': len(all_cases), 'passed': named_passed,
                         'by_section': {name: {'total': len(rows), 'passed': sum(x['status'] == 'PASS' for x in rows)}
                                        for name, rows in sections.items()}},
        **sections, 'bounded_same_corpus': bounded,
        'mutants_distinguished': sum(x['status'] == 'PASS' and x.get('details', {}).get('killed') is True
                                     for x in sections['actual_mutants']),
        'interpretation': [
            'EXCLUDED is checked against independently executed complete outcomes, including errors and ordered traces.',
            'Direct CALL and checked strict-let execution are compared only for complete resolved DAG inputs.',
            'The law bridge uses frozen R03 checking and preserves original entry and callee revision gates.',
            'Project evidence covers full rebuild and old/new identity union; it is not an incremental speed measurement.',
            'Two mutants yield actual false exclusions; one yields unequal executed effect traces after an unsafe expansion.',
            'Finite tests do not establish a universal proof, normative acceptance, or language implementation readiness.',
        ],
    }
    output = Path(args.output)
    if not output.is_absolute():
        output = PACKAGE_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    summary = {'status': report['status'], 'named_checks': report['named_checks'],
               'bounded_counts': bounded.get('counts'), 'mutants_distinguished': report['mutants_distinguished'],
               'source_bytes_unchanged_during_run': stable_sources, 'report': str(output),
               'failures': [case for case in all_cases if case['status'] != 'PASS']}
    if bounded['status'] != 'PASS':
        summary['bounded_failure'] = bounded
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
