"""Serial P0 receiver model over trusted synthetic initial fixtures.

No I/O, authentication service, durability, concurrency or candidate execution.
Session/grant fixtures are model inputs, never evidence of real authority.
"""
from copy import deepcopy
import re

MAX = (1 << 64) - 1
SCOPES = {'write:catalog', 'read:receipts', 'manage:transfer',
          'candidate:store', 'candidate:admit'}

def ident(x):
    return type(x) is str and re.fullmatch(r'[a-z][a-z0-9-]{0,63}', x) is not None

def uint(x):
    return type(x) is int and 0 <= x <= MAX

def canonical(x):
    return type(x) is list and all(type(v) is str for v in x) and x == sorted(set(x))

def fields(x, names):
    return type(x) is dict and set(x) == set(names.split())

def valid_intent(i, transfer):
    if transfer:
        return (fields(i, 'task_id transfer_id expected_epoch recipient scope')
                and all(ident(i[k]) for k in ('task_id', 'transfer_id', 'recipient'))
                and uint(i['expected_epoch']) and canonical(i['scope'])
                and all(re.fullmatch(r'[a-z][a-z0-9:-]{0,63}', s) for s in i['scope']))
    return (fields(i, 'task_id operation_id task_revision behavior_revision contract_revision expected_record_revision mutation')
            and all(ident(i[k]) for k in ('task_id', 'operation_id', 'behavior_revision', 'contract_revision'))
            and uint(i['task_revision']) and uint(i['expected_record_revision'])
            and fields(i['mutation'], 'add remove')
            and all(canonical(i['mutation'][k]) for k in ('add', 'remove')))

class Receiver:
    def __init__(self, state, sessions):
        # Only prevalidated frozen synthetic initial state is admitted here.
        self._state = deepcopy(state)
        self._sessions = deepcopy(sessions)

    def snapshot(self):
        return deepcopy(self._state)

    def fixture_revoke(self, principal, grant):
        for row in self._sessions.values():
            if row['principal'] == principal:
                row['grants'] = [g for g in row['grants'] if g != grant]

    def fixture_revision(self, field, value):
        if field not in ('task_revision', 'behavior_revision', 'contract_revision'):
            raise ValueError('FIXTURE_FIELD')
        if not (uint(value) if field == 'task_revision' else ident(value)):
            raise ValueError('FIXTURE_VALUE')
        self._state['task'][field] = value

    def command(self, kind, session, intent=None, epoch=None, task_id=None, receipt_id=None):
        if kind not in ('write', 'transfer', 'query_operation', 'query_transfer'):
            raise ValueError('UNSUPPORTED_MODEL_COMMAND')
        before = self.snapshot()
        state = deepcopy(before)
        lookup = False
        committed = False

        def finish(response):
            self._state = state
            record, authority = state['record'], state['authority']
            return deepcopy({'response': response, 'committed': committed,
                'receipt_lookup_performed': lookup, 'state_changed': state != before,
                'record': record, 'record_revision': record['revision'],
                'authority_epoch': authority['epoch'], 'assignee': authority['assignee'],
                'operation_receipt_count': len(state['operation_receipts']),
                'transfer_receipt_count': len(state['transfer_receipts'])})

        def refuse(reason, malformed=False):
            return finish({'kind': 'request-refusal' if malformed else 'current-refusal',
                           'reason': reason})

        def receipt(value):
            response = {'kind': 'receipt', 'value': value}
            if 'outcome' in value:
                response['outcome'] = value['outcome']
            return finish(response)

        is_query = kind.startswith('query_')
        if type(session) is not str:
            return refuse('invalid-request', True)
        if is_query:
            if not (ident(task_id) and ident(receipt_id)):
                return refuse('invalid-request', True)
        else:
            if not valid_intent(intent, kind == 'transfer') or (kind == 'write' and not uint(epoch)):
                return refuse('invalid-request', True)
            intent = deepcopy(intent)
            task_id = intent['task_id']
        auth = self._sessions.get(session)
        if not auth or not auth['authenticated']:
            return refuse('authentication-required')
        if task_id != state['task']['task_id']:
            return refuse('task-not-found')
        grants = auth['grants']
        if is_query:
            if 'read:receipts' not in grants:
                return refuse('read-scope-required')
            lookup = True
            table = state['operation_receipts' if kind == 'query_operation' else 'transfer_receipts']
            value = table.get((task_id, receipt_id))
            return receipt(value) if value is not None else finish({'kind': 'receipt-absent-at-query'})
        if kind == 'transfer':
            if 'manage:transfer' not in grants:
                return refuse('transfer-scope-required')
            key = (task_id, intent['transfer_id'])
            lookup = True
            old = state['transfer_receipts'].get(key)
            if old is not None:
                return receipt(old) if old['intent'] == intent else refuse('transfer-id-conflict')
            prior = state['authority']
            if intent['expected_epoch'] != prior['epoch']:
                return refuse('epoch-mismatch')
            recipients = [r for r in self._sessions.values()
                          if r['authenticated'] and r['principal'] == intent['recipient']]
            if not recipients or not all(s in SCOPES and s in recipients[0]['grants'] for s in intent['scope']):
                return refuse('recipient-or-scope-unsupported')
            if prior['epoch'] == MAX:
                return refuse('epoch-overflow')
            after = {'epoch': prior['epoch'] + 1, 'assignee': intent['recipient'], 'scope': intent['scope']}
            value = {'task_id': task_id, 'transfer_id': intent['transfer_id'], 'intent': intent,
                     'prior_authority': deepcopy(prior), 'resulting_authority': deepcopy(after)}
            state['authority'] = after
            state['transfer_receipts'][key] = value
            committed = True
            return receipt(value)
        authority, task = state['authority'], state['task']
        if auth['principal'] != authority['assignee']:
            return refuse('assignee-mismatch')
        if 'write:catalog' not in grants or 'write:catalog' not in authority['scope']:
            return refuse('write-scope-required')
        for field in ('task_revision', 'behavior_revision', 'contract_revision'):
            if intent[field] != task[field]:
                return refuse(field.replace('_', '-') + '-mismatch')
        if epoch != authority['epoch']:
            return refuse('epoch-mismatch')
        key = (task_id, intent['operation_id'])
        lookup = True
        old = state['operation_receipts'].get(key)
        if old is not None:
            return receipt(old) if old['intent'] == intent else refuse('operation-id-conflict')
        record = state['record']
        outcome = {'kind': 'refusal-committed', 'reason': 'revision-conflict',
                   'observed_record_revision': record['revision']}
        if intent['expected_record_revision'] == record['revision']:
            add, remove = intent['mutation']['add'], intent['mutation']['remove']
            detail = None
            if set(add) & set(remove):
                detail = 'overlapping-change'
            elif any(re.fullmatch(r'[a-z][a-z0-9-]{0,15}', t) is None for t in add + remove):
                detail = 'invalid-tag'
            elif not set(remove) <= set(record['tags']):
                detail = 'missing-remove'
            elif record['revision'] == MAX:
                detail = 'revision-overflow'
            if detail:
                outcome.update(reason='contract-refusal', detail=detail)
            else:
                after = {'revision': record['revision'] + 1,
                         'tags': sorted((set(record['tags']) - set(remove)) | set(add))}
                outcome = {'kind': 'effect-committed', 'record_revision_before': record['revision'],
                           'record_revision_after': after['revision'], 'tags_after': after['tags']}
                state['record'] = after
        value = {'task_id': task_id, 'operation_id': intent['operation_id'],
                 'intent': intent, 'outcome': outcome}
        state['operation_receipts'][key] = value
        committed = True
        return receipt(value)
