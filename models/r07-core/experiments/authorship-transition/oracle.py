"""Independent whole-state semantics for the finite AUTH-TX-0.1 experiment.

This module imports no implementation under test. Its input/output are ordinary
JSON values. It derives a complete committed snapshot first; an abstract cut
chooses old or complete-new state, independently of the caller observation.
It is not an implementation of physical durability or a second storage engine.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json


PROFILE = 'authorship-transition/r05-v1'
OPERATION = 'ReplaceAuthorship/v1'
HANDLER = 'authorship-index'
EVENT_TYPE = 'ArticleAuthorshipChanged'
EVENT_SCHEMA = 'AuthorshipEventV2'
MAX_VERSION = 2**63 - 1
CUTS = ('none', 'before_commit', 'after_commit_before_reply')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def digest(value):
    return sha256(canonical(value).encode('utf-8')).hexdigest()


def command_binding(store_id, request):
    return digest({'binding': 'authorship-command/r05-v1',
                   'profile_revision': PROFILE, 'operation_id': OPERATION,
                   'event_schema': EVENT_SCHEMA, 'store_id': store_id,
                   'request': request})


def event_binding(event):
    return digest({'binding': 'authorship-event/r05-v1',
                   'profile_revision': PROFILE, 'event': event})


def projection_receipt_binding(receipt):
    return digest({'binding': 'authorship-projection-receipt/r05-v1',
                   'profile_revision': PROFILE, 'receipt': receipt})


def index_from(people, projections):
    return [{'person_id': person,
             'article_ids': sorted(row['article_id'] for row in projections
                                   if person in row['author_ids'])}
            for person in sorted(people)]


def sorted_state(state):
    """Canonicalize identity collections, preserving semantic author order."""
    result = deepcopy(state)
    result['people'] = sorted(result['people'])
    for field in ('articles', 'projections'):
        result[field].sort(key=lambda row: row['article_id'])
    for row in result['articles']:
        row['editor_ids'] = sorted(row['editor_ids'])
    for field in ('outbox', 'acknowledgements'):
        result[field].sort(key=lambda row: row['event_id'])
    result['command_receipts'].sort(key=lambda row: (row['request']['actor_id'],
                                                    row['request']['command_id']))
    result['author_index'].sort(key=lambda row: row['person_id'])
    for row in result['author_index']:
        row['article_ids'] = sorted(row['article_ids'])
    result['inbox'].sort(key=lambda row: (row['handler_id'], row['event_id']))
    result['projection_receipts'].sort(key=lambda row: (row['handler_id'],
                                                       row['event']['event_id']))
    return result


def make_initial_state(store_id, people, articles):
    articles = deepcopy(articles)
    projections = [{key: row[key] for key in ('article_id', 'article_revision', 'author_ids')}
                   for row in articles]
    return sorted_state({'store_id': store_id, 'state_version': 1,
                         'people': list(people), 'articles': articles,
                         'outbox': [], 'command_receipts': [],
                         'projections': projections,
                         'author_index': index_from(people, projections),
                         'inbox': [], 'projection_receipts': [], 'acknowledgements': []})


def find(rows, **keys):
    return next((row for row in rows if all(row.get(key) == value
                                          for key, value in keys.items())), None)


def command_receipt(state, request):
    return next((row for row in state['command_receipts']
                 if row['request']['actor_id'] == request['actor_id']
                 and row['request']['command_id'] == request['command_id']), None)


def projection_receipt(state, event_id):
    return next((row for row in state['projection_receipts']
                 if row['handler_id'] == HANDLER and row['event']['event_id'] == event_id), None)


def observation(status, code, version=None, receipt=None, replayed=False):
    return {'status': status, 'code': code, 'receipt': deepcopy(receipt),
            'observed_state_version': version, 'replayed': replayed}


def rejected(state, code):
    return {'state': deepcopy(state), 'actual_commit': False,
            'observation': observation('REJECTED', code, state['state_version'])}


def replay(state, receipt, code):
    return {'state': deepcopy(state), 'actual_commit': False,
            'observation': observation('RESULT', code, state['state_version'], receipt, True)}


def commit(before, candidate, receipt, code, cut):
    if cut not in CUTS:
        raise ValueError('INVALID_CUT')
    if cut == 'before_commit':
        return {'state': deepcopy(before), 'actual_commit': False,
                'observation': observation('UNKNOWN', 'REPLY_LOST')}
    candidate = sorted_state(candidate)
    if cut == 'after_commit_before_reply':
        return {'state': candidate, 'actual_commit': True,
                'observation': observation('UNKNOWN', 'REPLY_LOST')}
    return {'state': candidate, 'actual_commit': True,
            'observation': observation('RESULT', code, candidate['state_version'], receipt)}


def acl_error(state, request):
    article = find(state['articles'], article_id=request['article_id'])
    if article is None:
        return 'UNKNOWN_ARTICLE'
    if request['actor_id'] not in article['editor_ids']:
        return 'PERMISSION_DENIED'
    return None


def stale_state(state, expected):
    return expected is not None and expected != state['state_version']


def replace_authorship(state, request, *, expected_state_version=None, cut='none'):
    error = acl_error(state, request)
    if error:
        return rejected(state, error)
    previous = command_receipt(state, request)
    if previous is not None:
        if canonical(previous['request']) != canonical(request):
            return rejected(state, 'IDEMPOTENCY_CONFLICT')
        return replay(state, previous, previous['status'])
    if stale_state(state, expected_state_version):
        return rejected(state, 'STATE_CONFLICT')
    authors = request['author_ids']
    if not authors:
        return rejected(state, 'EMPTY_AUTHORS')
    if len(set(authors)) != len(authors):
        return rejected(state, 'DUPLICATE_AUTHOR')
    if any(author not in state['people'] for author in authors):
        return rejected(state, 'UNKNOWN_PERSON')
    current = find(state['articles'], article_id=request['article_id'])
    if request['expected_article_version'] != current['article_revision']:
        return rejected(state, 'ARTICLE_CONFLICT')
    changed = authors != current['author_ids']
    if state['state_version'] == MAX_VERSION or (changed and current['article_revision'] == MAX_VERSION):
        return rejected(state, 'VERSION_EXHAUSTED')
    candidate = deepcopy(state)
    candidate['state_version'] += 1
    article = find(candidate['articles'], article_id=request['article_id'])
    event_id = None
    if changed:
        article['article_revision'] += 1
        article['author_ids'] = list(authors)
        event_id = 'ev_' + article['article_id'] + '_r' + str(article['article_revision'])
        candidate['outbox'].append({'event_id': event_id, 'store_id': state['store_id'],
                                    'causation_id': request['command_id'],
                                    'causation_actor_id': request['actor_id'],
                                    'article_id': article['article_id'],
                                    'article_revision': article['article_revision'],
                                    'author_ids': list(authors), 'event_type': EVENT_TYPE,
                                    'schema_revision': EVENT_SCHEMA})
    receipt = {'store_id': state['store_id'], 'request': deepcopy(request),
               'request_binding': command_binding(state['store_id'], request),
               'status': 'UPDATED' if changed else 'NOOP',
               'article_revision': article['article_revision'], 'event_id': event_id,
               'committed_state_version': candidate['state_version']}
    candidate['command_receipts'].append(receipt)
    return commit(state, candidate, receipt, receipt['status'], cut)


def trusted_event(state, event):
    source = find(state['outbox'], event_id=event['event_id'])
    return source is not None and canonical(source) == canonical(event)


def deliver_event(state, event, *, expected_state_version=None, cut='none'):
    if not trusted_event(state, event):
        return rejected(state, 'EVENT_CORRUPTION')
    previous = projection_receipt(state, event['event_id'])
    if previous is not None:
        return replay(state, previous, previous['status'])
    if stale_state(state, expected_state_version):
        return rejected(state, 'STATE_CONFLICT')
    projection = find(state['projections'], article_id=event['article_id'])
    if event['article_revision'] == projection['article_revision']:
        if event['author_ids'] != projection['author_ids']:
            return rejected(state, 'PROJECTION_VERSION_CONFLICT')
        outcome = 'ALREADY_CURRENT'
    elif event['article_revision'] < projection['article_revision']:
        outcome = 'SUPERSEDED'
    else:
        outcome = 'APPLIED'
    if state['state_version'] == MAX_VERSION:
        return rejected(state, 'VERSION_EXHAUSTED')
    candidate = deepcopy(state)
    candidate['state_version'] += 1
    if outcome == 'APPLIED':
        target = find(candidate['projections'], article_id=event['article_id'])
        target['article_revision'] = event['article_revision']
        target['author_ids'] = list(event['author_ids'])
        candidate['author_index'] = index_from(candidate['people'], candidate['projections'])
    projected = find(candidate['projections'], article_id=event['article_id'])
    binding = event_binding(event)
    receipt = {'store_id': state['store_id'], 'handler_id': HANDLER,
               'event': deepcopy(event), 'event_binding': binding,
               'status': outcome, 'projected_article_revision': projected['article_revision'],
               'committed_state_version': candidate['state_version']}
    candidate['inbox'].append({'handler_id': HANDLER, 'event_id': event['event_id'],
                                'event_binding': binding})
    candidate['projection_receipts'].append(receipt)
    return commit(state, candidate, receipt, outcome, cut)


def acknowledge_event(state, event_id, *, expected_state_version=None, cut='none'):
    event = find(state['outbox'], event_id=event_id)
    if event is None:
        return rejected(state, 'UNKNOWN_EVENT')
    previous = find(state['acknowledgements'], event_id=event_id)
    if previous is not None:
        return replay(state, previous, 'ACKNOWLEDGED')
    outcome = projection_receipt(state, event_id)
    if outcome is None:
        return rejected(state, 'EVENT_NOT_PROCESSED')
    if stale_state(state, expected_state_version):
        return rejected(state, 'STATE_CONFLICT')
    if state['state_version'] == MAX_VERSION:
        return rejected(state, 'VERSION_EXHAUSTED')
    candidate = deepcopy(state)
    candidate['state_version'] += 1
    receipt = {'store_id': state['store_id'], 'handler_id': HANDLER,
               'event_id': event_id, 'event_binding': event_binding(event),
               'projection_receipt_binding': projection_receipt_binding(outcome),
               'committed_state_version': candidate['state_version']}
    candidate['acknowledgements'].append(receipt)
    return commit(state, candidate, receipt, 'ACKNOWLEDGED', cut)


def recover_command(state, request, *, available=True):
    if not available:
        return observation('UNKNOWN', 'READ_UNAVAILABLE')
    error = acl_error(state, request)
    if error:
        return observation('REJECTED', error, state['state_version'])
    receipt = command_receipt(state, request)
    if receipt is None:
        return observation('ABSENT_AT_READ', 'NO_RECEIPT', state['state_version'])
    if canonical(request) != canonical(receipt['request']):
        return observation('REJECTED', 'IDEMPOTENCY_CONFLICT', state['state_version'])
    return observation('RESULT', receipt['status'], state['state_version'], receipt, True)


def recover_event(state, event, *, available=True):
    if not available:
        return observation('UNKNOWN', 'READ_UNAVAILABLE')
    if not trusted_event(state, event):
        return observation('REJECTED', 'EVENT_CORRUPTION', state['state_version'])
    receipt = projection_receipt(state, event['event_id'])
    if receipt is None:
        return observation('ABSENT_AT_READ', 'NO_RECEIPT', state['state_version'])
    return observation('RESULT', receipt['status'], state['state_version'], receipt, True)


def status(state):
    acked = {row['event_id'] for row in state['acknowledgements']}
    pending = sorted(row['event_id'] for row in state['outbox'] if row['event_id'] not in acked)
    lagging = []
    for article in state['articles']:
        projected = find(state['projections'], article_id=article['article_id'])
        if (article['article_revision'], article['author_ids']) != (projected['article_revision'],
                                                                  projected['author_ids']):
            lagging.append(article['article_id'])
    return {'state_version': state['state_version'], 'pending_event_ids': pending,
            'lagging_article_ids': sorted(lagging), 'complete': not pending and not lagging}


def search(state, person_id):
    if person_id not in state['people']:
        raise ValueError('UNKNOWN_PERSON')
    return list(find(state['author_index'], person_id=person_id)['article_ids'])


def apply(state, action):
    """Execute an authored operation. Recovery is wrapped without a mutation."""
    op = action['op']
    kwargs = {'expected_state_version': action.get('expected_state_version'),
              'cut': action.get('cut', 'none')}
    if op == 'replace':
        return replace_authorship(state, action['request'], **kwargs)
    if op == 'deliver':
        return deliver_event(state, action['event'], **kwargs)
    if op == 'ack':
        return acknowledge_event(state, action['event_id'], **kwargs)
    if op == 'recover_command':
        seen = recover_command(state, action['request'], available=action.get('available', True))
    elif op == 'recover_event':
        seen = recover_event(state, action['event'], available=action.get('available', True))
    else:
        raise ValueError('Unsupported oracle operation: ' + op)
    return {'state': deepcopy(state), 'actual_commit': False, 'observation': seen}
