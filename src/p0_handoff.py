"""Frozen P0 synthetic handoff model, no filesystem or candidate execution."""
from copy import deepcopy
from hashlib import sha256
import json
import re

def equal(a, b):
    # JSON values: distinguish bool/int and preserve array order.
    return json.dumps(a, sort_keys=True, separators=(',', ':')) == json.dumps(b, sort_keys=True, separators=(',', ':'))

def snapshot_valid(snapshot):
    if type(snapshot) is not dict or set(snapshot) != {'snapshot_id', 'snapshot_bytes_sha256', 'candidate_files'}:
        return False
    files = snapshot['candidate_files']
    if (type(files) is not list or not files or type(snapshot['snapshot_id']) is not str
            or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', snapshot['snapshot_id'])):
        return False
    paths, bundle = [], bytearray(b'p0-snapshot-v1\n')
    for row in files:
        if type(row) is not dict or set(row) != {'path', 'content_utf8', 'sha256'}:
            return False
        path, content = row['path'], row['content_utf8']
        if type(path) is not str or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,63}(?:/[a-z0-9][a-z0-9._-]{0,63})*', path):
            return False
        if len(path) > 255 or type(content) is not str:
            return False
        try:
            raw, name = content.encode('utf-8'), path.encode('ascii')
        except UnicodeError:
            return False
        if sha256(raw).hexdigest() != row['sha256']:
            return False
        paths.append(path)
        bundle.extend(f'file {len(name)} {len(raw)}\n'.encode('ascii') + name + raw)
    return paths == sorted(set(paths)) and sha256(bundle).hexdigest() == snapshot['snapshot_bytes_sha256']

CHECKPOINT_FIELDS = set('checkpoint_id task_revision behavior_revision contract_version oracle_version base_snapshot candidate_snapshot completed remaining case_results started_effects unknowns'.split())

def checkpoint_valid(c):
    return (type(c) is dict and set(c) == CHECKPOINT_FIELDS
            and type(c['task_revision']) is int and 0 <= c['task_revision'] < (1 << 64)
            and all(type(c[k]) is str and c[k] for k in ('checkpoint_id', 'behavior_revision', 'contract_version', 'oracle_version', 'base_snapshot'))
            and all(type(c[k]) is list for k in ('completed', 'remaining', 'case_results', 'started_effects', 'unknowns'))
            and snapshot_valid(c['candidate_snapshot']))

