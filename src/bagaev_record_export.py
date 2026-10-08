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
