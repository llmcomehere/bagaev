"""Data-only focused form6 replacement and canonical export; no execution."""
import copy
import re
import bagaev_record_json_bool_form as form
from bagaev_record_draft import digest, DraftError, need


def replace(source, replacement, *, base_sha256, function_sha256):
    program = form.decode(source)
    need(type(base_sha256) is str and digest(program) == base_sha256, 'FUNCTION_BASE')
    part = form.decode(replacement)
    name = part['entry']
    need(set(part['functions']) == {name} and name in program['functions'], 'FUNCTION_SCOPE')
    original, proposed = program['functions'][name], part['functions'][name]
    need(type(function_sha256) is str and digest(original) == function_sha256, 'FUNCTION_PIN')
    need(all(part[k] == program[k] for k in ('schema','records','lists','variants')), 'FUNCTION_SCOPE')
    need(original['params'] == proposed['params'] and original['result'] == proposed['result'], 'FUNCTION_SIGNATURE')
    need(original != proposed, 'FUNCTION_NO_CHANGE')
    candidate = copy.deepcopy(program)
    candidate['functions'][name] = copy.deepcopy(proposed)
    form.prior.bounded(candidate)
    return dict(schema='bagaev-record-draft/2', status='draft', base=base_sha256,
                target=digest(candidate), program=candidate,
                delta={'add':[], 'replace':[name]}, semantic_check=False, execution_admission=False)


def export_source(original, packet, *, base_sha256, target_sha256):
    for pin in (base_sha256, target_sha256):
        need(type(pin) is str and re.fullmatch('[0-9a-f]{64}',pin) is not None,'EXPORT_PIN')
    before = form.decode(original)
    need(digest(before) == base_sha256, 'EXPORT_BASE')
    keys = {'schema','status','base','target','program','delta','semantic_check','execution_admission'}
    need(type(packet) is dict and set(packet) == keys, 'EXPORT_PACKET')
    need(packet['schema'] == 'bagaev-record-draft/2' and packet['status'] == 'draft'
         and packet['base'] == base_sha256 and packet['semantic_check'] is False
         and packet['execution_admission'] is False, 'EXPORT_PACKET')
    encoded = form.encode(packet['program'])
    after = form.decode(encoded)
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
    part['functions'] = {name:copy.deepcopy(new[name])}
    rebuilt = replace(original, form.encode(part), base_sha256=base_sha256,
                      function_sha256=digest(old[name]))
    need(type(packet['delta']) is dict and packet['delta'] == rebuilt['delta'], 'EXPORT_PACKET')
    need(digest(packet) == digest(rebuilt), 'EXPORT_PACKET')
    return encoded


def export_source_preserving_layout(original, packet, *, base_sha256, target_sha256, source_sha256):
    """Explicit form6 body splice; pins and full draft validation remain required."""
    import hashlib
    import bagaev_record_json_bool_spans as spans
    need(type(source_sha256) is str and re.fullmatch('[0-9a-f]{64}',source_sha256) is not None,'EXPORT_PIN')
    need(type(original) in (str,bytes),'EXPORT_LAYOUT')
    try:
        raw = original.encode('utf8') if type(original) is str else original
    except UnicodeError:
        raise DraftError('EXPORT_LAYOUT') from None
    need(hashlib.sha256(raw).hexdigest() == source_sha256,'EXPORT_SOURCE')
    canonical = export_source(raw,packet,base_sha256=base_sha256,target_sha256=target_sha256)
    before, after = form.decode(raw), form.decode(canonical)
    changed = [n for n in before['functions'] if before['functions'][n] != after['functions'][n]]
    need(len(changed) == 1,'EXPORT_SCOPE')
    pointer = '/program/functions/' + changed[0] + '/body'
    def body_range(source):
        rows = [r for r in spans.source_map(source)['locations'] if r['program_pointer'] == pointer]
        need(len(rows) == 1 and rows[0]['precision'] == 'exact-expression','EXPORT_LAYOUT')
        start,end = rows[0]['start_byte'],rows[0]['end_byte']
        need(0 <= start < end <= len(source),'EXPORT_LAYOUT')
        return start,end
    start,end = body_range(raw)
    new_start,new_end = body_range(canonical)
    output = raw[:start] + canonical[new_start:new_end] + raw[end:]
    need(len(output) <= form.prior.old.BYTE_LIMIT,'EXPORT_BOUNDS')
    decoded = form.decode(output)
    need(decoded == after and digest(decoded) == target_sha256,'EXPORT_LAYOUT')
    return output
