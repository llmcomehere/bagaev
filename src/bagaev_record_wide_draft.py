"""Explicit profile11 whole-source function draft data; no execution or admission."""
import copy
import re
import bagaev_record_wide_form as form
from bagaev_record_draft import DraftError, digest, need


def draft(original, candidate, *, base_sha256, target_sha256):
    for pin in (base_sha256, target_sha256):
        need(type(pin) is str and re.fullmatch('[0-9a-f]{64}', pin) is not None, 'DRAFT_PIN')
    before = form.decode(original)
    need(digest(before) == base_sha256, 'DRAFT_BASE')
    after = form.decode(candidate)
    need(digest(after) == target_sha256, 'DRAFT_TARGET')
    need({k:v for k,v in before.items() if k != 'functions'} ==
         {k:v for k,v in after.items() if k != 'functions'}, 'DRAFT_SCOPE')
    old, new = before['functions'], after['functions']
    need(set(old) <= set(new), 'DRAFT_SCOPE')
    for name in old:
        need(old[name]['params'] == new[name]['params'] and old[name]['result'] == new[name]['result'],
             'DRAFT_SIGNATURE')
    delta = {'add': sorted(set(new) - set(old)),
             'replace': sorted(name for name in old if old[name] != new[name])}
    need(delta['add'] or delta['replace'], 'DRAFT_NO_CHANGE')
    return {'schema':'bagaev-record-draft/2', 'status':'draft', 'base':base_sha256,
            'target':target_sha256, 'program':copy.deepcopy(after), 'delta':delta,
            'semantic_check':False, 'execution_admission':False}
