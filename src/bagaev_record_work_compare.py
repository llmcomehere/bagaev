"""Pure pinned source-pair upper-work comparison; no execution or equivalence check."""
import hashlib
import json
from bagaev_record_draft import need
from bagaev_record_wide_draft import draft, form
from bagaev_record_work import analyze


def compare(original, candidate, bounds, *, base_sha256, target_sha256):
    """Compare conditional bounds under one shared entry-argument contract.

    Graph pins and draft scope are checked. Differences concern upper bounds,
    not actual execution, value equivalence, or admission. Nothing is run.
    """
    change = draft(original, candidate, base_sha256=base_sha256,
                   target_sha256=target_sha256)
    before = form.decode(original)
    after = change['program']
    entry = before['functions'].get(before['entry'])
    need(entry is not None, 'WORK_ARGUMENTS')
    params = dict(entry['params'])
    need(type(bounds) is dict and set(bounds) == set(params) and
         all(type(s) is dict and s.get('type') == params[n]
             for n, s in bounds.items()), 'WORK_ARGUMENTS')
    try:
        canonical = json.dumps(bounds, sort_keys=True, ensure_ascii=False,
                               separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError, RecursionError):
        need(False, 'WORK_ARGUMENTS')
    def bound(program):
        f = program['functions'][program['entry']]
        result = analyze(f['body'], bounds, program['functions'],
                         program['records'], program['lists'])
        if 'location' in result and result['location']['function'] is None:
            result['location']['function'] = program['entry']
        return result
    def source_pin(source):
        return hashlib.sha256(source.encode('utf-8') if isinstance(source, str)
                              else source).hexdigest()
    left, right = bound(before), bound(after)
    result = {'schema': 'bagaev-record-work-comparison/1', 'status': 'comparison',
              'base': base_sha256, 'target': target_sha256,
              'original_source_sha256': source_pin(original),
              'candidate_source_sha256': source_pin(candidate),
              'argument_bounds_sha256': hashlib.sha256(canonical).hexdigest(),
              'delta': change['delta'], 'before': left, 'after': right,
              'semantic_check': False, 'execution_admission': False,
              'equivalence_check': False}
    if left['status'] == right['status'] == 'SUPPORTED':
        result['upper_work_delta'] = right['upper_work'] - left['upper_work']
    return result
