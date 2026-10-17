"""Bounded form5 comparison; no semantic checking, execution or patch creation."""
import hashlib
import json
import re
import bagaev_record_wide_form as form
from bagaev_record_draft import digest

SOURCE_LIMIT = 1048576
REPORT_LIMIT = 1048576

class DiffError(ValueError):
    def __init__(self, code, side=None):
        self.code, self.side = code, side
        super().__init__(code)

def _need(condition, code, side=None):
    if not condition:
        raise DiffError(code, side)

def _pins(before, after):
    for side, value in (('before', before), ('after', after)):
        _need(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None,
              'DIFF_PIN', side)

def _canonical(value, side=None):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise DiffError('DIFF_ENCODING', side) from None

def _digest(value, side=None):
    try:
        return digest(value)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise DiffError('DIFF_ENCODING', side) from None

def _decode(raw, side):
    try:
        return form.decode(raw)
    except form.FormError as error:
        raise DiffError(error.code, side) from None
    except UnicodeError:
        raise DiffError('DIFF_ENCODING', side) from None
    except json.JSONDecodeError:
        raise DiffError('FORM_SYNTAX', side) from None
    except RecursionError:
        raise DiffError('FORM_BOUNDS', side) from None

def _namespace(before, after, functions=False):
    result = {'added': [], 'removed': [], 'changed': []}
    for name in sorted(set(after) - set(before)):
        result['added'].append({'name': name, 'after_sha256': _digest(after[name], 'after')})
    for name in sorted(set(before) - set(after)):
        result['removed'].append({'name': name, 'before_sha256': _digest(before[name], 'before')})
    for name in sorted(set(before) & set(after)):
        old, new = before[name], after[name]
        if _canonical(old, 'before') == _canonical(new, 'after'):
            continue
        row = {'name': name, 'before_sha256': _digest(old, 'before'),
               'after_sha256': _digest(new, 'after')}
        if functions:
            old_signature = {key: old[key] for key in ('params', 'result')}
            new_signature = {key: new[key] for key in ('params', 'result')}
            row['signature_changed'] = _canonical(old_signature, 'before') != _canonical(new_signature, 'after')
            row['body_changed'] = _canonical(old['body'], 'before') != _canonical(new['body'], 'after')
        result['changed'].append(row)
    return result

def encode_report(report):
    raw = _canonical(report)
    _need(len(raw) <= REPORT_LIMIT, 'DIFF_BOUNDS')
    return raw

def compare_sources(before, after, *, before_sha256, after_sha256):
    """Return detached structural data for two exact caller-selected byte inputs."""
    _pins(before_sha256, after_sha256)
    for side, raw in (('before', before), ('after', after)):
        _need(type(raw) is bytes, 'DIFF_INPUT', side)
        _need(len(raw) <= SOURCE_LIMIT, 'DIFF_BOUNDS', side)
    for side, raw, pin in (('before', before, before_sha256), ('after', after, after_sha256)):
        _need(hashlib.sha256(raw).hexdigest() == pin, 'DIFF_' + side.upper(), side)
    old, new = _decode(before, 'before'), _decode(after, 'after')
    old_bytes, new_bytes = _canonical(old, 'before'), _canonical(new, 'after')
    report = {
        'schema': 'bagaev-record-source-diff/1', 'status': 'compared', 'form': 'record-form/5',
        'before': {'source_sha256': before_sha256, 'program_sha256': _digest(old, 'before'), 'source_bytes': len(before)},
        'after': {'source_sha256': after_sha256, 'program_sha256': _digest(new, 'after'), 'source_bytes': len(after)},
        'source_equal': before == after, 'program_equal': old_bytes == new_bytes,
        'entry': {'before': old['entry'], 'after': new['entry'], 'changed': old['entry'] != new['entry']},
        'declarations': {name: _namespace(old[name], new[name]) for name in ('records', 'lists', 'variants')},
        'functions': _namespace(old['functions'], new['functions'], functions=True),
        'semantic_check': False, 'execution_admission': False, 'patch_application': False,
    }
    encode_report(report)
    return report
