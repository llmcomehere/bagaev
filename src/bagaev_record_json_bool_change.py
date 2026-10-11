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
    need(digest(packet) == digest(rebuilt), 'EXPORT_PACKET')
    return encoded
