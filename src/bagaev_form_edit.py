"""Pure probe-form-edit/1 receiver. Returns detached drafts, never admission/effects."""
from __future__ import annotations
import copy
import hashlib
import math
import re
import bagaev_forms as forms
import bagaev_l2 as l2

FRAME_BYTES, FRAME_DEPTH, FRAME_VALUES = 2097152, 8, 32
DIGEST = re.compile(r'sha256:[0-9a-f]{64}\Z', re.ASCII)
ID = re.compile(r'[A-Za-z][A-Za-z0-9._-]{0,63}\Z', re.ASCII)

def _fail(code, location=''):
    raise forms.FormError(code, location)

def _scalar_string(value, location):
    if type(value) is not str or any(0xd800 <= ord(c) <= 0xdfff for c in value):
        _fail('FORM_SHAPE', location)

def _frame(source):
    if type(source) not in (str, bytes):
        _fail('FORM_SYNTAX')
    try:
        raw = source.encode('utf-8') if type(source) is str else source
    except UnicodeError:
        _fail('FORM_SYNTAX')
    if len(raw) > FRAME_BYTES:
        _fail('FORM_BOUNDS')
    try:
        value = l2._parse(raw, text_limit=False)
    except l2.L2Error:
        _fail('FORM_SYNTAX')
    # Non-finite number rejection belongs to the syntax gate, before depth/count.
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is float and not math.isfinite(item):
            _fail('FORM_SYNTAX')
        if type(item) is dict:
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)
    pending = [(value, 1)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if depth > FRAME_DEPTH or count > FRAME_VALUES:
            _fail('FORM_BOUNDS')
        if type(item) is dict:
            pending.extend((item[k], depth + 1) for k in reversed(sorted(item)))
        elif type(item) is list:
            pending.extend((x, depth + 1) for x in reversed(item))
    if type(value) is not dict or set(value) != {'schema','form','base','candidate_id','patch'}:
        _fail('FORM_SHAPE')
    for field, accepted in [('schema', ('probe-form-edit/1',)), ('form', forms.FORMS)]:
        _scalar_string(value[field], '/' + field)
        if value[field] not in accepted:
            _fail('FORM_VERSION', '/' + field)
    if type(value['base']) is not str or not DIGEST.fullmatch(value['base']):
        _fail('FORM_SHAPE', '/base')
    if value['candidate_id'] is not None and (type(value['candidate_id']) is not str or not ID.fullmatch(value['candidate_id'])):
        _fail('FORM_SHAPE', '/candidate_id')
    _scalar_string(value['patch'], '/patch')
    if len(value['patch'].encode('utf-8')) > forms.BYTE_LIMIT:
        _fail('FORM_BOUNDS', '/patch')
    return value

def _patch_envelope(patch):
    # Preserve the existing L2 pre-CAS envelope/map gates, including nonempty,
    # disjoint add/replace maps. Do not inspect definition semantics here.
    l2._fields(patch, ('schema','base','target','add','replace'), 'L2_PATCH')
    l2._need(type(patch['schema']) is str and patch['schema'] == l2.PATCH_SCHEMA, 'L2_PATCH')
    l2._need(all(type(patch[k]) is str and DIGEST.fullmatch(patch[k]) for k in ('base','target')), 'L2_PATCH')
    for key in ('add','replace'):
        l2._need(type(patch[key]) is dict, 'L2_PATCH')
        for name, definition in patch[key].items():
            l2._need(type(name) is str and ID.fullmatch(name) and type(definition) is dict, 'L2_PATCH')
    l2._need(patch['add'] or patch['replace'], 'L2_PATCH')
    l2._need(not patch['add'].keys() & patch['replace'].keys(), 'L2_PATCH')

def _content_pin(value):
    """Stream canonical JSON data; no representation transport or semantic gate."""
    h = hashlib.sha256()
    def token(text):
        h.update(text.encode('utf-8'))
    pending = [('value', value)]
    while pending:
        kind, item = pending.pop()
        if kind == 'token':
            token(item)
            continue
        if type(item) is dict:
            if not all(type(k) is str for k in item):
                raise ValueError('noncanonical key')
            token('{')
            pending.append(('token', '}'))
            keys = sorted(item)
            for i in range(len(keys)-1, -1, -1):
                key = keys[i]
                pending.extend([('value', item[key]), ('token', ':'), ('value', key)])
                if i:
                    pending.append(('token', ','))
        elif type(item) is list:
            token('[')
            pending.append(('token', ']'))
            for i in range(len(item)-1, -1, -1):
                pending.append(('value', item[i]))
                if i:
                    pending.append(('token', ','))
        else:
            if type(item) is str and any(0xd800 <= ord(c) <= 0xdfff for c in item):
                raise ValueError('noncanonical string')
            token(forms._quote(item))
    return 'sha256:' + h.hexdigest()

def draft(original, frame, *, candidate_map=None):
    """Validate original, outer gates and patch before returning a separate draft.

    candidate_map, when needed, is a caller-owned immutable-during-call dict:
    ID -> {'kind': 'patch', 'pin': H(patch)}. It confers no authority.
    L2 errors retain their code and have no wrapper location.
    """
    before = l2.check_program(original)
    value = _frame(frame)
    patch = forms.decode(value['patch'], value['form'], mode='patch')
    _patch_envelope(patch)
    if value['base'] != patch['base']:
        _fail('FORM_BASE', '/base')
    if value['candidate_id'] is not None:
        if type(candidate_map) is not dict or not all(type(k) is str for k in candidate_map):
            _fail('FORM_CANDIDATE', '/candidate_id')
        selected = candidate_map.get(value['candidate_id'])
        if type(selected) is not dict or not all(type(k) is str for k in selected):
            _fail('FORM_CANDIDATE', '/candidate_id')
        if type(selected.get('kind')) is not str or selected['kind'] != 'patch' or type(selected.get('pin')) is not str:
            _fail('FORM_CANDIDATE', '/candidate_id')
        try:
            pin = _content_pin(patch)
        except (ValueError, UnicodeError, RecursionError):
            _fail('FORM_CANDIDATE', '/candidate_id')
        if selected['pin'] != pin:
            _fail('FORM_CANDIDATE', '/candidate_id')
    after = l2.apply_patch(before, patch)
    return {'schema':'probe-draft/1', 'status':'draft', 'base':before.digest,
            'target':after.digest, 'program':l2.program_value(after),
            'patch':copy.deepcopy(patch), 'admission':False}
