"""Bounded portable form5 source history. Syntax/identity only; no execution."""
import hashlib
import json
import re

import bagaev_record_wide_form as form
from bagaev_record_draft import digest

LIMIT = 1048576
MAX_REVISIONS = 16
SCHEMA = 'bagaev-record-revisions/1'


class RevisionError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def need(condition, code):
    if not condition:
        raise RevisionError(code)


def pin(value):
    need(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None,
         'REVISION_PIN')


def canonical(value):
    # Bound traversal before JSON serialization, including hostile API objects.
    active = set()
    count = 0
    string_bytes = 0
    def visit(item, depth):
        nonlocal count, string_bytes
        count += 1
        need(count <= 1024 and depth <= 32, 'REVISION_BOUNDS')
        kind = type(item)
        need(kind in (dict, list, str, bool, type(None)), 'REVISION_SHAPE')
        if kind is str:
            try:
                string_bytes += len(item.encode('utf8'))
                need(string_bytes <= LIMIT, 'REVISION_BOUNDS')
            except UnicodeError:
                raise RevisionError('REVISION_UTF8') from None
        elif kind in (dict, list):
            need(id(item) not in active, 'REVISION_SHAPE')
            active.add(id(item))
            if kind is dict:
                for key, child in item.items():
                    need(type(key) is str, 'REVISION_SHAPE')
                    visit(key, depth + 1)
                    visit(child, depth + 1)
            else:
                for child in item:
                    visit(child, depth + 1)
            active.remove(id(item))
    visit(value, 0)
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     separators=(',', ':'), allow_nan=False).encode('utf8')
    need(len(raw) <= LIMIT, 'REVISION_BOUNDS')
    return raw


def package_digest(package):
    return hashlib.sha256(canonical(package)).hexdigest()


def source_bytes(source):
    need(type(source) in (bytes, str), 'REVISION_SOURCE')
    try:
        raw = source.encode('utf8') if type(source) is str else source
        need(len(raw) <= LIMIT, 'REVISION_BOUNDS')
        raw.decode('utf8')
    except UnicodeError:
        raise RevisionError('REVISION_UTF8') from None
    return raw


def make_revision(source, parent, source_sha256, program_sha256):
    pin(source_sha256)
    pin(program_sha256)
    if parent is not None:
        pin(parent)
    raw = source_bytes(source)
    need(hashlib.sha256(raw).hexdigest() == source_sha256, 'REVISION_SOURCE_PIN')
    try:
        program = form.decode(raw)
    except form.FormError:
        raise RevisionError('REVISION_SOURCE') from None
    need(digest(program) == program_sha256, 'REVISION_PROGRAM_PIN')
    identity = dict(parent=parent, source_sha256=source_sha256,
                    program_sha256=program_sha256)
    return dict(identity, id=package_digest(identity), source=raw.decode('utf8'))


def validate(package):
    canonical(package)
    keys = {'schema', 'form', 'revisions', 'head', 'semantic_check', 'execution_admission'}
    need(type(package) is dict and set(package) == keys, 'REVISION_SHAPE')
    need(package['schema'] == SCHEMA and package['form'] == 'record-form/5', 'REVISION_PROFILE')
    need(package['semantic_check'] is False and package['execution_admission'] is False,
         'REVISION_ASSURANCE')
    rows = package['revisions']
    need(type(rows) is list, 'REVISION_SHAPE')
    need(1 <= len(rows) <= MAX_REVISIONS, 'REVISION_BOUNDS')
    parent, previous_program, ids = None, None, set()
    for row in rows:
        need(type(row) is dict and set(row) == {'id', 'parent', 'source',
             'source_sha256', 'program_sha256'}, 'REVISION_SHAPE')
        need(type(row['source']) is str, 'REVISION_SHAPE')
        pin(row['id'])
        need(row['parent'] == parent, 'REVISION_LINEAGE')
        rebuilt = make_revision(row['source'], parent, row['source_sha256'], row['program_sha256'])
        need(row['id'] == rebuilt['id'] and row['id'] not in ids, 'REVISION_ID')
        need(row['program_sha256'] != previous_program, 'REVISION_NO_CHANGE')
        ids.add(row['id'])
        parent, previous_program = row['id'], row['program_sha256']
    pin(package['head'])
    need(package['head'] == parent, 'REVISION_HEAD')
    return package


def initialize(source, *, source_sha256, program_sha256):
    row = make_revision(source, None, source_sha256, program_sha256)
    return validate(dict(schema=SCHEMA, form='record-form/5', revisions=[row],
                         head=row['id'], semantic_check=False, execution_admission=False))


def append(package, source, *, expected_package_sha256, expected_head,
           source_sha256, program_sha256):
    validate(package)
    pin(expected_package_sha256)
    pin(expected_head)
    need(package_digest(package) == expected_package_sha256, 'REVISION_STALE_PACKAGE')
    need(package['head'] == expected_head, 'REVISION_STALE_HEAD')
    need(len(package['revisions']) < MAX_REVISIONS, 'REVISION_BOUNDS')
    row = make_revision(source, expected_head, source_sha256, program_sha256)
    result = json.loads(canonical(package))
    result['revisions'].append(row)
    result['head'] = row['id']
    return validate(result)


def inspect(package):
    validate(package)
    return dict(schema=SCHEMA, form='record-form/5', head=package['head'],
                revisions=[{k: v for k, v in row.items() if k != 'source'}
                           for row in package['revisions']],
                semantic_check=False, execution_admission=False)


def checkout(package, revision_id):
    validate(package)
    pin(revision_id)
    for row in package['revisions']:
        if row['id'] == revision_id:
            return row['source'].encode('utf8')
    raise RevisionError('REVISION_NOT_FOUND')


def loads(raw):
    raw = source_bytes(raw)
    # Bound syntactic nesting before invoking the JSON decoder.
    depth, quoted, escaped = 0, False, False
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            need(depth <= 32, 'REVISION_BOUNDS')
        elif byte in (93, 125):
            depth -= 1
    def pairs(items):
        out = {}
        for key, value in items:
            need(key not in out, 'REVISION_JSON')
            out[key] = value
        return out
    def reject_number(value):
        raise RevisionError('REVISION_JSON')
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_int=reject_number,
                           parse_float=reject_number, parse_constant=reject_number)
    except (ValueError, RecursionError) as error:
        if isinstance(error, RevisionError):
            raise
        raise RevisionError('REVISION_JSON') from None
    return validate(value)
