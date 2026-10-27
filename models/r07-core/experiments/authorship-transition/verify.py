#!/usr/bin/env python3
"""Finite independent AUTH-TX-0.1 verification, with authored crash-cut cases.

The oracle uses plain whole-state values and imports no tested implementation.
Abstract cuts select deterministic model branches; no process or disk is killed.
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

import engine
import oracle


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_REF = 'fixtures/authorship-transition.json'
SOURCE_REFS = (
    'experiments/authorship-transition/engine.py',
    'experiments/authorship-transition/oracle.py',
    'experiments/authorship-transition/verify.py',
    'experiments/authorship-transition/API.md',
    'experiments/authorship-transition/README.md',
    FIXTURE_REF, 'data/authorship-fixtures.json',
)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def digest(value):
    return sha256(encoded(value).encode('utf-8')).hexdigest()


def equal(actual, expected, label=''):
    if encoded(actual) != encoded(expected):
        raise AssertionError(f'{label}: actual={actual!r}; expected={expected!r}')


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def model_state(raw):
    values = deepcopy(raw)
    constructors = {'articles': engine.Article, 'outbox': engine.Event,
                    'projections': engine.Projection, 'author_index': engine.AuthorIndexEntry,
                    'inbox': engine.InboxEntry, 'acknowledgements': engine.AckReceipt}
    for field, constructor in constructors.items():
        values[field] = tuple(constructor(**row) for row in values[field])
    values['command_receipts'] = tuple(engine.CommandReceipt(
        **{**row, 'request': engine.ReplaceAuthorship(**row['request'])})
        for row in values['command_receipts'])
    values['projection_receipts'] = tuple(engine.ProjectionReceipt(
        **{**row, 'event': engine.Event(**row['event'])})
        for row in values['projection_receipts'])
    return engine.DurableState(**values)


def initial_states(fixtures):
    row = fixtures['initial']
    expected = oracle.make_initial_state(row['store_id'], row['people'], row['articles'])
    actual = engine.make_initial_state(row['store_id'], row['people'],
                                       tuple(engine.Article(**item) for item in row['articles']))
    equal(engine.canonical(actual), expected, 'prepared D1')
    equal(expected['author_index'], row['expected_index'], 'authored D1 index')
    equal(oracle.status(expected), row['expected_status'], 'authored D1 status')
    return actual, expected


def resolve_action(template, fixtures, state):
    action = deepcopy(template)
    if 'request_ref' in action:
        action['request'] = deepcopy(fixtures['requests'][action.pop('request_ref')])
    if action['op'] in ('deliver', 'recover_event') and 'event' not in action:
        identifier = action.pop('event_id')
        event = oracle.find(state['outbox'], event_id=identifier)
        require(event is not None, 'Fixture references an absent source event: ' + identifier)
        action['event'] = deepcopy(event)
    return action


def model_step(state, action):
    op = action['op']
    options = {'expected_state_version': action.get('expected_state_version'),
               'cut': action.get('cut', 'none')}
    if op == 'replace':
        return engine.replace_authorship(state, engine.ReplaceAuthorship(**action['request']), **options)
    if op == 'deliver':
        return engine.deliver_event(state, engine.Event(**action['event']), **options)
    if op == 'ack':
        return engine.acknowledge_event(state, action['event_id'], **options)
    if op == 'recover_command':
        seen = engine.recover_command(state, engine.ReplaceAuthorship(**action['request']),
                                      available=action.get('available', True))
    elif op == 'recover_event':
        seen = engine.recover_event(state, engine.Event(**action['event']),
                                    available=action.get('available', True))
    else:
        raise AssertionError('Unknown fixture operation: ' + op)
    return engine.Transition(state, False, seen)


def views(state, raw):
    actual = {'transition_status': engine.canonical(engine.status(state)),
              'search': {person: list(engine.search(state, person)) for person in raw['people']}}
    expected = {'transition_status': oracle.status(raw),
                'search': {person: oracle.search(raw, person) for person in raw['people']}}
    equal(actual, expected, 'independent read views')
    return actual


def compared_step(state, raw, action):
    before_model = engine.canonical(state)
    before_oracle = deepcopy(raw)
    actual = model_step(state, action)
    expected = oracle.apply(raw, action)
    equal(engine.canonical(state), before_model, 'immutable implementation input')
    equal(raw, before_oracle, 'immutable oracle input')
    engine.validate_state(actual.state)
    actual_data = engine.canonical(actual)
    equal(actual_data, expected, 'whole durable state + observed reply + harness commit truth')
    query_views = views(actual.state, expected['state'])
    actual_data.update(query_views)
    return actual, expected, actual_data


def pointer(value, path):
    current = value
    for token in path.lstrip('/').split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current


def authored_assertions(result, expected):
    require(expected, 'Every authored step needs explicit expectations')
    for path, value in expected.items():
        equal(pointer(result, path), value, 'authored expectation ' + path)


def run_named(actions):
    rows = []
    for identifier, action in actions:
        try:
            rows.append({'id': identifier, 'status': 'PASS', 'details': action()})
        except Exception as error:
            rows.append({'id': identifier, 'status': 'FAIL', 'error': repr(error)})
    return rows


def manual_sequences(fixtures):
    initial_model, initial_raw = initial_states(fixtures)
    checkpoints = {'initial': deepcopy(initial_raw)}
    actions = []
    for scenario in fixtures['manual_sequences']:
        def run(scenario=scenario):
            state, raw = initial_model, deepcopy(initial_raw)
            rows = []
            for index, step in enumerate(scenario['steps'], 1):
                action = resolve_action(step['action'], fixtures, raw)
                before = digest(raw)
                actual, expected, result = compared_step(state, raw, action)
                authored_assertions(result, step['expected'])
                state, raw = actual.state, expected['state']
                if 'checkpoint' in step:
                    require(step['checkpoint'] not in checkpoints, 'Duplicate authored checkpoint')
                    checkpoints[step['checkpoint']] = deepcopy(raw)
                rows.append({'step': index, 'input_state_sha256': before, 'action': action,
                             'authored_expected': step['expected'], 'actual': result,
                             'independent_whole_state_match': True})
            return {'purpose': scenario['purpose'], 'steps': rows,
                    'step_count': len(rows), 'final_state_sha256': digest(raw)}
        actions.append((scenario['id'], run))
    return run_named(actions), checkpoints


def rejection(action, code):
    try:
        action()
    except engine.ModelError as error:
        equal(error.code, code, 'host/state diagnostic')
        return {'diagnostic': error.code, 'detail': error.detail}
    raise AssertionError('Invalid host input/state was accepted: ' + code)


def boundary_cases(fixtures, checkpoints):
    def delivery_orders():
        newer = checkpoints['newer_first_complete']; older = checkpoints['older_first_complete']
        for field in ('articles', 'projections', 'author_index'):
            equal(newer[field], older[field], 'limited convergence/' + field)
        equal(oracle.status(newer), oracle.status(older))
        require(newer['projection_receipts'] != older['projection_receipts'], 'Histories were falsely equated')
        late = oracle.projection_receipt(newer, 'ev_a_101_r2')
        early = oracle.projection_receipt(older, 'ev_a_101_r2')
        equal((late['status'], early['status']), ('SUPERSEDED', 'APPLIED'))
        return {'equal_projection_and_index': True, 'equal_complete_state': False,
                'late_v2_receipt': late, 'early_v2_receipt': early,
                'state_hashes': [digest(newer), digest(older)]}

    def exact_event():
        raw = checkpoints['canonical_after_replace']; state = model_state(raw)
        original = raw['outbox'][0]
        changes = {'event_id': 'ev_unknown', 'store_id': 'another_store',
                   'causation_id': 'different_command', 'causation_actor_id': 'u_boris',
                   'author_ids': ['p_alina', 'p_boris'], 'article_revision': 3,
                   'event_type': 'OtherEvent', 'schema_revision': 'other-schema'}
        rows = []
        for field, value in changes.items():
            event = {**deepcopy(original), field: value}
            action = {'op': 'deliver', 'event': event, 'cut': 'after_commit_before_reply'}
            actual, expected, _ = compared_step(state, raw, action)
            equal(expected['observation']['code'], 'EVENT_CORRUPTION')
            equal(expected['state'], raw, 'corrupt source event must leave all state unchanged')
            rows.append({'changed_field': field, 'observation': engine.canonical(actual.observation)})
        return {'corrupt_event_cases': rows}

    def revoked_acl():
        raw = deepcopy(checkpoints['canonical_after_replace'])
        raw['state_version'] += 1
        raw['articles'][0]['editor_ids'] = []
        state = model_state(raw); engine.validate_state(state)
        rows = []
        for op in ('replace', 'recover_command'):
            action = {'op': op, 'request': fixtures['requests']['update'], 'expected_state_version': 1}
            actual, expected, _ = compared_step(state, raw, action)
            equal(expected['observation']['code'], 'PERMISSION_DENIED')
            equal(expected['state'], raw)
            rows.append(engine.canonical(actual.observation))
        return {'prepared_external_acl_snapshot': True, 'acl_mutation_api_implemented': False,
                'historical_receipt_retained': raw['command_receipts'][0], 'observations': rows}

    def version_exhaustion():
        rows = []
        raw = deepcopy(checkpoints['initial']); raw['state_version'] = oracle.MAX_VERSION
        for key in ('noop', 'update'):
            _, expected, _ = compared_step(model_state(raw), raw,
                                           {'op': 'replace', 'request': fixtures['requests'][key]})
            equal(expected['observation']['code'], 'VERSION_EXHAUSTED')
            rows.append({'case': 'state/' + key, 'observation': expected['observation']})
        raw = deepcopy(checkpoints['initial'])
        raw['articles'][0]['article_revision'] = oracle.MAX_VERSION
        raw['projections'][0]['article_revision'] = oracle.MAX_VERSION
        for key, outcome in (('update', 'VERSION_EXHAUSTED'), ('noop', 'NOOP')):
            request = {**fixtures['requests'][key], 'expected_article_version': oracle.MAX_VERSION}
            _, expected, _ = compared_step(model_state(raw), raw, {'op': 'replace', 'request': request})
            equal(expected['observation']['code'], outcome)
            equal(expected['state']['articles'][0]['article_revision'], oracle.MAX_VERSION)
            rows.append({'case': 'article/' + key, 'observation': expected['observation']})
        return {'version_cases': rows}

    def immutable_inputs():
        authors = ['p_alina']; editors = ['u_editor']; people = ['p_alina', 'p_boris', 'p_vera']
        article = engine.Article('a_101', 1, authors, editors)
        articles = [article]
        state = engine.make_initial_state('store_authorship', people, articles)
        request_authors = ['p_boris', 'p_alina']
        request = engine.ReplaceAuthorship('immutable_request', 'u_editor', 'a_101', 1, request_authors)
        before = engine.canonical(state); before_request = engine.canonical(request)
        authors.append('p_boris'); editors.clear(); people.clear(); articles.clear(); request_authors.reverse()
        equal(engine.canonical(state), before, 'nested collection aliases leaked into state')
        equal(engine.canonical(request), before_request, 'nested request aliases leaked into command binding')
        result = engine.replace_authorship(state, request)
        equal(list(result.state.articles[0].author_ids), ['p_boris', 'p_alina'])
        return {'state_sha256': digest(before), 'frozen_request': before_request,
                'result_authors': list(result.state.articles[0].author_ids)}

    def typed_diagnostics():
        state = model_state(checkpoints['initial']); req = engine.ReplaceAuthorship(**fixtures['requests']['update'])
        rows = [rejection(lambda: engine.replace_authorship(state, req, cut='during_half_write'), 'UNSUPPORTED_CUT'),
                rejection(lambda: engine.replace_authorship(state, req, expected_state_version=True), 'INVALID_VERSION'),
                rejection(lambda: engine.Article('a', True, ['p_alina'], []), 'INVALID_VERSION'),
                rejection(lambda: engine.ReplaceAuthorship('\ud800', 'u_editor', 'a_101', 1, ['p_alina']),
                          'INVALID_UNICODE_SCALAR'),
                rejection(lambda: engine.search(state, 'p_missing'), 'UNKNOWN_PERSON'),
                rejection(lambda: replace(state, articles=(state.articles[0], state.articles[0])),
                          'DUPLICATE_RECORD_KEY')]
        return {'diagnostics': rows}

    def corrupt_snapshots():
        rows = []
        raw = deepcopy(checkpoints['canonical_after_replace'])
        raw['author_index'][0]['article_ids'] = []
        rows.append({'kind': 'index_projection_disagreement', **rejection(lambda: engine.validate_state(model_state(raw)), 'STATE_CORRUPTION')})
        raw = deepcopy(checkpoints['canonical_after_replace'])
        raw['command_receipts'][0]['request_binding'] = 'wrong_binding'
        rows.append({'kind': 'wrong_request_binding', **rejection(lambda: engine.validate_state(model_state(raw)), 'STATE_CORRUPTION')})
        raw = deepcopy(checkpoints['canonical_after_delivery']); raw['projection_receipts'] = []
        rows.append({'kind': 'inbox_without_receipt', **rejection(lambda: engine.validate_state(model_state(raw)), 'STATE_CORRUPTION')})
        raw = deepcopy(checkpoints['canonical_after_ack'])
        raw['acknowledgements'][0]['projection_receipt_binding'] = 'wrong_binding'
        rows.append({'kind': 'ack_wrong_outcome_binding', **rejection(lambda: engine.validate_state(model_state(raw)), 'STATE_CORRUPTION')})
        raw = deepcopy(checkpoints['initial']); raw['articles'][0]['article_revision'] = 2
        raw['projections'][0]['author_ids'] = ['p_missing']; raw['author_index'][0]['article_ids'] = []
        rows.append({'kind': 'stale_projection_unknown_person', **rejection(lambda: engine.validate_state(model_state(raw)), 'STATE_CORRUPTION')})
        return {'diagnostics': rows}

    def equal_version_projection():
        raw = deepcopy(checkpoints['canonical_after_replace'])
        raw['projections'][0] = {key: deepcopy(raw['articles'][0][key])
                                 for key in ('article_id', 'article_revision', 'author_ids')}
        raw['author_index'] = oracle.index_from(raw['people'], raw['projections'])
        actual, expected, _ = compared_step(model_state(raw), raw, {'op': 'deliver', 'event': raw['outbox'][0]})
        equal(expected['observation']['code'], 'ALREADY_CURRENT')
        row = {'already_current': engine.canonical(actual.observation)}
        raw = deepcopy(checkpoints['two_updates'])
        raw['projections'][0].update(article_revision=2, author_ids=['p_vera'])
        raw['author_index'] = oracle.index_from(raw['people'], raw['projections'])
        actual, expected, _ = compared_step(model_state(raw), raw, {'op': 'deliver', 'event': raw['outbox'][0]})
        equal(expected['observation']['code'], 'PROJECTION_VERSION_CONFLICT')
        row['conflicting_equal_version'] = engine.canonical(actual.observation)
        row['prepared_projection_inputs_not_rebuild_api'] = True
        return row

    def namespaces():
        raw = deepcopy(checkpoints['initial']); raw['articles'][0]['editor_ids'] = ['u_editor', 'u_second_editor']
        state = model_state(raw)
        first = deepcopy(fixtures['requests']['update']); first['actor_id'] = 'u_second_editor'
        result, expected, _ = compared_step(state, raw, {'op': 'replace', 'request': first})
        second = {**fixtures['requests']['update'], 'expected_article_version': 2, 'author_ids': ['p_vera']}
        result, expected, _ = compared_step(result.state, expected['state'], {'op': 'replace', 'request': second})
        equal(len(expected['state']['command_receipts']), 2)
        require({row['request']['actor_id'] for row in expected['state']['command_receipts']} ==
                {'u_editor', 'u_second_editor'}, 'Actor namespace collapsed')
        original_store = checkpoints['initial']['store_id']
        require(oracle.command_binding(original_store, second) != oracle.command_binding('another_store', second),
                'Store missing from exact request binding')
        return {'command_keys': [[row['request']['actor_id'], row['request']['command_id']]
                                 for row in expected['state']['command_receipts']],
                'article_revision': expected['state']['articles'][0]['article_revision'],
                'distinct_store_bindings': True}

    def capacities():
        long_id = 'a' * 256
        initial = engine.make_initial_state('store', ['p_alina', 'p_boris'],
                                             [engine.Article(long_id, 1, ['p_alina'], ['u_editor'])])
        request = engine.ReplaceAuthorship('cmd', 'u_editor', long_id, 1, ['p_boris'])
        result = engine.replace_authorship(initial, request)
        require(256 < len(result.state.outbox[0].event_id) <= 512, 'Derived event ID has wrong limit')
        raw = deepcopy(checkpoints['initial']); raw['state_version'] = 513
        for number in range(512):
            request = {**fixtures['requests']['noop'], 'command_id': 'capacity_' + str(number)}
            raw['command_receipts'].append({'store_id': raw['store_id'], 'request': request,
                'request_binding': oracle.command_binding(raw['store_id'], request), 'status': 'NOOP',
                'article_revision': 1, 'event_id': None, 'committed_state_version': number + 2})
        raw = oracle.sorted_state(raw); state = model_state(raw); engine.validate_state(state)
        before = engine.canonical(state)
        failure = rejection(lambda: engine.replace_authorship(state, engine.ReplaceAuthorship(**fixtures['requests']['noop'])),
                            'CAPACITY_LIMIT')
        equal(engine.canonical(state), before, 'Capacity failure must not discard retained receipts')
        return {'derived_event_id_length': len(result.state.outbox[0].event_id),
                'retained_receipts_at_limit': 512, 'overflow': failure}

    return run_named([
        ('B01_DELIVERY_ORDER_HISTORY', delivery_orders), ('B02_EXACT_SOURCE_EVENT_BINDING', exact_event),
        ('B03_CURRENT_ACL_BEFORE_REPLAY', revoked_acl), ('B04_DISTINCT_VERSION_EXHAUSTION', version_exhaustion),
        ('B05_DEEPLY_FROZEN_INPUTS', immutable_inputs), ('B06_TYPED_BOUNDARIES', typed_diagnostics),
        ('B07_CORRUPT_SNAPSHOTS', corrupt_snapshots), ('B08_EQUAL_PROJECTION_VERSION', equal_version_projection),
        ('B09_STORE_ACTOR_NAMESPACES', namespaces), ('B10_CAPACITY_AND_DERIVED_IDS', capacities),
    ])


def finite_matrix(fixtures, checkpoints):
    definition = fixtures['bounded_matrix']; state_ids = definition['state_checkpoints']
    states = [{'id': identifier, 'state': checkpoints[identifier]} for identifier in state_ids]
    require(len({digest(row['state']) for row in states}) == len(states), 'Duplicate bounded state')
    records = []; counts = Counter(); input_states = []
    for item in states:
        raw = item['state']; state = model_state(raw)
        actions = [('request:' + key, {'op': 'replace', 'request': fixtures['requests'][key]})
                   for key in definition['request_refs']]
        for event in raw['outbox']:
            actions.extend([('deliver:' + event['event_id'], {'op': 'deliver', 'event': event}),
                            ('ack:' + event['event_id'], {'op': 'ack', 'event_id': event['event_id']})])
        require(len({identifier for identifier, _ in actions}) == len(actions), 'Duplicate finite action')
        input_states.append({'id': item['id'], 'state_sha256': digest(raw), 'state': raw,
                             'action_ids': [identifier for identifier, _ in actions]})
        for identifier, base_action in actions:
            guards = (('default_current_input', None), ('explicit_current', raw['state_version']),
                      ('explicit_stale_current_plus_one', raw['state_version'] + 1))
            equal([name for name, _ in guards], definition['state_guards'])
            for guard_name, guard in guards:
                for cut in definition['cuts']:
                    action = {**deepcopy(base_action), 'expected_state_version': guard, 'cut': cut}
                    counts['attempts'] += 1
                    try:
                        actual, expected, _ = compared_step(state, raw, action)
                        value = engine.canonical(actual)
                        counts['whole_state_matches'] += 1
                        counts['actual_commits'] += bool(actual.actual_commit)
                        counts['replays'] += bool(actual.observation.replayed)
                        counts['caller_unknown'] += actual.observation.status == 'UNKNOWN'
                        counts['rejections'] += actual.observation.status == 'REJECTED'
                        if not actual.actual_commit:
                            equal(value['state'], raw, 'No-commit attempt changed durable state')
                        if actual.observation.status == 'UNKNOWN':
                            require(actual.observation.receipt is None and actual.observation.observed_state_version is None,
                                    'Harness commit truth leaked into lost reply')
                        records.append({'state_id': item['id'], 'action_id': identifier, 'phase': action['op'],
                                        'guard': guard_name, 'cut': cut, 'status': 'PASS',
                                        'actual_sha256': digest(value), 'oracle_sha256': digest(expected),
                                        'actual_commit': actual.actual_commit,
                                        'observation': engine.canonical(actual.observation)})
                    except Exception as error:
                        counts['mismatches'] += 1
                        records.append({'state_id': item['id'], 'action_id': identifier, 'phase': action['op'],
                                        'guard': guard_name, 'cut': cut, 'status': 'FAIL', 'error': repr(error)})
    counts['mismatches'] += 0
    expected_total = sum(len(row['action_ids']) for row in input_states) * len(definition['state_guards']) * len(definition['cuts'])
    equal(counts['attempts'], expected_total, 'Exact finite product')
    return {'status': 'PASS' if not counts['mismatches'] else 'FAIL', 'definition': definition,
            'state_count': len(states), 'base_action_count': sum(len(row['action_ids']) for row in input_states),
            'counts': dict(counts), 'by_phase': dict(Counter(row['phase'] for row in records)),
            'by_cut': dict(Counter(row['cut'] for row in records)),
            'input_states': input_states, 'attempts': records}


def bad_producer_after_article_commit(state, request):
    """Executed defect: write article before durable outbox+receipt, then stop."""
    old_receipt = next((row for row in state['command_receipts']
                        if (row['request']['actor_id'], row['request']['command_id']) ==
                        (request['actor_id'], request['command_id'])), None)
    if old_receipt is not None:
        return {'state': deepcopy(state), 'actual_commit': False,
                'observation': {'status': 'RESULT', 'code': old_receipt['status'], 'receipt': deepcopy(old_receipt),
                                'observed_state_version': state['state_version'], 'replayed': True}}
    article = next(row for row in state['articles'] if row['article_id'] == request['article_id'])
    if article['article_revision'] != request['expected_article_version']:
        return {'state': deepcopy(state), 'actual_commit': False,
                'observation': {'status': 'REJECTED', 'code': 'ARTICLE_CONFLICT', 'receipt': None,
                                'observed_state_version': state['state_version'], 'replayed': False}}
    broken = deepcopy(state); broken['state_version'] += 1
    article = next(row for row in broken['articles'] if row['article_id'] == request['article_id'])
    article['article_revision'] += 1; article['author_ids'] = list(request['author_ids'])
    return {'state': broken, 'actual_commit': True,
            'observation': {'status': 'UNKNOWN', 'code': 'REPLY_LOST', 'receipt': None,
                            'observed_state_version': None, 'replayed': False}}


def bad_inbox_before_projection(state, event):
    """Executed defect: mark completed inbox first, leaving projection stale."""
    previous = next((row for row in state['projection_receipts']
                     if row['handler_id'] == 'authorship-index' and row['event']['event_id'] == event['event_id']), None)
    if previous is not None:
        return {'state': deepcopy(state), 'actual_commit': False,
                'observation': {'status': 'RESULT', 'code': previous['status'], 'receipt': deepcopy(previous),
                                'observed_state_version': state['state_version'], 'replayed': True}}
    broken = deepcopy(state); broken['state_version'] += 1
    binding = digest({'binding': 'authorship-event/r05-v1', 'profile_revision': 'authorship-transition/r05-v1', 'event': event})
    receipt = {'store_id': state['store_id'], 'handler_id': 'authorship-index', 'event': deepcopy(event),
               'event_binding': binding, 'status': 'APPLIED', 'projected_article_revision': event['article_revision'],
               'committed_state_version': broken['state_version']}
    broken['inbox'].append({'handler_id': 'authorship-index', 'event_id': event['event_id'], 'event_binding': binding})
    broken['projection_receipts'].append(receipt)
    return {'state': broken, 'actual_commit': True,
            'observation': {'status': 'UNKNOWN', 'code': 'REPLY_LOST', 'receipt': None,
                            'observed_state_version': None, 'replayed': False}}


def bad_key_only_replay(state, request):
    """Executed defect: a matching identity is mistaken for equal intent."""
    receipt = next(row for row in state['command_receipts']
                   if (row['request']['actor_id'], row['request']['command_id']) ==
                   (request['actor_id'], request['command_id']))
    return {'state': deepcopy(state), 'actual_commit': False,
            'observation': {'status': 'RESULT', 'code': receipt['status'], 'receipt': deepcopy(receipt),
                            'observed_state_version': state['state_version'], 'replayed': True}}


def actual_mutants(fixtures, checkpoints):
    def producer():
        before = checkpoints['initial']; request = fixtures['requests']['update']
        actual = bad_producer_after_article_commit(before, request)
        expected = oracle.replace_authorship(before, request, cut='after_commit_before_reply')
        require(actual['state'] != expected['state'], 'Producer mutant was not distinguished')
        equal(actual['observation'], expected['observation'], 'Both callers must see the same lost reply')
        retried = bad_producer_after_article_commit(actual['state'], request)
        expected_retry = oracle.replace_authorship(expected['state'], request)
        equal(retried['observation']['code'], 'ARTICLE_CONFLICT')
        equal(expected_retry['observation']['code'], 'UPDATED')
        return {'mutant_executed': True, 'distinguished': True,
                'defect': 'Article committed without the same-boundary outbox and successful command receipt.',
                'expected': expected, 'actual': actual, 'expected_retry': expected_retry, 'actual_retry': retried,
                'distinguishing_fields': ['state.outbox', 'state.command_receipts', 'retry.observation']}

    def consumer():
        before = checkpoints['canonical_after_replace']; event = before['outbox'][0]
        actual = bad_inbox_before_projection(before, event)
        expected = oracle.deliver_event(before, event, cut='after_commit_before_reply')
        require(actual['state'] != expected['state'], 'Inbox mutant was not distinguished')
        equal(actual['observation'], expected['observation'])
        retried = bad_inbox_before_projection(actual['state'], event)
        expected_retry = oracle.deliver_event(expected['state'], event)
        equal(retried['observation'], expected_retry['observation'])
        require(retried['state']['author_index'] != expected_retry['state']['author_index'],
                'Duplicate unexpectedly repaired the stale projection')
        diagnostic = rejection(lambda: engine.validate_state(model_state(actual['state'])), 'STATE_CORRUPTION')
        return {'mutant_executed': True, 'distinguished': True,
                'defect': 'Inbox/receipt claims APPLIED before the matching projection and index were committed.',
                'expected': expected, 'actual': actual, 'expected_retry': expected_retry, 'actual_retry': retried,
                'implementation_state_validator': diagnostic,
                'distinguishing_fields': ['state.projections', 'state.author_index', 'retry.state.author_index']}

    def key_only():
        before = checkpoints['canonical_after_replace']; request = fixtures['requests']['same_key_other_payload']
        actual = bad_key_only_replay(before, request)
        expected = oracle.replace_authorship(before, request)
        equal(actual['state'], expected['state'])
        equal(actual['observation']['code'], 'UPDATED'); equal(expected['observation']['code'], 'IDEMPOTENCY_CONFLICT')
        require(actual['observation'] != expected['observation'], 'Key-only mutant was not distinguished')
        return {'mutant_executed': True, 'distinguished': True,
                'defect': 'Receipt identity reused for different ordered authors, without exact request comparison.',
                'expected': expected, 'actual': actual, 'distinguishing_fields': ['observation']}

    return run_named([('M01_SPLIT_PRODUCER_COMMIT', producer), ('M02_INBOX_WITHOUT_PROJECTION', consumer),
                      ('M03_KEY_ONLY_RECEIPT_REPLAY', key_only)])


def hashes():
    return {ref: sha256((ROOT / ref).read_bytes()).hexdigest() for ref in SOURCE_REFS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='results/authorship-transition/report.json')
    parser.add_argument('--named-only', action='store_true', help='Targeted development smoke; writes no report.')
    args = parser.parse_args()
    fixture = json.loads((ROOT / FIXTURE_REF).read_text(encoding='utf-8'))
    started = time.perf_counter()
    source_before = None if args.named_only else hashes()
    manual, checkpoints = manual_sequences(fixture)
    boundaries = boundary_cases(fixture, checkpoints)
    mutants = actual_mutants(fixture, checkpoints)
    named = manual + boundaries + mutants
    if args.named_only:
        for row in named:
            print(row['id'] + ': ' + row['status'] + (' ' + row.get('error', '') if row['status'] != 'PASS' else ''))
        print(json.dumps({'named_checks': len(named), 'passed': sum(row['status'] == 'PASS' for row in named)}, sort_keys=True))
        return 0 if all(row['status'] == 'PASS' for row in named) else 1
    matrix = finite_matrix(fixture, checkpoints)
    source_after = hashes(); stable = source_before == source_after
    passed = all(row['status'] == 'PASS' for row in named) and matrix['status'] == 'PASS' and stable
    report = {
        'format': 'r05-authorship-transition-report/1', 'profile': 'AUTH-TX-0.1',
        'status': 'PASS' if passed else 'FAIL', 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(), 'elapsed_seconds': round(time.perf_counter() - started, 6),
        'bagaev_execution': False, 'research_ast_execution': False,
        'abstract_transition_model_execution': True, 'abstract_durable_model': True,
        'real_durability_tested': False, 'real_storage_tested': False, 'database_integration_tested': False,
        'physical_crash_execution': False, 'concurrent_interleavings_tested': False, 'migration_executed': False,
        'hypothesis_tested': False, 'machine_checked_universal_proof': False,
        'requirements_satisfaction_tested': False, 'performance_benchmark_performed': False,
        'tasks_closed': [], 'T06_status': 'NOT_CLOSED', 'T07_status': 'NOT_CLOSED', 'T15_ABC_status': 'NOT_RUN',
        'scope': {
            'oracle': 'Independent plain-JSON whole-state transition interpreter; does not import engine.',
            'initial_boundary': 'Prepared D1 / ArticleV2; no migration or code activation.',
            'checked_observations': ['whole durable state', 'caller observation including retained receipts',
                                     'harness-only actual_commit', 'index search', 'projection freshness and pending ACK'],
            'atomic_boundaries': ['article + outbox + successful command receipt', 'projection + index + inbox + projection receipt',
                                  'producer acknowledgement receipt'],
            'crash_cuts': list(oracle.CUTS), 'event_payload': 'full ordered author snapshot',
            'delivery_order': 'monotone per-article revision; histories are not equated',
            'idempotency': 'retained exact successful receipt, checked after current ACL and before stale guards',
            'finite_matrix': fixture['bounded_matrix']['bound_note'],
            'mutants': 'Three executed local defective transition fragments; not alternate complete storage implementations.',
            'legacy_fixture_execution': False,
            'limitations': ['No real disk, process crash, database adapter, concurrent CAS, or distributed acknowledgement.',
                            'No migration, schema activation, title/byline/export implementation, or A/B/C experiment.',
                            'Fixed people and ACL; prepared ACL/projection boundary inputs are not mutation APIs.',
                            'No receipt GC, retention policy, external authentication, or external exactly-once claim.',
                            'Finite supported-contract evidence does not close V1 criteria or establish a universal proof.']},
        'named_checks': {'manual_sequences': len(manual), 'manual_steps': sum(row['details']['step_count'] for row in manual if row['status'] == 'PASS'),
                         'boundary_cases': len(boundaries), 'actual_mutants': len(mutants), 'total': len(named),
                         'passed': sum(row['status'] == 'PASS' for row in named)},
        'manual_sequences': manual, 'boundary_cases': boundaries, 'bounded_crash_matrix': matrix,
        'actual_mutants': mutants, 'mutants_distinguished': sum(row['status'] == 'PASS' and row['details']['distinguished'] for row in mutants),
        'source_sha256': source_before, 'source_bytes_unchanged_during_run': stable,
        'reproduce': 'python -B experiments/authorship-transition/verify.py --output results/authorship-transition/report.json',
    }
    destination = Path(args.output)
    if not destination.is_absolute():
        destination = ROOT / destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'named_checks': report['named_checks'],
                      'bounded_counts': matrix['counts'], 'mutants_distinguished': report['mutants_distinguished'],
                      'source_bytes_unchanged_during_run': stable, 'report': str(destination)}, sort_keys=True))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
