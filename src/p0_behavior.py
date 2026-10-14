"""Own pure implementation of the frozen historical P0 catalog behavior only."""
from copy import deepcopy
import re

MAX = (1 << 64) - 1

def identifier(x):
    return type(x) is str and re.fullmatch(r'[a-z][a-z0-9-]{0,63}', x) is not None

def tag(x):
    return type(x) is str and re.fullmatch(r'[a-z][a-z0-9-]{0,15}', x) is not None

def run(operation, catalog, entry_id=None, new_tag=None):
    if operation not in ('migrate-list-to-set', 'add-tag'):
        raise ValueError('P0_BEHAVIOR_OPERATION')
    migrate = operation == 'migrate-list-to-set'

    def refuse(reason):
        result = {'kind': 'refusal', 'reason': reason, 'state_unchanged': True}
        if migrate:
            result['partial_output'] = False
        return result

    schema = 'catalog-list-1' if migrate else 'catalog-set-1'
    if (type(catalog) is not dict or set(catalog) != {'schema', 'revision', 'entries'}
            or catalog['schema'] != schema or type(catalog['revision']) is not int
            or not 0 <= catalog['revision'] <= MAX or type(catalog['entries']) is not list
            or any(type(e) is not dict or set(e) != {'id', 'tags'}
                   or type(e['tags']) is not list for e in catalog['entries'])):
        return refuse('invalid-schema')
    entries = catalog['entries']
    ids = [e['id'] for e in entries]
    if not all(identifier(i) for i in ids):
        return refuse('invalid-entry-id')
    if len(set(ids)) != len(ids):
        return refuse('duplicate-entry-id')
    if ids != sorted(ids):
        return refuse('entry-order')
    if migrate:
        if any(not tag(t) for e in entries for t in e['tags']):
            return refuse('invalid-tag')
        if catalog['revision'] == MAX:
            return refuse('revision-overflow')
        # Do not construct even partial output until every validation succeeds.
        output = {'schema': 'catalog-set-1', 'revision': catalog['revision'] + 1,
                  'entries': [{'id': e['id'], 'tags': sorted(set(e['tags']))} for e in entries]}
        return {'kind': 'success', 'output': output}
    for entry in entries:
        tags = entry['tags']
        if any(not tag(t) for t in tags) or tags != sorted(set(tags)):
            return refuse('noncanonical-set')
    if not identifier(entry_id):
        return refuse('invalid-entry-id')
    if not tag(new_tag):
        return refuse('invalid-tag')
    if entry_id not in ids:
        return refuse('entry-not-found')
    target = entries[ids.index(entry_id)]
    if new_tag in target['tags']:
        return {'kind': 'success', 'output': deepcopy(catalog)}
    if catalog['revision'] == MAX:
        return refuse('revision-overflow')
    output = deepcopy(catalog)
    output['revision'] += 1
    output['entries'][ids.index(entry_id)]['tags'] = sorted(target['tags'] + [new_tag])
    return {'kind': 'success', 'output': output}

def compare_migrations(left, right):
    a = run('migrate-list-to-set', left)
    b = run('migrate-list-to-set', right)
    return {'legacy_equal': left == right, 'left_result': a, 'right_result': b,
            'migrated_equal': a['kind'] == b['kind'] == 'success' and a['output'] == b['output']}