class Handoff:
    def __init__(self, state, behavior_cases):
        self._state = deepcopy(state)
        self._cases = deepcopy(behavior_cases)

    def snapshot(self):
        return deepcopy(self._state)

    def validate(self, checkpoint, successor_run):
        valid = checkpoint_valid(checkpoint)
        frozen = (successor_run['oracle_version'] == self._state['oracle_version']
                  and successor_run['required_case_ids'] == self._state['required_case_ids'])
        return {'checkpoint_complete': valid, 'candidate_hashes_verified': valid,
                'checkpoint_is_behavior_acceptance': False,
                'before_and_after_runs_required': successor_run['phases'] == ['before-successor-change','after-successor-change'],
                'same_frozen_oracle_before_after': frozen,
                'delivery_tag_is_behavior_evidence': False, 'hidden_reasoning_required': False}

    def accept(self, request):
        r, s = deepcopy(request), self._state
        facts = {'result_records_examined': False, 'snapshot_checks_performed': False,
                 'admission_checked': False}
        def finish(response):
            return deepcopy({'response': response, **facts,
                             'handoff_acceptance_record_count': len(s['handoff_acceptance_records'])})
        def refuse(reason, **extra):
            facts.update(extra)
            return finish({'kind': 'handoff-refusal', 'reason': reason})
        if any(r[k] != s[k] for k in ('contract_version','oracle_version')):
            return refuse('handoff-version-stale')
        required = s['required_case_ids']
        if r['input_case_ids'] != required:
            return refuse('handoff-input-stale', stale_input_case_ids=[i for i in required if i not in r['input_case_ids']])
        stale = []
        for row in r['before_results'] + r['after_results']:
            cid = row.get('case_id')
            if cid not in self._cases or not equal(row.get('input'), self._cases[cid]['input']):
                if cid not in stale:
                    stale.append(cid)
        if stale:
            return refuse('handoff-input-stale', stale_input_case_ids=stale)
        facts['snapshot_checks_performed'] = True
        checkpoint = s['checkpoints'].get(r['checkpoint_id'])
        predecessor, successor = r['predecessor_snapshot'], r['successor_snapshot']
        if (not checkpoint_valid(checkpoint) or not snapshot_valid(predecessor)
                or not equal(predecessor, checkpoint['candidate_snapshot'])):
            return refuse('handoff-snapshot-mismatch', mismatched_snapshot='predecessor')
        retained = [c for c in s['retained_candidates'].values()
                    if c['candidate_snapshot']['snapshot_id'] == successor['snapshot_id']]
        if (not snapshot_valid(successor) or len(retained) != 1
                or not equal(retained[0]['candidate_snapshot'], successor)
                or retained[0]['candidate_bytes_sha256'] != successor['snapshot_bytes_sha256']):
            return refuse('handoff-snapshot-mismatch', mismatched_snapshot='successor', same_snapshot_id=bool(retained))
        candidate = retained[0]
        selection = s['current_admission_selection']
        bindings = {'candidate_snapshot_id': successor['snapshot_id'],
                    'candidate_bytes_sha256': successor['snapshot_bytes_sha256'],
                    **{k: candidate[k] for k in ('code_revision','base_snapshot_revision','behavior_revision','contract_revision')}}
        evidence_ids = candidate['evidence_ids']
        evidence = s['trusted_evidence'].get(evidence_ids[0]) if len(evidence_ids) == 1 else None
        if (not evidence or any(selection.get(k) != v or evidence.get(k) != v for k,v in bindings.items())):
            return refuse('handoff-snapshot-mismatch', mismatched_snapshot='successor', same_snapshot_id=True)
        facts.update(predecessor_file_count=len(predecessor['candidate_files']),
                     successor_file_count=len(successor['candidate_files']), aggregate_hashes_verified=True)
        facts['result_records_examined'] = True
        invalid = []
        for phase in ('before_results','after_results'):
            seen = set()
            for row in r[phase]:
                cid, status = row['case_id'], row.get('status')
                shape = {'case_id','input','status'} | (set() if status == 'not-run' else {'observation'})
                valid = set(row) == shape and status in ('pass','fail','not-run') and cid not in seen
                seen.add(cid)
                if status != 'not-run':
                    computed = 'pass' if equal(row.get('observation'), self._cases[cid]['expect']) else 'fail'
                    valid = valid and status == computed
                if not valid and cid not in invalid:
                    invalid.append(cid)
        if invalid:
            return refuse('handoff-result-invalid', invalid_case_ids=invalid)
        before = {x['case_id']:x for x in r['before_results']}
        after = {x['case_id']:x for x in r['after_results']}
        missing = [i for i in required if i not in before]
        not_run = [i for i in required if i in before and before[i]['status'] == 'not-run']
        if missing or not_run:
            return refuse('handoff-before-incomplete', missing_case_ids=missing, not_run_case_ids=not_run)
        missing = [i for i in required if i not in after or after[i]['status'] == 'not-run']
        if missing:
            return refuse('handoff-after-incomplete', missing_case_ids=missing)
        mismatch = [i for i in required if after[i]['status'] != 'pass']
        if mismatch:
            return refuse('handoff-after-mismatch', mismatched_case_ids=mismatch)
        facts['after_all_match'] = True
        if checkpoint['started_effects'] or checkpoint['unknowns']:
            return refuse('handoff-checkpoint-unresolved',
                          unresolved_effect_ids=[e['effect_id'] for e in checkpoint['started_effects']],
                          unresolved_assumptions=checkpoint['unknowns'])
        facts['admission_checked'] = True
        admission = s['admission_records'].get(r['admission_record_id'])
        if (not admission or any(admission.get(k) != v for k,v in bindings.items())
                or admission.get('candidate_id') != candidate['candidate_id']
                or admission.get('evidence_id') != evidence_ids[0]
                or admission.get('requirement_assertion') != 'behavior-cases-pass'
                or any(evidence.get(k) != v for k,v in {
                    'trusted_origin':'trusted-checker', 'assertion':'behavior-cases-pass',
                    'tool_revision':'checker-1', 'result':'pass', 'assumptions':['synthetic-cpu-only'],
                    'input_binding':{'oracle_version':s['oracle_version'],'case_ids':required}}.items())):
            return refuse('handoff-admission-missing')
        facts['admission_checked_separately'] = True
        facts['before_failures_retained'] = [i for i in required if before[i]['status'] == 'fail']
        record = {k:r[k] for k in ('acceptance_id','checkpoint_id','contract_version','oracle_version','input_case_ids','before_results','after_results','admission_record_id')}
        for label, snap in (('predecessor',predecessor),('successor',successor)):
            record[label+'_snapshot_id'] = snap['snapshot_id']
            record[label+'_snapshot_sha256'] = snap['snapshot_bytes_sha256']
        previous = s['handoff_acceptance_records'].get(r['acceptance_id'])
        if previous is not None and not equal(previous, record):
            raise ValueError('UNSPECIFIED_ACCEPTANCE_ID_CONFLICT')
        s['handoff_acceptance_records'][r['acceptance_id']] = deepcopy(record)
        return finish({'kind':'handoff-accepted','value':record})
