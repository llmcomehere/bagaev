"""Pure comparison reference for docs/catalog-wide.md, catalog-application/3.

Only ordinary finite JSON values are in the callable domain. Validation is
shallow and bounded by the schema, including when malformed values are deeply
nested. No mutation, persistence, parsing, or external effects occur here.
"""


def _object(value, required, optional=()):
    return (type(value) is dict and required <= value.keys()
            and value.keys() <= required | set(optional))


def _identifier(value):
    return (type(value) is str and 1 <= len(value) <= 8
            and 'a' <= value[0] <= 'z'
            and all('a' <= c <= 'z' or '0' <= c <= '9' or c == '-'
                    for c in value))


def _tags(value):
    return type(value) is list and len(value) <= 4 and all(map(_identifier, value))


def _shape(request):
    if not _object(request, {'interface', 'behavior_revision', 'state', 'reindex'}):
        return False
    revision = request['behavior_revision']
    if (request['interface'] != 'catalog-application/3'
            or type(revision) is not int or not 0 <= revision <= 3):
        return False
    state = request['state']
    if not _object(state, {'entries'}):
        return False
    entries = state['entries']
    if type(entries) is not list or len(entries) > 16:
        return False
    for entry in entries:
        if not _object(entry, {'id', 'title', 'manual_tags', 'indexed_tags'}, {'date'}):
            return False
        title = entry['title']
        if (not _identifier(entry['id']) or type(title) is not str
                or not 1 <= len(title) <= 16
                or not all(' ' <= c <= '~' for c in title)
                or not _tags(entry['manual_tags']) or not _tags(entry['indexed_tags'])):
            return False
    operation = request['reindex']
    return operation is None or (
        _object(operation, {'entry_id', 'tags'})
        and _identifier(operation['entry_id']) and _tags(operation['tags']))


def _refuse(reason):
    return {'kind': 'refusal', 'reason': reason}


def evaluate(request):
    """Return a detached exact success/refusal, following the seven ordered gates."""
    if not _shape(request):
        return _refuse('invalid-request')
    entries = request['state']['entries']
    revision, operation = request['behavior_revision'], request['reindex']
    if any('date' in e and (type(e['date']) is not int or not 0 <= e['date'] <= 31)
           for e in entries):
        return _refuse('invalid-date')
    ids = [e['id'] for e in entries]
    if len(set(ids)) != len(ids):
        return _refuse('duplicate-entry-id')
    if ids != sorted(ids):
        return _refuse('entry-order')
    if any(set(e['manual_tags']).intersection(e['indexed_tags']) for e in entries):
        return _refuse('origin-collision')
    if operation is not None:
        if operation['entry_id'] not in ids:
            return _refuse('entry-not-found')
        selected = entries[ids.index(operation['entry_id'])]
        if revision >= 2 and set(selected['manual_tags']).intersection(operation['tags']):
            return _refuse('origin-collision')

    # All values copied by reference below are now validated immutable scalars.
    result = []
    for entry in entries:
        output = {key: entry[key] for key in ('id', 'title')}
        if 'date' in entry:
            output['date'] = entry['date']
        manual, indexed = entry['manual_tags'], entry['indexed_tags']
        if operation is not None and entry['id'] == operation['entry_id']:
            manual = [] if revision < 2 else manual
            indexed = operation['tags']
        output['manual_tags'] = sorted(set(manual)) if revision else list(manual)
        output['indexed_tags'] = sorted(set(indexed)) if revision else list(indexed)
        result.append(output)

    def order(entry):
        if 'date' not in entry:
            return (1 if revision == 3 else -1, 0, entry['id'])
        return (0, entry['date'], entry['id'])

    return {'kind': 'success', 'state': {'entries': result},
            'entry_ids': [e['id'] for e in sorted(result, key=order)]}
