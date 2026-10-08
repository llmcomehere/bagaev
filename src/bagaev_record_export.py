"""Reconstitute a pinned focused draft as source data; no execution or admission."""
import copy
import re
import bagaev_record_function as narrow
import bagaev_record_wide_function as wide
from bagaev_record_draft import DraftError, need, digest


def export_source(original, packet, *, base_sha256, target_sha256, form_version='4'):
    need(form_version in ('4', '5'), 'EXPORT_FORM')
    edit = wide if form_version == '5' else narrow
    for pin in (base_sha256, target_sha256):
        need(type(pin) is str and re.fullmatch('[0-9a-f]{64}', pin) is not None, 'EXPORT_PIN')
    before = edit.form.decode(original)
    need(digest(before) == base_sha256, 'EXPORT_BASE')
    keys = {'schema', 'status', 'base', 'target', 'program', 'delta', 'semantic_check', 'execution_admission'}
    need(type(packet) is dict and set(packet) == keys, 'EXPORT_PACKET')
    need(packet['schema'] == ('bagaev-record-draft/2' if form_version == '5' else 'bagaev-record-draft/1')
         and packet['status'] == 'draft' and packet['base'] == base_sha256
         and packet['semantic_check'] is False and packet['execution_admission'] is False, 'EXPORT_PACKET')
    encoded = edit.form.encode(packet['program'])
    after = edit.form.decode(encoded)
    need(digest(after) == target_sha256 and packet['target'] == target_sha256, 'EXPORT_TARGET')
    need({k:v for k,v in before.items() if k != 'functions'} ==
         {k:v for k,v in after.items() if k != 'functions'}, 'EXPORT_SCOPE')
    old, new = before['functions'], after['functions']
    need(set(old) == set(new), 'EXPORT_SCOPE')
    changed = [name for name in old if old[name] != new[name]]
    need(len(changed) == 1, 'EXPORT_SCOPE')
    name = changed[0]
    part = copy.deepcopy(after)
    part['entry'] = name
    part['functions'] = {name: copy.deepcopy(new[name])}
    rebuilt = edit.replace(original, edit.form.encode(part), base_sha256=base_sha256,
                           function_sha256=digest(old[name]))
    need(digest(packet) == digest(rebuilt), 'EXPORT_PACKET')
    return encoded


def export_source_preserving_layout(original, packet, *, base_sha256, target_sha256, source_sha256):
    """Form5 body-only splice after full focused-draft validation and exact layout pin."""
    import hashlib
    import bagaev_record_wide_spans as spans
    need(type(source_sha256) is str and re.fullmatch('[0-9a-f]{64}', source_sha256) is not None, 'EXPORT_PIN')
    need(type(original) in (str, bytes), 'EXPORT_LAYOUT')
    try:
        raw = original.encode('utf8') if type(original) is str else original
    except UnicodeError:
        raise DraftError('EXPORT_LAYOUT') from None
    need(hashlib.sha256(raw).hexdigest() == source_sha256, 'EXPORT_SOURCE')
    canonical = export_source(raw, packet, base_sha256=base_sha256,
                              target_sha256=target_sha256, form_version='5')
    before, after = wide.form.decode(raw), wide.form.decode(canonical)
    changed = [name for name in before['functions'] if before['functions'][name] != after['functions'][name]]
    need(len(changed) == 1, 'EXPORT_SCOPE')
    pointer = '/program/functions/' + changed[0] + '/body'
    def body_range(source):
        rows = [row for row in spans.source_map(source)['locations'] if row['program_pointer'] == pointer]
        need(len(rows) == 1 and rows[0]['precision'] == 'exact-expression', 'EXPORT_LAYOUT')
        start, end = rows[0]['start_byte'], rows[0]['end_byte']
        need(0 <= start < end <= len(source), 'EXPORT_LAYOUT')
        return start, end
    start, end = body_range(raw)
    new_start, new_end = body_range(canonical)
    output = raw[:start] + canonical[new_start:new_end] + raw[end:]
    need(len(output) <= wide.form.old.BYTE_LIMIT, 'EXPORT_BOUNDS')
    decoded = wide.form.decode(output)
    need(decoded == after and digest(decoded) == target_sha256, 'EXPORT_LAYOUT')
    return output


def export_source_with_fragment_layout(original, packet, replacement, *, base_sha256,
                                       target_sha256, source_sha256):
    """Use an independently supplied matching fragment's exact expression bytes."""
    import bagaev_record_wide_spans as spans
    # Keep all prior packet, scope, source pin and target checks authoritative.
    validated = export_source_preserving_layout(original, packet, base_sha256=base_sha256,
                                                target_sha256=target_sha256, source_sha256=source_sha256)
    raw = original.encode('utf8') if type(original) is str else original
    need(type(replacement) in (str, bytes), 'EXPORT_LAYOUT')
    try:
        fragment = replacement.encode('utf8') if type(replacement) is str else replacement
    except UnicodeError:
        raise DraftError('EXPORT_LAYOUT') from None
    before, part = wide.form.decode(raw), wide.form.decode(fragment)
    name = part['entry']
    need(name in before['functions'], 'EXPORT_SCOPE')
    rebuilt = wide.replace(raw, fragment, base_sha256=base_sha256,
                           function_sha256=digest(before['functions'][name]))
    need(digest(rebuilt) == digest(packet), 'EXPORT_FRAGMENT')
    pointer = '/program/functions/' + name + '/body'
    def body_range(source):
        rows = [row for row in spans.source_map(source)['locations'] if row['program_pointer'] == pointer]
        need(len(rows) == 1 and rows[0]['precision'] == 'exact-expression', 'EXPORT_LAYOUT')
        start, end = rows[0]['start_byte'], rows[0]['end_byte']
        need(0 <= start < end <= len(source), 'EXPORT_LAYOUT')
        return start, end
    start, end = body_range(raw)
    new_start, new_end = body_range(fragment)
    output = raw[:start] + fragment[new_start:new_end] + raw[end:]
    need(len(output) <= wide.form.old.BYTE_LIMIT, 'EXPORT_BOUNDS')
    decoded = wide.form.decode(output)
    need(decoded == wide.form.decode(validated) and digest(decoded) == target_sha256, 'EXPORT_LAYOUT')
    return output
